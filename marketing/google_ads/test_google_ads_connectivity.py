#!/usr/bin/env python3
"""Safe read-only Google Ads API connectivity check for JSM reporting."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    load_dotenv = None


REPO_ROOT = Path(__file__).resolve().parents[2]


def normalize_customer_id(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def date_range(days: int) -> tuple[str, str]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=max(1, days) - 1)
    return start.isoformat(), end.isoformat()


def required_config() -> dict[str, str]:
    return {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip(),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", "").strip(),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "").strip(),
        "customer_id": normalize_customer_id(os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")),
    }


def load_client(config: dict[str, str]):
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as exc:
        raise RuntimeError("google-ads Python package is not installed.") from exc

    client_config = {
        "developer_token": config["developer_token"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": config["refresh_token"],
        "use_proto_plus": True,
    }
    login_customer_id = normalize_customer_id(os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""))
    if login_customer_id:
        client_config["login_customer_id"] = login_customer_id
    return GoogleAdsClient.load_from_dict(client_config)


def google_ads_error_payload(error: Exception) -> dict[str, object]:
    payload: dict[str, object] = {
        "type": type(error).__name__,
        "message": str(error),
    }
    if hasattr(error, "request_id"):
        payload["request_id"] = getattr(error, "request_id", "")
    failure = getattr(error, "failure", None)
    errors = getattr(failure, "errors", None)
    if errors:
        payload["errors"] = []
        for item in errors:
            payload["errors"].append(
                {
                    "message": getattr(item, "message", ""),
                    "error_code": str(getattr(item, "error_code", "")),
                    "trigger": str(getattr(item, "trigger", "")),
                    "location": str(getattr(item, "location", "")),
                }
            )
    return payload


def query_account(service, customer_id: str) -> dict[str, str]:
    query = """
      SELECT
        customer.id,
        customer.descriptive_name,
        customer.currency_code,
        customer.time_zone
      FROM customer
      LIMIT 1
    """
    rows = list(service.search(customer_id=customer_id, query=query))
    if not rows:
        return {}
    row = rows[0]
    return {
        "customer_id": str(row.customer.id),
        "customer_name": row.customer.descriptive_name,
        "currency_code": row.customer.currency_code,
        "time_zone": row.customer.time_zone,
    }


def query_campaigns(service, customer_id: str, days: int) -> list[dict[str, object]]:
    start, end = date_range(days)
    query = f"""
      SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value
      FROM campaign
      WHERE segments.date BETWEEN '{start}' AND '{end}'
      ORDER BY metrics.cost_micros DESC
      LIMIT 25
    """
    rows = []
    for row in service.search(customer_id=customer_id, query=query):
        rows.append(
            {
                "campaign_id": str(row.campaign.id),
                "campaign_name": row.campaign.name,
                "campaign_status": row.campaign.status.name,
                "impressions": int(row.metrics.impressions or 0),
                "clicks": int(row.metrics.clicks or 0),
                "cost": round(float(row.metrics.cost_micros or 0) / 1_000_000, 2),
                "conversions": float(row.metrics.conversions or 0),
                "conversion_value": float(row.metrics.conversions_value or 0),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, choices=[1, 7, 30, 90])
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    args = parser.parse_args()

    if load_dotenv and args.env_file.exists():
        load_dotenv(args.env_file)

    config = required_config()
    missing = [key for key, value in config.items() if not value]
    if missing:
        print(json.dumps({"ok": False, "stage": "configuration", "missing": missing}, indent=2))
        return 2

    try:
        client = load_client(config)
        service = client.get_service("GoogleAdsService")
        payload = {
            "ok": True,
            "stage": "reporting",
            "account": query_account(service, config["customer_id"]),
            "campaigns": query_campaigns(service, config["customer_id"], args.days),
        }
        print(json.dumps(payload, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "stage": "google_ads_api", "error": google_ads_error_payload(error)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
