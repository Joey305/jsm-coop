"""Google Data Manager ingestion helpers for signed-book purchases."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2 import service_account


DATA_MANAGER_SCOPE = "https://www.googleapis.com/auth/datamanager"
EVENTS_INGEST_URL = "https://datamanager.googleapis.com/v1/events:ingest"
ACCOUNT_TYPE_GOOGLE_ADS = "GOOGLE_ADS"
DEFAULT_QUOTA_PROJECT = "jsmcoop-ads-api-305-2026"


class DataManagerConfigError(RuntimeError):
    """Raised when Data Manager is missing required safe configuration."""


@dataclass
class DataManagerResult:
    status: str
    http_status: int | None = None
    request_id: str = ""
    reason: str = ""
    message: str = ""
    validate_only: bool = True
    payload_accepted: bool = False
    retryable: bool = False
    destination: dict[str, Any] | None = None
    field_warnings: list[dict[str, Any]] | None = None
    error: dict[str, Any] | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "http_status": self.http_status,
            "request_id": self.request_id,
            "reason": self.reason,
            "message": self.message[:500] if self.message else "",
            "validate_only": self.validate_only,
            "payload_accepted": self.payload_accepted,
            "retryable": self.retryable,
            "destination": self.destination or {},
            "field_warnings": self.field_warnings or [],
            "error": self.error or {},
        }


def normalize_digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def redacted_digits(value: Any) -> str:
    digits = normalize_digits(value)
    if not digits:
        return ""
    if len(digits) <= 4:
        return "<redacted>"
    return f"<redacted:{len(digits)} digits ending {digits[-4:]}>"


def sanitize(value: Any, sensitive_values: list[str] | None = None) -> Any:
    sensitive_values = [str(item) for item in sensitive_values or [] if item]
    if isinstance(value, dict):
        return {key: sanitize(item, sensitive_values) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item, sensitive_values) for item in value]
    if not isinstance(value, str):
        return value

    redacted = value
    for sensitive in sensitive_values:
        redacted = redacted.replace(sensitive, redacted_digits(sensitive))
    return re.sub(r"\b\d{5,}\b", lambda match: redacted_digits(match.group(0)), redacted)


def config_value(config: dict[str, Any] | None, key: str, default: str = "") -> str:
    if config and config.get(key) not in {None, ""}:
        return str(config.get(key)).strip()
    return os.getenv(key, default).strip()


def validate_only_from_config(config: dict[str, Any] | None) -> bool:
    if config and config.get("TESTING"):
        return True
    environment = (config_value(config, "ANALYTICS_ENVIRONMENT") or os.getenv("FLASK_ENV") or "").lower()
    default = environment not in {"production", "prod"}
    return parse_bool(config_value(config, "GOOGLE_DATA_MANAGER_VALIDATE_ONLY"), default)


def customer_id_from_config(config: dict[str, Any] | None) -> str:
    return normalize_digits(config_value(config, "GOOGLE_ADS_CUSTOMER_ID"))


def purchase_conversion_action_id_from_config(config: dict[str, Any] | None) -> str:
    action_id = normalize_digits(
        config_value(config, "GOOGLE_ADS_SIGNED_BOOK_PURCHASE_CONVERSION_ACTION_ID")
    )
    if action_id:
        return action_id
    return normalize_digits(
        config_value(config, "GOOGLE_ADS_PAYPAL_PURCHASE_CONVERSION_ACTION_ID")
    )


def quota_project_from_config(config: dict[str, Any] | None) -> str:
    return config_value(config, "GOOGLE_DATA_MANAGER_QUOTA_PROJECT", DEFAULT_QUOTA_PROJECT)


def build_destination(customer_id: str, conversion_action_id: str, login_customer_id: str = "") -> dict[str, Any]:
    login_customer_id = normalize_digits(login_customer_id) or customer_id
    account = {"accountType": ACCOUNT_TYPE_GOOGLE_ADS, "accountId": customer_id}
    return {
        "operatingAccount": account,
        "loginAccount": {
            "accountType": ACCOUNT_TYPE_GOOGLE_ADS,
            "accountId": login_customer_id,
        },
        "productDestinationId": conversion_action_id,
    }


def destination_summary(destination: dict[str, Any], validate_only: bool, quota_project: str) -> dict[str, Any]:
    operating = destination.get("operatingAccount") or {}
    login = destination.get("loginAccount") or {}
    return {
        "operating_account_type": operating.get("accountType", ""),
        "operating_account_id": redacted_digits(operating.get("accountId", "")),
        "login_account_type": login.get("accountType", ""),
        "login_account_id": redacted_digits(login.get("accountId", "")),
        "product_destination_type": "GOOGLE_ADS_CONVERSION_ACTION_ID",
        "conversion_action_id": redacted_digits(destination.get("productDestinationId", "")),
        "validate_only": "yes" if validate_only else "no",
        "quota_project": quota_project,
        "endpoint": EVENTS_INGEST_URL,
    }


def parse_event_timestamp(value: Any) -> str:
    if not value:
        return utc_now_iso()
    text = str(value).strip()
    if not text:
        return utc_now_iso()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except ValueError:
        return text


def purchase_transaction_id(record: dict[str, Any]) -> str:
    return (
        str(record.get("capture_id") or "").strip()
        or str(record.get("resource_id") or "").strip()
        or str(record.get("order_id") or "").strip()
        or str(record.get("event_id") or "").strip()
        or str(record.get("checkout_id") or "").strip()
    )


def purchase_ad_identifiers(record: dict[str, Any]) -> dict[str, str]:
    identifiers = {}
    for key in ("gclid", "gbraid", "wbraid"):
        value = str(record.get(key) or "").strip()
        if value:
            identifiers[key] = value
    return identifiers


def build_purchase_event(record: dict[str, Any]) -> dict[str, Any]:
    transaction_id = purchase_transaction_id(record)
    if not transaction_id:
        raise DataManagerConfigError("Missing stable PayPal transaction ID for Data Manager event.")

    try:
        conversion_value = float(record.get("value") or 0)
    except (TypeError, ValueError):
        conversion_value = 0.0

    currency = str(record.get("currency") or "").strip().upper()
    if not currency:
        raise DataManagerConfigError("Missing PayPal transaction currency for Data Manager event.")

    event = {
        "transactionId": transaction_id,
        "eventTimestamp": parse_event_timestamp(
            record.get("completed_at") or record.get("event_create_time") or record.get("received_at")
        ),
        "eventSource": "WEB",
        "conversionValue": conversion_value,
        "conversionCount": 1,
        "currency": currency,
    }

    ad_identifiers = purchase_ad_identifiers(record)
    if ad_identifiers:
        event["adIdentifiers"] = ad_identifiers
    return event


def build_ingest_payload(
    destination: dict[str, Any],
    event: dict[str, Any],
    validate_only: bool,
) -> dict[str, Any]:
    return {
        "destinations": [destination],
        "events": [event],
        "validateOnly": validate_only,
    }


def service_account_info_from_env() -> dict[str, Any] | None:
    encoded = os.getenv("GOOGLE_DATA_MANAGER_SERVICE_ACCOUNT_JSON_BASE64", "").strip()
    raw = os.getenv("GOOGLE_DATA_MANAGER_SERVICE_ACCOUNT_JSON", "").strip()
    if encoded:
        raw = base64.b64decode(encoded).decode("utf-8")
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as error:
        raise DataManagerConfigError("Invalid Google Data Manager service-account JSON.") from error
    if not isinstance(info, dict):
        raise DataManagerConfigError("Google Data Manager service-account JSON must decode to an object.")
    return info


def load_credentials(config: dict[str, Any] | None = None):
    quota_project = quota_project_from_config(config)
    info = service_account_info_from_env()
    if info:
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=[DATA_MANAGER_SCOPE],
        )
        if quota_project and hasattr(credentials, "with_quota_project"):
            credentials = credentials.with_quota_project(quota_project)
        return credentials

    credentials, _project_id = google.auth.default(
        scopes=[DATA_MANAGER_SCOPE],
        quota_project_id=quota_project or None,
    )
    return credentials


def extract_error(response: Any, sensitive_values: list[str]) -> dict[str, Any]:
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
        error_info["error_message"] = getattr(response, "text", "")
        return sanitize(error_info, sensitive_values)

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

    for header_name in ("x-request-id", "x-google-request-id", "x-goog-request-id"):
        if not error_info["request_id"] and response.headers.get(header_name):
            error_info["request_id"] = response.headers[header_name]
            break

    error_info["structured_error_body"] = body
    return sanitize(error_info, sensitive_values)


def ingest_purchase(
    record: dict[str, Any],
    config: dict[str, Any] | None = None,
    *,
    validate_only: bool | None = None,
    session: Any | None = None,
    timeout: int = 30,
) -> DataManagerResult:
    customer_id = customer_id_from_config(config)
    conversion_action_id = purchase_conversion_action_id_from_config(config)
    login_customer_id = customer_id
    quota_project = quota_project_from_config(config)

    if not customer_id:
        raise DataManagerConfigError("Missing GOOGLE_ADS_CUSTOMER_ID.")
    if not conversion_action_id:
        raise DataManagerConfigError("Missing GOOGLE_ADS_SIGNED_BOOK_PURCHASE_CONVERSION_ACTION_ID.")

    validate = validate_only_from_config(config) if validate_only is None else bool(validate_only)
    destination = build_destination(customer_id, conversion_action_id, login_customer_id)
    summary = destination_summary(destination, validate, quota_project)

    ad_identifiers = purchase_ad_identifiers(record)
    if not ad_identifiers:
        return DataManagerResult(
            status="skipped",
            reason="missing_ad_identifier",
            message="No gclid, gbraid, or wbraid was available for this verified purchase.",
            validate_only=validate,
            destination=summary,
        )

    try:
        event = build_purchase_event(record)
    except DataManagerConfigError as error:
        return DataManagerResult(
            status="skipped",
            reason="missing_purchase_field",
            message=str(error),
            validate_only=validate,
            destination=summary,
        )

    payload = build_ingest_payload(destination, event, validate)
    sensitive_values = [
        customer_id,
        conversion_action_id,
        login_customer_id,
        purchase_transaction_id(record),
        *(ad_identifiers.values()),
    ]

    try:
        active_session = session
        if active_session is None:
            credentials = load_credentials(config)
            credentials.refresh(Request())
            active_session = AuthorizedSession(credentials)
        response = active_session.post(EVENTS_INGEST_URL, json=payload, timeout=timeout)
    except Exception as error:
        return DataManagerResult(
            status="failed",
            reason="request_error",
            message=f"{type(error).__name__}: {error}",
            validate_only=validate,
            destination=summary,
            retryable=True,
        )

    if response.ok:
        try:
            body = response.json()
        except ValueError:
            body = {}
        return DataManagerResult(
            status="validated" if validate else "uploaded",
            http_status=response.status_code,
            request_id=body.get("requestId", ""),
            validate_only=validate,
            payload_accepted=True,
            destination=summary,
            field_warnings=body.get("fieldWarnings", []),
        )

    error = extract_error(response, sensitive_values)
    return DataManagerResult(
        status="failed",
        http_status=response.status_code,
        request_id=error.get("request_id", ""),
        reason=error.get("error_reason", "") or error.get("google_rpc_status", ""),
        message=error.get("error_message", ""),
        validate_only=validate,
        payload_accepted=False,
        retryable=response.status_code in {408, 429, 500, 502, 503, 504},
        destination=summary,
        error=error,
    )
