#!/usr/bin/env python3
"""Minimal validation-only Google Data Manager API connectivity probe.

This script intentionally does not import app.py or modify production behavior.
It uses Application Default Credentials, validates the intended service-account
identity, and sends one validateOnly event-ingestion request to the configured
JSM Google Ads destination.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession, Request
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_MANAGER_SCOPE = "https://www.googleapis.com/auth/datamanager"
DATA_MANAGER_EVENTS_INGEST_URL = "https://datamanager.googleapis.com/v1/events:ingest"
EXPECTED_SERVICE_ACCOUNT = (
    "starting-account-jt9ttnrj92ac@jsmcoop-ads-api-305-2026.iam.gserviceaccount.com"
)
EXPECTED_QUOTA_PROJECT = "jsmcoop-ads-api-305-2026"
SYNTHETIC_VALIDATION_EMAIL = "dmapi-validation-only@jsmcoop.invalid"


def normalize_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def redacted_digits(value: str) -> str:
    value = normalize_digits(value)
    if not value:
        return ""
    if len(value) <= 4:
        return "<redacted>"
    return f"<redacted:{len(value)} digits ending {value[-4:]}>"


def redact_value(value: Any, sensitive_values: list[str] | None = None) -> Any:
    sensitive_values = [item for item in sensitive_values or [] if item]
    if isinstance(value, dict):
        return {key: redact_value(item, sensitive_values) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item, sensitive_values) for item in value]
    if not isinstance(value, str):
        return value

    redacted = value
    for sensitive in sensitive_values:
        redacted = redacted.replace(sensitive, redacted_digits(sensitive))
    return re.sub(r"\b\d{5,}\b", lambda match: redacted_digits(match.group(0)), redacted)


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def env_value(name: str) -> str:
    return (os.getenv(name) or "").strip()


def configured_conversion_action_id() -> str:
    signed_book_action_id = normalize_digits(env_value("GOOGLE_ADS_SIGNED_BOOK_PURCHASE_CONVERSION_ACTION_ID"))
    if signed_book_action_id:
        return signed_book_action_id

    action_id = normalize_digits(env_value("GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_ID"))
    if action_id:
        return action_id

    resource = env_value("GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_RESOURCE")
    match = re.fullmatch(r"customers/\d+/conversionActions/(\d+)", resource)
    return match.group(1) if match else ""


def hashed_validation_email() -> str:
    normalized = SYNTHETIC_VALIDATION_EMAIL.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def adc_identity(credentials: Any) -> str:
    for attr in ("service_account_email", "target_principal"):
        value = getattr(credentials, attr, None)
        if value:
            return value
    return ""


def build_payload(customer_id: str, conversion_action_id: str, login_customer_id: str) -> dict[str, Any]:
    account = {"accountType": "GOOGLE_ADS", "accountId": customer_id}
    destination = {
        "operatingAccount": account,
        "loginAccount": {
            "accountType": "GOOGLE_ADS",
            "accountId": login_customer_id or customer_id,
        },
        "productDestinationId": conversion_action_id,
    }

    return {
        "destinations": [destination],
        "encoding": "HEX",
        "validateOnly": True,
        "consent": {
            "adUserData": "CONSENT_GRANTED",
            "adPersonalization": "CONSENT_GRANTED",
        },
        "events": [
            {
                "transactionId": f"dmapi-validation-{uuid.uuid4()}",
                "eventTimestamp": datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
                "eventSource": "WEB",
                "conversionValue": 0,
                "conversionCount": 1,
                "currency": env_value("BOOK_DIRECT_PRICE_CURRENCY") or "USD",
                "userData": {
                    "userIdentifiers": [
                        {
                            "emailAddress": hashed_validation_email(),
                        }
                    ]
                },
            }
        ],
    }


def sanitized_destination_summary(
    payload: dict[str, Any],
    quota_project: str,
    endpoint: str,
) -> dict[str, Any]:
    destinations = payload.get("destinations") or []
    destination = destinations[0] if destinations else {}
    operating_account = destination.get("operatingAccount") or {}
    login_account = destination.get("loginAccount") or {}

    return {
        "operating_account_type": operating_account.get("accountType", ""),
        "operating_account_id": redacted_digits(operating_account.get("accountId", "")),
        "login_account_type": login_account.get("accountType", ""),
        "login_account_id": redacted_digits(login_account.get("accountId", "")),
        "product_destination_type": "GOOGLE_ADS_CONVERSION_ACTION_ID",
        "conversion_action_id": redacted_digits(destination.get("productDestinationId", "")),
        "validate_only": bool_text(bool(payload.get("validateOnly"))),
        "quota_project": quota_project,
        "endpoint": endpoint,
    }


def extract_google_rpc_error(
    response: Any,
    sensitive_values: list[str],
) -> dict[str, Any]:
    error_info: dict[str, Any] = {
        "http_status": response.status_code,
        "google_rpc_status": "",
        "error_message": "",
        "error_reason": "",
        "field_violations": [],
        "request_id": "",
        "structured_error_body": {},
    }

    try:
        body = response.json()
    except ValueError:
        error_info["error_message"] = response.text.strip()
        return redact_value(error_info, sensitive_values)

    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        error_info["google_rpc_status"] = error.get("status", "")
        error_info["error_message"] = error.get("message", "")

        for detail in error.get("details", []) or []:
            if not isinstance(detail, dict):
                continue
            detail_type = detail.get("@type", "")
            if detail_type.endswith("google.rpc.ErrorInfo"):
                error_info["error_reason"] = detail.get("reason", "")
                metadata = detail.get("metadata") or {}
                if isinstance(metadata, dict) and metadata.get("requestId"):
                    error_info["request_id"] = metadata["requestId"]
            elif detail_type.endswith("google.rpc.BadRequest"):
                error_info["field_violations"] = detail.get("fieldViolations", [])
            elif detail_type.endswith("google.rpc.RequestInfo") and detail.get("requestId"):
                error_info["request_id"] = detail["requestId"]
    else:
        error_info["error_message"] = json.dumps(body, sort_keys=True)

    for header_name in (
        "x-request-id",
        "x-google-request-id",
        "x-goog-request-id",
        "x-guploader-uploadid",
    ):
        if not error_info["request_id"] and response.headers.get(header_name):
            error_info["request_id"] = response.headers[header_name]
            break

    error_info["structured_error_body"] = body
    return redact_value(error_info, sensitive_values)


def tokeninfo_identity(credentials: Any) -> dict[str, str]:
    token = getattr(credentials, "token", "")
    if not token:
        return {
            "tokeninfo_checked": "no",
            "token_email": "unavailable",
            "token_scope_contains_datamanager": "unknown",
        }

    try:
        session = AuthorizedSession(credentials)
        response = session.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": token},
            timeout=15,
        )
        body = response.json() if response.ok else {}
    except Exception:
        return {
            "tokeninfo_checked": "no",
            "token_email": "unavailable",
            "token_scope_contains_datamanager": "unknown",
        }

    scopes = set((body.get("scope") or "").split())
    return {
        "tokeninfo_checked": "yes",
        "token_email": body.get("email", "unavailable"),
        "token_scope_contains_datamanager": bool_text(DATA_MANAGER_SCOPE in scopes),
    }


def main() -> int:
    load_dotenv(BASE_DIR / ".env")

    result: dict[str, Any] = {
        "authentication_result": {
            "adc_resolved": "no",
            "service_account_used": "",
            "scope_used": DATA_MANAGER_SCOPE,
            "quota_project_used": EXPECTED_QUOTA_PROJECT,
            "adc_default_project_matches_quota_project": "unknown",
        },
        "data_manager_api_result": {
            "endpoint_service_called": "not called",
            "http_api_status": "not called",
            "jsm_google_ads_destination_reachable": "unknown",
        },
        "request_destination": {
            "operating_account_type": "",
            "operating_account_id": "",
            "login_account_type": "",
            "login_account_id": "",
            "product_destination_type": "",
            "conversion_action_id": "",
            "validate_only": "yes",
            "quota_project": EXPECTED_QUOTA_PROJECT,
            "endpoint": DATA_MANAGER_EVENTS_INGEST_URL,
        },
        "effective_caller": {
            "credentials_identity": "",
            "tokeninfo_checked": "no",
            "token_email": "unavailable",
            "token_scope_contains_datamanager": "unknown",
            "authorizing_as_expected_service_account": "unknown",
        },
        "validation_result": {
            "validate_only": "yes",
            "payload_accepted_in_validation_only": "unknown",
            "used_fake_gclid": "no",
            "sent_real_conversion": "no",
        },
        "errors": [],
    }

    try:
        credentials, default_project_id = google.auth.default(
            scopes=[DATA_MANAGER_SCOPE],
            quota_project_id=EXPECTED_QUOTA_PROJECT,
        )
        credentials.refresh(Request())
    except Exception as exc:  # pragma: no cover - command-line diagnostic
        result["errors"].append(f"ADC_ERROR: {type(exc).__name__}: {exc}")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    identity = adc_identity(credentials)
    token_identity = tokeninfo_identity(credentials)
    result["authentication_result"].update(
        {
            "adc_resolved": bool_text(bool(identity)),
            "service_account_used": identity or "unavailable",
            "adc_default_project_matches_quota_project": bool_text(
                default_project_id == EXPECTED_QUOTA_PROJECT
            ),
        }
    )
    result["effective_caller"].update(
        {
            "credentials_identity": identity or "unavailable",
            **token_identity,
            "authorizing_as_expected_service_account": bool_text(
                identity == EXPECTED_SERVICE_ACCOUNT
                and token_identity.get("token_email", identity) in {EXPECTED_SERVICE_ACCOUNT, "unavailable"}
            ),
        }
    )

    if identity != EXPECTED_SERVICE_ACCOUNT:
        result["errors"].append(
            "ADC_IDENTITY_MISMATCH: ADC did not resolve to the intended JSM service account."
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    customer_id = normalize_digits(env_value("GOOGLE_ADS_CUSTOMER_ID"))
    conversion_action_id = configured_conversion_action_id()
    login_customer_id = customer_id

    missing = []
    if not customer_id:
        missing.append("GOOGLE_ADS_CUSTOMER_ID")
    if not conversion_action_id:
        missing.append("GOOGLE_ADS_SIGNED_BOOK_PURCHASE_CONVERSION_ACTION_ID")

    if missing:
        result["errors"].append(
            "CONFIG_ERROR: Missing required JSM configuration: " + ", ".join(missing)
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    result["data_manager_api_result"].update(
        {
            "endpoint_service_called": DATA_MANAGER_EVENTS_INGEST_URL,
            "google_ads_customer_id": redacted_digits(customer_id),
            "conversion_action_id": redacted_digits(conversion_action_id),
            "login_customer_id": redacted_digits(login_customer_id or customer_id),
        }
    )

    payload = build_payload(customer_id, conversion_action_id, login_customer_id)
    result["request_destination"] = sanitized_destination_summary(
        payload,
        EXPECTED_QUOTA_PROJECT,
        DATA_MANAGER_EVENTS_INGEST_URL,
    )
    session = AuthorizedSession(credentials)
    try:
        response = session.post(DATA_MANAGER_EVENTS_INGEST_URL, json=payload, timeout=30)
    except Exception as exc:  # pragma: no cover - command-line diagnostic
        result["errors"].append(f"REQUEST_ERROR: {type(exc).__name__}: {exc}")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    result["data_manager_api_result"]["http_api_status"] = response.status_code
    if response.ok:
        result["data_manager_api_result"]["jsm_google_ads_destination_reachable"] = "yes"
        result["validation_result"]["payload_accepted_in_validation_only"] = "yes"
        try:
            body = response.json()
        except ValueError:
            body = {}
        if body.get("fieldWarnings"):
            result["validation_result"]["field_warnings"] = body["fieldWarnings"]
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    structured_error = extract_google_rpc_error(
        response,
        [customer_id, conversion_action_id, login_customer_id],
    )
    result["data_manager_api_result"]["jsm_google_ads_destination_reachable"] = "no"
    result["validation_result"]["payload_accepted_in_validation_only"] = "no"
    result["full_data_manager_error"] = structured_error
    result["errors"].append(
        "API_ERROR: "
        + (structured_error.get("error_message") or json.dumps(structured_error, sort_keys=True))
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1


if __name__ == "__main__":
    sys.exit(main())
