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


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def env_value(name: str) -> str:
    return (os.getenv(name) or "").strip()


def configured_conversion_action_id() -> str:
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


def api_error_message(response: Any) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()

    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return error.get("message") or json.dumps(error, sort_keys=True)
    return json.dumps(body, sort_keys=True)


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
    result["authentication_result"].update(
        {
            "adc_resolved": bool_text(bool(identity)),
            "service_account_used": identity or "unavailable",
            "adc_default_project_matches_quota_project": bool_text(
                default_project_id == EXPECTED_QUOTA_PROJECT
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
    login_customer_id = normalize_digits(env_value("GOOGLE_ADS_LOGIN_CUSTOMER_ID"))

    missing = []
    if not customer_id:
        missing.append("GOOGLE_ADS_CUSTOMER_ID")
    if not conversion_action_id:
        missing.append("GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_ID")

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

    message = api_error_message(response)
    result["data_manager_api_result"]["jsm_google_ads_destination_reachable"] = "no"
    result["validation_result"]["payload_accepted_in_validation_only"] = "no"
    result["errors"].append(f"API_ERROR: {message}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1


if __name__ == "__main__":
    sys.exit(main())
