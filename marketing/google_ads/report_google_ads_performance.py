#!/usr/bin/env python3
"""Read-only performance reporting for the JSM Google Ads campaign registry."""

from __future__ import annotations

import argparse
import csv
import re
from datetime import date, timedelta
from pathlib import Path


HERE = Path(__file__).resolve().parent
REGISTRY_CSV = HERE / "live_campaign_registry.csv"
OUTPUT_CSV = HERE / "performance_latest.csv"


def normalize_customer_id(customer_id: str) -> str:
    return re.sub(r"\D", "", customer_id or "")


def load_google_ads_client(google_ads_yaml: Path | None):
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as exc:
        raise RuntimeError("google-ads Python package is not installed") from exc

    if google_ads_yaml:
        if not google_ads_yaml.exists():
            raise RuntimeError(f"google-ads.yaml not found: {google_ads_yaml}")
        return GoogleAdsClient.load_from_storage(str(google_ads_yaml))

    return GoogleAdsClient.load_from_env()


def read_registry() -> list[dict[str, str]]:
    if not REGISTRY_CSV.exists():
        raise RuntimeError("live_campaign_registry.csv does not exist yet")
    with REGISTRY_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows = [row for row in rows if row.get("Google Ads Campaign ID")]
    if not rows:
        raise RuntimeError("live_campaign_registry.csv has no campaign IDs yet")
    return rows


def date_range(days: int) -> tuple[str, str]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def gaql_ids(ids: list[str]) -> str:
    return ", ".join(ids)


def query_performance(client, customer_id: str, campaign_ids: list[str], days: int) -> list[dict[str, str]]:
    start, end = date_range(days)
    service = client.get_service("GoogleAdsService")
    query = f"""
      SELECT
        segments.date,
        campaign.id,
        campaign.name,
        ad_group.id,
        ad_group.name,
        ad_group_criterion.keyword.text,
        ad_group_criterion.keyword.match_type,
        metrics.impressions,
        metrics.clicks,
        metrics.ctr,
        metrics.average_cpc,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_from_interactions_rate,
        metrics.cost_per_conversion
      FROM keyword_view
      WHERE campaign.id IN ({gaql_ids(campaign_ids)})
        AND segments.date BETWEEN '{start}' AND '{end}'
      ORDER BY segments.date DESC, campaign.name, ad_group.name
    """
    rows = []
    for row in service.search(customer_id=customer_id, query=query):
        rows.append(
            {
                "date": row.segments.date,
                "campaign_id": str(row.campaign.id),
                "campaign": row.campaign.name,
                "ad_group_id": str(row.ad_group.id),
                "ad_group": row.ad_group.name,
                "keyword": row.ad_group_criterion.keyword.text,
                "match_type": row.ad_group_criterion.keyword.match_type.name,
                "impressions": str(row.metrics.impressions),
                "clicks": str(row.metrics.clicks),
                "ctr": f"{row.metrics.ctr:.6f}",
                "average_cpc": f"{row.metrics.average_cpc / 1_000_000:.2f}",
                "spend": f"{row.metrics.cost_micros / 1_000_000:.2f}",
                "conversions": f"{row.metrics.conversions:.2f}",
                "conversion_rate": f"{row.metrics.conversions_from_interactions_rate:.6f}",
                "cost_per_conversion": f"{row.metrics.cost_per_conversion / 1_000_000:.2f}"
                if row.metrics.cost_per_conversion
                else "",
                "landing_page": "",
                "search_term": "",
            }
        )
    return rows


def write_output(rows: list[dict[str, str]]) -> None:
    fields = [
        "date",
        "campaign_id",
        "campaign",
        "ad_group_id",
        "ad_group",
        "keyword",
        "match_type",
        "search_term",
        "landing_page",
        "impressions",
        "clicks",
        "ctr",
        "average_cpc",
        "spend",
        "conversions",
        "conversion_rate",
        "cost_per_conversion",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, choices=[1, 7, 30])
    parser.add_argument("--google-ads-yaml", type=Path)
    parser.add_argument("--customer-id", required=True)
    args = parser.parse_args()

    customer_id = normalize_customer_id(args.customer_id)
    if not customer_id:
        raise SystemExit("--customer-id is required")

    try:
        registry = read_registry()
        campaign_ids = [row["Google Ads Campaign ID"] for row in registry]
        client = load_google_ads_client(args.google_ads_yaml)
        rows = query_performance(client, customer_id, campaign_ids, args.days)
        write_output(rows)
    except RuntimeError as exc:
        print(f"BLOCKED: {exc}")
        return 2

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
