#!/usr/bin/env python3
"""Deploy the approved JSM Cooperative Google Ads campaign package.

Dry-run is the default. Live creation requires --apply, a valid Google Ads
API configuration, a customer ID, and the official google-ads Python package.

Guardrails:
- exact campaign-name idempotency before creating anything
- new campaigns are constructed PAUSED
- components are verified by querying Google Ads back after mutation
- campaigns are enabled only after validation unless --leave-paused is passed
- no deletion or modification of existing campaigns
- no credentials are printed or written to reports
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
CONFIG = HERE / "campaigns.yaml"
KEYWORDS = HERE / "keywords.csv"
NEGATIVES = HERE / "negative_keywords.csv"
RSAS = HERE / "responsive_search_ads.csv"
ASSETS = HERE / "assets.csv"
DEPLOYMENT_JSON = HERE / "deployment_report.json"
DEPLOYMENT_MD = HERE / "deployment_report.md"
REGISTRY_CSV = HERE / "live_campaign_registry.csv"

DAILY_BUDGET_MICROS = 250_000_000

LANGUAGE_CONSTANTS = {
    "English": "languageConstants/1000",
    "Spanish": "languageConstants/1003",
}

# Launch geography defaults from the approved package's recommendation text.
# They are intentionally broad for travel/book discovery and can be narrowed
# after search-term and conversion data. IDs are Google geo target constants.
ENGLISH_GEO_TARGETS = {
    "United States": "geoTargetConstants/2840",
    "United Kingdom": "geoTargetConstants/2826",
    "Ireland": "geoTargetConstants/2372",
    "Canada": "geoTargetConstants/2124",
    "Australia": "geoTargetConstants/2036",
    "Spain": "geoTargetConstants/2724",
}
SPANISH_GEO_TARGETS = {
    "Spain": "geoTargetConstants/2724",
}


@dataclass
class CampaignBuild:
    config: dict[str, Any]
    keywords: list[dict[str, str]] = field(default_factory=list)
    negatives: list[dict[str, str]] = field(default_factory=list)
    rsas: list[dict[str, str]] = field(default_factory=list)
    assets: list[dict[str, str]] = field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_customer_id(customer_id: str) -> str:
    return re.sub(r"\D", "", customer_id or "")


def final_url_without_query(final_url: str) -> str:
    parsed = urlsplit(final_url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", parsed.fragment))


def validate_url(url: str) -> tuple[int, str]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 JSMAdsDeploy"})
    with urlopen(req, timeout=15) as response:
        return response.status, response.geturl()


def build_package(config: dict[str, Any]) -> dict[str, CampaignBuild]:
    keywords = read_csv(KEYWORDS)
    negatives = read_csv(NEGATIVES)
    rsas = read_csv(RSAS)
    assets = read_csv(ASSETS)
    builds: dict[str, CampaignBuild] = {}

    for campaign in config["campaigns"]:
        name = campaign["name"]
        builds[name] = CampaignBuild(
            config=campaign,
            keywords=[row for row in keywords if row["Campaign"] == name],
            negatives=[row for row in negatives if row["Campaign"] == name],
            rsas=[row for row in rsas if row["campaign"] == name],
            assets=[row for row in assets if row["Campaign"] == name],
        )

    return builds


def validate_package(config: dict[str, Any], builds: dict[str, CampaignBuild]) -> list[str]:
    errors: list[str] = []
    names = [campaign["name"] for campaign in config["campaigns"]]

    if len(names) != 10:
        errors.append(f"Expected 10 campaigns, found {len(names)}")
    if len(set(names)) != len(names):
        errors.append("Campaign names are not unique")

    for name, build in builds.items():
        if len(build.rsas) != 2:
            errors.append(f"{name}: expected 2 RSA rows, found {len(build.rsas)}")
        if not build.keywords:
            errors.append(f"{name}: no keywords")
        if not build.negatives:
            errors.append(f"{name}: no negative keywords")
        if not build.config["final_url_suffix"].startswith("utm_source=google&utm_medium=cpc"):
            errors.append(f"{name}: missing Google CPC final URL suffix")
        if "after-dark" in build.config["primary_landing_page"] or "before-the-city-wakes" in build.config["primary_landing_page"]:
            errors.append(f"{name}: future-dated landing page configured")

        for rsa in build.rsas:
            for i in range(1, 16):
                text = rsa.get(f"headline {i}", "")
                if text and len(text) > 30:
                    errors.append(f"{name}: headline {i} too long: {text}")
            for i in range(1, 5):
                text = rsa.get(f"description {i}", "")
                if text and len(text) > 90:
                    errors.append(f"{name}: description {i} too long")
            if len(rsa.get("path 1", "")) > 15 or len(rsa.get("path 2", "")) > 15:
                errors.append(f"{name}: display path exceeds 15 characters")

    return errors


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


def missing_auth_requirements(google_ads_yaml: Path | None, customer_id: str) -> list[str]:
    missing: list[str] = []

    try:
        has_google_ads_package = importlib.util.find_spec("google.ads.googleads.client") is not None
    except ModuleNotFoundError:
        has_google_ads_package = False

    if not has_google_ads_package:
        missing.append("google-ads Python package")

    if not customer_id:
        missing.append("Google Ads customer ID")

    if google_ads_yaml:
        if not google_ads_yaml.exists():
            missing.append(f"google-ads.yaml at {google_ads_yaml}")
        return missing

    required_env = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
    ]
    for key in required_env:
        if not os.getenv(key):
            missing.append(key)

    return missing


def gaql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def search_exact_campaigns(client: Any, customer_id: str, campaign_names: list[str]) -> dict[str, dict[str, Any]]:
    service = client.get_service("GoogleAdsService")
    quoted = ", ".join(f"'{gaql_string(name)}'" for name in campaign_names)
    query = f"""
        SELECT
          campaign.id,
          campaign.name,
          campaign.status,
          campaign.advertising_channel_type,
          campaign_budget.id,
          campaign_budget.amount_micros
        FROM campaign
        WHERE campaign.name IN ({quoted})
    """
    found: dict[str, dict[str, Any]] = {}
    for row in service.search(customer_id=customer_id, query=query):
        found[row.campaign.name] = {
            "campaign_id": str(row.campaign.id),
            "campaign_resource": row.campaign.resource_name,
            "status": row.campaign.status.name,
            "channel": row.campaign.advertising_channel_type.name,
            "budget_id": str(row.campaign_budget.id),
            "budget_micros": int(row.campaign_budget.amount_micros),
        }
    return found


def create_budget(client: Any, customer_id: str, name: str, amount_micros: int) -> str:
    operation = client.get_type("CampaignBudgetOperation")
    budget = operation.create
    budget.name = name
    budget.amount_micros = amount_micros
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.explicitly_shared = False
    return client.get_service("CampaignBudgetService").mutate_campaign_budgets(
        customer_id=customer_id,
        operations=[operation],
    ).results[0].resource_name


def create_campaign(client: Any, customer_id: str, build: CampaignBuild, budget_resource: str, leave_paused: bool) -> str:
    operation = client.get_type("CampaignOperation")
    campaign = operation.create
    campaign.name = build.config["name"]
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.campaign_budget = budget_resource
    campaign.final_url_suffix = build.config["final_url_suffix"]
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = False
    campaign.network_settings.target_content_network = False
    campaign.network_settings.target_partner_search_network = False
    campaign.maximize_clicks.target_spend_micros = 0
    return client.get_service("CampaignService").mutate_campaigns(
        customer_id=customer_id,
        operations=[operation],
    ).results[0].resource_name


def create_campaign_criteria(client: Any, customer_id: str, campaign_resource: str, language: str) -> list[str]:
    operations = []
    lang_constant = LANGUAGE_CONSTANTS[language]
    geo_targets = SPANISH_GEO_TARGETS if language == "Spanish" else ENGLISH_GEO_TARGETS

    language_operation = client.get_type("CampaignCriterionOperation")
    language_criterion = language_operation.create
    language_criterion.campaign = campaign_resource
    language_criterion.language.language_constant = lang_constant
    operations.append(language_operation)

    for geo_resource in geo_targets.values():
        geo_operation = client.get_type("CampaignCriterionOperation")
        geo_criterion = geo_operation.create
        geo_criterion.campaign = campaign_resource
        geo_criterion.location.geo_target_constant = geo_resource
        operations.append(geo_operation)

    response = client.get_service("CampaignCriterionService").mutate_campaign_criteria(
        customer_id=customer_id,
        operations=operations,
    )
    return [result.resource_name for result in response.results]


def create_ad_group(client: Any, customer_id: str, build: CampaignBuild, campaign_resource: str) -> str:
    operation = client.get_type("AdGroupOperation")
    ad_group = operation.create
    ad_group.name = build.config["ad_groups"][0]["name"]
    ad_group.campaign = campaign_resource
    ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
    ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    return client.get_service("AdGroupService").mutate_ad_groups(
        customer_id=customer_id,
        operations=[operation],
    ).results[0].resource_name


def keyword_match_type(client: Any, label: str):
    if label.lower().startswith("exact"):
        return client.enums.KeywordMatchTypeEnum.EXACT
    return client.enums.KeywordMatchTypeEnum.PHRASE


def create_keywords(client: Any, customer_id: str, build: CampaignBuild, ad_group_resource: str) -> list[str]:
    operations = []
    for row in build.keywords:
        operation = client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = ad_group_resource
        criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.keyword.text = row["Keyword"]
        criterion.keyword.match_type = keyword_match_type(client, row["Match Type"])
        criterion.final_urls.append(build.config["final_url"].split("?")[0])
        operations.append(operation)
    response = client.get_service("AdGroupCriterionService").mutate_ad_group_criteria(
        customer_id=customer_id,
        operations=operations,
    )
    return [result.resource_name for result in response.results]


def create_negative_keywords(client: Any, customer_id: str, build: CampaignBuild, campaign_resource: str) -> list[str]:
    operations = []
    for row in build.negatives:
        operation = client.get_type("CampaignCriterionOperation")
        criterion = operation.create
        criterion.campaign = campaign_resource
        criterion.negative = True
        criterion.keyword.text = row["Negative Keyword"]
        criterion.keyword.match_type = keyword_match_type(client, row["Match Type"])
        operations.append(operation)
    response = client.get_service("CampaignCriterionService").mutate_campaign_criteria(
        customer_id=customer_id,
        operations=operations,
    )
    return [result.resource_name for result in response.results]


def add_text_assets(asset_collection: Any, texts: list[str]) -> None:
    for text in texts:
        if not text:
            continue
        asset = asset_collection.add()
        asset.text = text


def create_responsive_search_ads(client: Any, customer_id: str, build: CampaignBuild, ad_group_resource: str) -> list[str]:
    operations = []
    for row in build.rsas:
        operation = client.get_type("AdGroupAdOperation")
        ad_group_ad = operation.create
        ad_group_ad.ad_group = ad_group_resource
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
        ad = ad_group_ad.ad
        ad.final_urls.append(final_url_without_query(row["final URL"]))
        ad.path1 = row["path 1"]
        ad.path2 = row["path 2"]
        add_text_assets(ad.responsive_search_ad.headlines, [row.get(f"headline {i}", "") for i in range(1, 16)])
        add_text_assets(ad.responsive_search_ad.descriptions, [row.get(f"description {i}", "") for i in range(1, 5)])
        operations.append(operation)
    response = client.get_service("AdGroupAdService").mutate_ad_group_ads(
        customer_id=customer_id,
        operations=operations,
    )
    return [result.resource_name for result in response.results]


def create_asset(client: Any, customer_id: str, row: dict[str, str]) -> tuple[str, str]:
    operation = client.get_type("AssetOperation")
    asset = operation.create
    asset.name = f"JSM {row['Asset Type']} - {row['Text'][:40]} - {now_iso()}"

    if row["Asset Type"] == "Sitelink":
        asset.sitelink_asset.link_text = row["Text"]
        asset.sitelink_asset.description1 = row["Description 1"]
        asset.sitelink_asset.description2 = row["Description 2"]
        asset.final_urls.append(row["Final URL"])
        field_type = "SITELINK"
    elif row["Asset Type"] == "Callout":
        asset.callout_asset.callout_text = row["Text"]
        field_type = "CALLOUT"
    else:
        # Structured snippet headers are constrained by Google. Use a broadly
        # supported header while preserving values from the source package.
        header, _, values = row["Text"].partition(":")
        asset.structured_snippet_asset.header = "Types" if header else "Types"
        for value in [part.strip() for part in values.split(",") if part.strip()]:
            asset.structured_snippet_asset.values.append(value)
        field_type = "STRUCTURED_SNIPPET"

    response = client.get_service("AssetService").mutate_assets(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name, field_type


def create_and_attach_assets(client: Any, customer_id: str, build: CampaignBuild, campaign_resource: str) -> list[str]:
    attach_operations = []
    asset_resources: list[str] = []
    for row in build.assets:
        asset_resource, field_type_name = create_asset(client, customer_id, row)
        asset_resources.append(asset_resource)
        operation = client.get_type("CampaignAssetOperation")
        campaign_asset = operation.create
        campaign_asset.campaign = campaign_resource
        campaign_asset.asset = asset_resource
        campaign_asset.field_type = getattr(client.enums.AssetFieldTypeEnum, field_type_name)
        attach_operations.append(operation)

    if attach_operations:
        client.get_service("CampaignAssetService").mutate_campaign_assets(
            customer_id=customer_id,
            operations=attach_operations,
        )
    return asset_resources


def validate_created_campaign(client: Any, customer_id: str, campaign_name: str) -> dict[str, Any]:
    service = client.get_service("GoogleAdsService")
    campaign_query = f"""
      SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.advertising_channel_type,
        campaign.final_url_suffix,
        campaign_budget.id,
        campaign_budget.amount_micros,
        campaign.bidding_strategy_type
      FROM campaign
      WHERE campaign.name = '{gaql_string(campaign_name)}'
      LIMIT 1
    """
    rows = list(service.search(customer_id=customer_id, query=campaign_query))
    if not rows:
        return {"ok": False, "errors": ["campaign not found"]}
    row = rows[0]
    campaign_id = str(row.campaign.id)

    counts: dict[str, int] = {}
    count_queries = {
        "ad_groups": f"SELECT ad_group.id FROM ad_group WHERE campaign.id = {campaign_id}",
        "keywords": f"SELECT ad_group_criterion.criterion_id FROM keyword_view WHERE campaign.id = {campaign_id}",
        "negative_keywords": f"SELECT campaign_criterion.criterion_id FROM campaign_criterion WHERE campaign.id = {campaign_id} AND campaign_criterion.negative = TRUE",
        "rsas": f"SELECT ad_group_ad.ad.id FROM ad_group_ad WHERE campaign.id = {campaign_id} AND ad_group_ad.ad.type = RESPONSIVE_SEARCH_AD",
        "assets": f"SELECT campaign_asset.asset FROM campaign_asset WHERE campaign.id = {campaign_id}",
    }
    for key, query in count_queries.items():
        counts[key] = sum(1 for _ in service.search(customer_id=customer_id, query=query))

    errors = []
    if row.campaign.advertising_channel_type.name != "SEARCH":
        errors.append("campaign is not SEARCH")
    if int(row.campaign_budget.amount_micros) != DAILY_BUDGET_MICROS:
        errors.append(f"budget is {row.campaign_budget.amount_micros}, expected {DAILY_BUDGET_MICROS}")
    if counts["ad_groups"] != 1:
        errors.append(f"expected 1 ad group, found {counts['ad_groups']}")
    if counts["rsas"] != 2:
        errors.append(f"expected 2 RSAs, found {counts['rsas']}")

    return {
        "ok": not errors,
        "errors": errors,
        "campaign_id": campaign_id,
        "campaign_resource": row.campaign.resource_name,
        "status": row.campaign.status.name,
        "budget_id": str(row.campaign_budget.id),
        "budget_micros": int(row.campaign_budget.amount_micros),
        "bidding_strategy": row.campaign.bidding_strategy_type.name,
        "counts": counts,
    }


def enable_campaign(client: Any, customer_id: str, campaign_resource: str) -> None:
    operation = client.get_type("CampaignOperation")
    campaign = operation.update
    campaign.resource_name = campaign_resource
    campaign.status = client.enums.CampaignStatusEnum.ENABLED
    client.copy_from(operation.update_mask, {"paths": ["status"]})
    client.get_service("CampaignService").mutate_campaigns(customer_id=customer_id, operations=[operation])


def write_reports(report: dict[str, Any]) -> None:
    DEPLOYMENT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Google Ads Deployment Report",
        "",
        f"- Created at: `{report['created_at']}`",
        f"- Customer ID: `{report.get('customer_id', 'unavailable')}`",
        f"- Mode: `{report['mode']}`",
        f"- Overall status: `{report['status']}`",
        f"- Daily budget per new campaign: `$250`",
        f"- Total intended daily budget: `$2,500`",
        "",
        "## Campaigns",
        "",
    ]
    for item in report.get("campaigns", []):
        lines.extend(
            [
                f"### {item['campaign_name']}",
                f"- Campaign ID: `{item.get('campaign_id', '')}`",
                f"- Status: `{item.get('final_status', item.get('status', ''))}`",
                f"- Budget resource: `{item.get('budget_resource', '')}`",
                f"- Ad group ID: `{item.get('ad_group_id', '')}`",
                f"- RSA IDs: `{', '.join(item.get('ad_ids', []))}`",
                f"- Keywords: `{item.get('keyword_count', 0)}`",
                f"- Negatives: `{item.get('negative_count', 0)}`",
                f"- Assets: `{item.get('asset_count', 0)}`",
                f"- Validation: `{item.get('validation_status', '')}`",
                "",
            ]
        )
    if report.get("missing_auth"):
        lines.extend(["## Authentication Missing", ""])
        lines.extend(f"- {item}" for item in report["missing_auth"])
        lines.append("")
    DEPLOYMENT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_registry(report: dict[str, Any]) -> None:
    fields = [
        "Campaign Name",
        "Google Ads Campaign ID",
        "Status",
        "Daily Budget",
        "Ad Group ID",
        "RSA 1 ID",
        "RSA 2 ID",
        "Landing Page",
        "UTM Campaign",
        "Bidding Strategy",
        "Language",
        "Created At",
    ]
    with REGISTRY_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report.get("campaigns", []):
            ad_ids = item.get("ad_ids", [])
            writer.writerow(
                {
                    "Campaign Name": item["campaign_name"],
                    "Google Ads Campaign ID": item.get("campaign_id", ""),
                    "Status": item.get("final_status", item.get("status", "")),
                    "Daily Budget": "$250",
                    "Ad Group ID": item.get("ad_group_id", ""),
                    "RSA 1 ID": ad_ids[0] if len(ad_ids) > 0 else "",
                    "RSA 2 ID": ad_ids[1] if len(ad_ids) > 1 else "",
                    "Landing Page": item.get("landing_page", ""),
                    "UTM Campaign": item.get("utm_campaign", ""),
                    "Bidding Strategy": item.get("bidding_strategy", ""),
                    "Language": item.get("language", ""),
                    "Created At": item.get("created_at", ""),
                }
            )


def extract_id(resource_name: str) -> str:
    return resource_name.rsplit("/", 1)[-1] if resource_name else ""


def dry_run(config: dict[str, Any], builds: dict[str, CampaignBuild], daily_budget_micros: int) -> None:
    print(f"Base domain: {config['base_domain']}")
    print(f"Campaigns to deploy: {len(builds)}")
    print(f"Average daily budget per campaign: ${daily_budget_micros / 1_000_000:,.2f}")
    print(f"Total configured daily budget: ${(daily_budget_micros * len(builds)) / 1_000_000:,.2f}")
    for build in builds.values():
        print(
            "DRY RUN | "
            f"{build.config['name']} | "
            f"{build.config['language']} | "
            f"{len(build.keywords)} keywords | "
            f"{len(build.negatives)} negatives | "
            f"{len(build.rsas)} RSAs | "
            f"{build.config['primary_landing_page']}"
        )


def deploy(args: argparse.Namespace, config: dict[str, Any], builds: dict[str, CampaignBuild]) -> dict[str, Any]:
    customer_id = normalize_customer_id(args.customer_id)
    missing = missing_auth_requirements(args.google_ads_yaml, customer_id)
    if missing:
        raise RuntimeError("missing " + ", ".join(missing))

    client = load_google_ads_client(args.google_ads_yaml)
    names = list(builds.keys())
    existing = search_exact_campaigns(client, customer_id, names)
    report = {
        "created_at": now_iso(),
        "mode": "apply",
        "status": "IN_PROGRESS",
        "customer_id": customer_id,
        "daily_budget_micros": args.daily_budget_micros,
        "total_budget_micros": args.daily_budget_micros * len(builds),
        "campaigns": [],
    }

    for name, build in builds.items():
        item = {
            "campaign_name": name,
            "landing_page": build.config["primary_landing_page"],
            "utm_campaign": build.config["utm_campaign"],
            "language": build.config["language"],
            "created_at": now_iso(),
            "keyword_count": len(build.keywords),
            "negative_count": len(build.negatives),
            "asset_count": len(build.assets),
            "ad_ids": [],
            "final_url": build.config["final_url"],
            "bidding_strategy": "MAXIMIZE_CLICKS",
        }
        report["campaigns"].append(item)

        if name in existing:
            item.update(existing[name])
            item["validation_status"] = "EXISTING_NOT_DUPLICATED"
            item["final_status"] = existing[name]["status"]
            continue

        budget_resource = create_budget(client, customer_id, f"{name} | $250/day | {now_iso()}", args.daily_budget_micros)
        campaign_resource = create_campaign(client, customer_id, build, budget_resource, args.leave_paused)
        create_campaign_criteria(client, customer_id, campaign_resource, build.config["language"])
        ad_group_resource = create_ad_group(client, customer_id, build, campaign_resource)
        keyword_resources = create_keywords(client, customer_id, build, ad_group_resource)
        negative_resources = create_negative_keywords(client, customer_id, build, campaign_resource)
        ad_resources = create_responsive_search_ads(client, customer_id, build, ad_group_resource)
        asset_resources = create_and_attach_assets(client, customer_id, build, campaign_resource)

        validation = validate_created_campaign(client, customer_id, name)
        item.update(
            {
                "campaign_id": validation.get("campaign_id", ""),
                "campaign_resource": campaign_resource,
                "budget_resource": budget_resource,
                "budget_id": extract_id(budget_resource),
                "ad_group_id": extract_id(ad_group_resource),
                "keyword_resource_count": len(keyword_resources),
                "negative_resource_count": len(negative_resources),
                "ad_ids": [extract_id(resource) for resource in ad_resources],
                "asset_resource_count": len(asset_resources),
                "validation_status": "PASS" if validation["ok"] else "FAIL",
                "validation_errors": validation.get("errors", []),
                "bidding_strategy": validation.get("bidding_strategy", "MAXIMIZE_CLICKS"),
            }
        )

        if validation["ok"] and not args.leave_paused:
            status_code, resolved_url = validate_url(final_url_without_query(build.config["final_url"]))
            item["landing_url_status"] = status_code
            item["landing_url_resolved"] = resolved_url
            if status_code == 200:
                enable_campaign(client, customer_id, campaign_resource)
                final_validation = validate_created_campaign(client, customer_id, name)
                item["final_status"] = final_validation.get("status", "UNKNOWN")
            else:
                item["final_status"] = "PAUSED"
                item["validation_status"] = "FAIL"
                item.setdefault("validation_errors", []).append(f"landing URL returned {status_code}")
        else:
            item["final_status"] = "PAUSED"

    failures = [item for item in report["campaigns"] if item.get("validation_status") == "FAIL"]
    report["status"] = "PARTIAL_FAILURE" if failures else "SUCCESS"
    write_reports(report)
    write_registry(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=CONFIG, type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Validate and print intended deployment. This is the default.")
    parser.add_argument("--apply", action="store_true", help="Create/verify campaigns in Google Ads.")
    parser.add_argument("--leave-paused", action="store_true", help="Do not enable campaigns after validation.")
    parser.add_argument("--google-ads-yaml", type=Path, help="Path to google-ads.yaml. If omitted, environment config is used.")
    parser.add_argument("--customer-id", help="Google Ads customer ID, with or without dashes.")
    parser.add_argument("--daily-budget-micros", type=int, default=DAILY_BUDGET_MICROS)
    args = parser.parse_args()

    config = load_json_config(args.config)
    builds = build_package(config)
    errors = validate_package(config, builds)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    if not args.apply:
        dry_run(config, builds, args.daily_budget_micros)
        return 0

    try:
        report = deploy(args, config, builds)
    except RuntimeError as exc:
        report = {
            "created_at": now_iso(),
            "mode": "apply",
            "status": "BLOCKED_AUTHENTICATION",
            "customer_id": normalize_customer_id(args.customer_id or ""),
            "missing_auth": [str(exc)],
            "campaigns": [],
        }
        write_reports(report)
        write_registry(report)
        print(f"BLOCKED: {exc}")
        return 2

    print(f"Deployment status: {report['status']}")
    print(f"Campaigns in report: {len(report['campaigns'])}")
    return 0 if report["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
