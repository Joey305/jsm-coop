import csv
import io
import json
import re
import sqlite3
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCHEMA_VERSION = 1
MAX_ANALYTICS_PAYLOAD_BYTES = 32_000
MAX_BATCH_SIZE = 20

EVENT_NAME_ALIASES = {
    "donation_button_click": "donation_click",
    "newsletter_signup_success": "newsletter_signup",
    "newsletter_signup_submit": "newsletter_signup_attempt",
    "paypal_checkout_started": "direct_checkout_started",
    "paypal_payment_completed": "verified_direct_purchase_completed",
}

VALID_EVENT_NAMES = {
    "page_view",
    "session_start",
    "book_preview_click",
    "camino_subscription_click",
    "camino_subscription_completed",
    "click_coruna_to_book",
    "click_coruna_to_literary_tour",
    "click_literary_tour_to_book",
    "click_signed_copy_cta",
    "click_through_the_lens_article",
    "click_through_the_lens_to_guide",
    "direct_checkout_returned",
    "direct_checkout_started",
    "donation_click",
    "newsletter_form_view",
    "newsletter_signup_attempt",
    "newsletter_signup",
    "newsletter_signup_error",
    "pillar_article_view",
    "pillar_to_book_click",
    "pillar_preview_click",
    "pillar_signed_copy_click",
    "purchase_modal_open",
    "retailer_click_amazon_us",
    "retailer_click_barnes_noble",
    "retailer_click_amazon_es",
    "signed_copy_checkout_click",
    "signed_copy_gallery_interaction",
    "signed_copy_inscription_info_view",
    "signed_copy_page_view",
    "signed_copy_preview_click",
    "signed_copy_promo_click",
    "signed_copy_promo_dismiss",
    "signed_copy_promo_impression",
    "signed_copy_promo_reopen",
    "signed_page_preview_click",
    "verified_direct_purchase_completed",
    "view_coruna_literary_tour",
    "view_coruna_things_to_do",
    "view_through_the_lens",
}

BOOK_ACTION_EVENTS = {
    "book_preview_click",
    "pillar_to_book_click",
    "pillar_preview_click",
    "pillar_signed_copy_click",
    "purchase_modal_open",
    "retailer_click_amazon_us",
    "retailer_click_barnes_noble",
    "retailer_click_amazon_es",
    "signed_copy_checkout_click",
    "signed_copy_preview_click",
    "signed_copy_promo_click",
    "signed_page_preview_click",
    "click_coruna_to_book",
    "click_literary_tour_to_book",
    "click_signed_copy_cta",
}

MEANINGFUL_ACTION_EVENTS = BOOK_ACTION_EVENTS | {
    "direct_checkout_started",
    "direct_checkout_returned",
    "newsletter_signup",
    "donation_click",
    "camino_subscription_click",
    "camino_subscription_completed",
    "click_coruna_to_literary_tour",
    "click_through_the_lens_article",
    "click_through_the_lens_to_guide",
}

EVENT_CATEGORIES = {
    "page_view": "content",
    "session_start": "content",
    "newsletter_form_view": "newsletter",
    "newsletter_signup_attempt": "newsletter",
    "newsletter_signup": "newsletter",
    "newsletter_signup_error": "newsletter",
    "donation_click": "donation",
    "camino_subscription_click": "camino",
    "camino_subscription_completed": "camino",
    "direct_checkout_started": "checkout",
    "direct_checkout_returned": "checkout",
    "verified_direct_purchase_completed": "sales",
}

for _event in BOOK_ACTION_EVENTS:
    EVENT_CATEGORIES.setdefault(_event, "book")
for _event in ("click_coruna_to_literary_tour", "click_through_the_lens_article", "click_through_the_lens_to_guide", "view_coruna_literary_tour", "view_coruna_things_to_do", "view_through_the_lens"):
    EVENT_CATEGORIES.setdefault(_event, "a_coruna")

EVENT_COLUMNS = [
    "event_id",
    "schema_version",
    "event_name",
    "event_category",
    "occurred_at",
    "client_occurred_at",
    "page_path",
    "page_title",
    "landing_page",
    "content_id",
    "content_type",
    "article_slug",
    "series",
    "element_id",
    "element_label",
    "element_type",
    "element_position",
    "destination_url",
    "destination_domain",
    "referrer_url",
    "referrer_domain",
    "source",
    "medium",
    "campaign",
    "term",
    "campaign_content",
    "gclid",
    "gbraid",
    "wbraid",
    "anonymous_session_id",
    "device_category",
    "environment",
    "metadata_json",
]

FILTER_KEYS = {
    "event_name",
    "event_category",
    "page_path",
    "content_type",
    "series",
    "article_slug",
    "element_position",
    "destination_domain",
    "device_category",
    "campaign",
    "source",
    "medium",
    "environment",
}


class AnalyticsValidationError(ValueError):
    pass


class LocalAnalyticsStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=3000")
        return connection

    def _ensure_schema(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    schema_version INTEGER NOT NULL,
                    event_name TEXT NOT NULL,
                    event_category TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    client_occurred_at TEXT,
                    page_path TEXT,
                    page_title TEXT,
                    landing_page TEXT,
                    content_id TEXT,
                    content_type TEXT,
                    article_slug TEXT,
                    series TEXT,
                    element_id TEXT,
                    element_label TEXT,
                    element_type TEXT,
                    element_position TEXT,
                    destination_url TEXT,
                    destination_domain TEXT,
                    referrer_url TEXT,
                    referrer_domain TEXT,
                    source TEXT,
                    medium TEXT,
                    campaign TEXT,
                    term TEXT,
                    campaign_content TEXT,
                    gclid TEXT,
                    gbraid TEXT,
                    wbraid TEXT,
                    anonymous_session_id TEXT,
                    device_category TEXT,
                    environment TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            for column in ("occurred_at", "event_name", "event_category", "page_path", "landing_page", "anonymous_session_id", "campaign", "source", "medium", "device_category", "environment"):
                connection.execute(f"CREATE INDEX IF NOT EXISTS idx_jsm_analytics_{column} ON analytics_events ({column})")

    def store_event(self, event):
        row = {column: event.get(column, "") for column in EVENT_COLUMNS}
        row["metadata_json"] = json.dumps(event.get("metadata") or {}, sort_keys=True)
        row["created_at"] = event["occurred_at"]
        with self.connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO analytics_events (
                        event_id, schema_version, event_name, event_category, occurred_at,
                        client_occurred_at, page_path, page_title, landing_page, content_id,
                        content_type, article_slug, series, element_id, element_label,
                        element_type, element_position, destination_url, destination_domain,
                        referrer_url, referrer_domain, source, medium, campaign, term,
                        campaign_content, gclid, gbraid, wbraid, anonymous_session_id,
                        device_category, environment, metadata_json, created_at
                    )
                    VALUES (
                        :event_id, :schema_version, :event_name, :event_category, :occurred_at,
                        :client_occurred_at, :page_path, :page_title, :landing_page, :content_id,
                        :content_type, :article_slug, :series, :element_id, :element_label,
                        :element_type, :element_position, :destination_url, :destination_domain,
                        :referrer_url, :referrer_domain, :source, :medium, :campaign, :term,
                        :campaign_content, :gclid, :gbraid, :wbraid, :anonymous_session_id,
                        :device_category, :environment, :metadata_json, :created_at
                    )
                    """,
                    row,
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def store_events(self, events):
        inserted = 0
        duplicates = 0
        for event in events:
            if self.store_event(event):
                inserted += 1
            else:
                duplicates += 1
        return {"inserted": inserted, "duplicates": duplicates}

    def query_summary(self, start, end, filters=None):
        previous_start = start - (end - start)
        previous_end = start
        current = self._period_summary(start, end, filters or {})
        previous = self._period_summary(previous_start, previous_end, filters or {})
        current["previous"] = previous["totals"]
        current["comparison"] = {
            key: compare_counts(current["totals"].get(key, 0), previous["totals"].get(key, 0))
            for key in current["totals"]
        }
        return current

    def query_events(self, start, end, filters=None, page=1, page_size=50):
        page = max(1, int(page or 1))
        page_size = max(1, min(200, int(page_size or 50)))
        where, params = self._where(start, end, filters)
        offset = (page - 1) * page_size
        with self.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM analytics_events {where}", params).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM analytics_events {where} ORDER BY occurred_at DESC, id DESC LIMIT ? OFFSET ?",
                [*params, page_size, offset],
            ).fetchall()
        return {
            "events": [event_from_row(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
        }

    def export_events(self, start, end, filters=None):
        result = self.query_events(start, end, filters, page=1, page_size=5000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Time", "Event", "Category", "Source page", "Element", "Position", "Destination", "Campaign", "Source", "Medium", "Device"])
        for event in result["events"]:
            writer.writerow([
                csv_safe(event.get("occurred_at")),
                csv_safe(event.get("event_name")),
                csv_safe(event.get("event_category")),
                csv_safe(event.get("page_path")),
                csv_safe(event.get("element_label")),
                csv_safe(event.get("element_position")),
                csv_safe(event.get("destination_url")),
                csv_safe(event.get("campaign")),
                csv_safe(event.get("source")),
                csv_safe(event.get("medium")),
                csv_safe(event.get("device_category")),
            ])
        return output.getvalue()

    def health_check(self):
        try:
            with self.connect() as connection:
                row = connection.execute("SELECT COUNT(*) AS count, MAX(occurred_at) AS last_recorded_at FROM analytics_events").fetchone()
            return {
                "ok": True,
                "backend": "local sqlite",
                "path": str(self.path),
                "event_count": row["count"],
                "last_recorded_at": row["last_recorded_at"] or "",
            }
        except sqlite3.Error as error:
            return {"ok": False, "backend": "local sqlite", "error": str(error), "event_count": 0, "last_recorded_at": ""}

    def _period_summary(self, start, end, filters):
        events = self._events(start, end, filters)
        page_views = count_events(events, "page_view")
        sessions = len({event["anonymous_session_id"] for event in events if event.get("anonymous_session_id")})
        totals = {
            "page_views": page_views,
            "anonymous_sessions": sessions,
            "meaningful_actions": sum(1 for event in events if event["event_name"] in MEANINGFUL_ACTION_EVENTS),
            "book_actions": sum(1 for event in events if event["event_name"] in BOOK_ACTION_EVENTS),
            "newsletter_form_views": count_events(events, "newsletter_form_view"),
            "newsletter_signup_attempts": count_events(events, "newsletter_signup_attempt"),
            "newsletter_signups": count_events(events, "newsletter_signup"),
            "newsletter_errors": count_events(events, "newsletter_signup_error"),
            "signed_copy_page_views": count_events(events, "signed_copy_page_view") + count_page_prefix(events, "/book/signed"),
            "book_page_views": count_page_prefix(events, "/book"),
            "book_preview_clicks": count_events(events, "book_preview_click") + count_events(events, "signed_copy_preview_click"),
            "purchase_modal_opens": count_events(events, "purchase_modal_open"),
            "signed_promo_impressions": count_events(events, "signed_copy_promo_impression"),
            "signed_promo_clicks": count_events(events, "signed_copy_promo_click"),
            "signed_cta_clicks": count_events(events, "signed_copy_checkout_click") + count_events(events, "click_signed_copy_cta"),
            "retailer_clicks": sum(count_events(events, name) for name in ("retailer_click_amazon_us", "retailer_click_barnes_noble", "retailer_click_amazon_es")),
            "direct_checkout_starts": count_events(events, "direct_checkout_started"),
            "paypal_returns": count_events(events, "direct_checkout_returned"),
            "camino_page_views": count_page_prefix(events, "/novel-subscription"),
            "camino_clicks": count_events(events, "camino_subscription_click"),
            "camino_completions": count_events(events, "camino_subscription_completed"),
            "donation_page_views": count_page_prefix(events, "/donate"),
            "donation_clicks": count_events(events, "donation_click"),
            "a_coruna_page_views": sum(1 for event in events if event["event_name"] == "page_view" and is_a_coruna_path(event.get("page_path", ""))),
            "a_coruna_sessions": len({event["anonymous_session_id"] for event in events if event.get("anonymous_session_id") and is_a_coruna_event(event)}),
            "through_lens_views": sum(1 for event in events if event["event_name"] == "page_view" and is_through_lens_path(event.get("page_path", ""), event)),
            "things_to_do_views": count_page_prefix(events, "/a-coruna/things-to-do"),
            "literary_tour_views": count_page_prefix(events, "/a-coruna/literary-walking-tour"),
            "through_lens_article_clicks": count_events(events, "click_through_the_lens_article"),
            "literary_tour_clicks": count_events(events, "click_coruna_to_literary_tour") + count_events(events, "click_literary_tour_to_book"),
            "book_clicks_from_coruna": count_events(events, "click_coruna_to_book") + count_events(events, "click_literary_tour_to_book"),
            "signed_clicks_from_coruna": count_events(events, "click_signed_copy_cta"),
        }
        return {
            "totals": totals,
            "top_pages": group_counts(events, "page_path", event_name="page_view"),
            "top_landing_pages": group_counts(events, "landing_page", event_name="page_view"),
            "traffic_sources": traffic_sources(events),
            "device_categories": group_counts(events, "device_category"),
            "cta_performance": cta_performance(events),
            "journey_paths": journey_paths(events),
            "top_content": content_table(events),
            "through_lens_content": through_lens_table(events),
            "retailer_performance": retailer_performance(events),
            "campaign_performance": campaign_performance(events),
            "newsletter_pages": group_counts(events, "page_path", event_name="newsletter_signup"),
            "newsletter_sources": group_counts(events, "source", event_name="newsletter_signup"),
            "camino_sources": group_counts([event for event in events if event["event_name"].startswith("camino_") or event.get("page_path") == "/novel-subscription"], "source"),
            "donation_sources": group_counts(events, "page_path", event_name="donation_click"),
            "a_coruna_pages": group_counts([event for event in events if event["event_name"] == "page_view" and is_a_coruna_path(event.get("page_path", ""))], "page_path"),
            "daily_trend": daily_trend(events, start, end),
            "events": events,
        }

    def _events(self, start, end, filters=None, limit=25000):
        where, params = self._where(start, end, filters)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM analytics_events {where} ORDER BY occurred_at ASC, id ASC LIMIT ?",
                [*params, limit],
            ).fetchall()
        return [event_from_row(row) for row in rows]

    def _where(self, start, end, filters=None):
        filters = {key: value for key, value in (filters or {}).items() if key in FILTER_KEYS and str(value).strip()}
        clauses = ["occurred_at >= ?", "occurred_at < ?"]
        params = [to_utc_iso(start), to_utc_iso(end)]
        for key, value in filters.items():
            clauses.append(f"{key} = ?")
            params.append(str(value).strip())
        return "WHERE " + " AND ".join(clauses), params


def analytics_store(config):
    backend = (config.get("ANALYTICS_STORAGE_BACKEND") or "local").lower()
    if backend == "remote":
        return RemoteAnalyticsStore(
            config.get("ANALYTICS_REMOTE_BASE_URL"),
            config.get("ANALYTICS_REMOTE_API_TOKEN"),
            config.get("ANALYTICS_REMOTE_TIMEOUT_SECONDS", 5),
        )
    cache_key = f"local:{config['ANALYTICS_DB_PATH']}"
    if config.get("_JSM_ANALYTICS_STORE_KEY") != cache_key:
        config["_JSM_ANALYTICS_STORE"] = LocalAnalyticsStore(config["ANALYTICS_DB_PATH"])
        config["_JSM_ANALYTICS_STORE_KEY"] = cache_key
    return config["_JSM_ANALYTICS_STORE"]


def analytics_enabled(config):
    return str(config.get("ANALYTICS_ENABLED", "1")).lower() not in {"0", "false", "no", "off"}


def analytics_environment(config):
    return config.get("ANALYTICS_ENVIRONMENT") or config.get("FLASK_ENV") or "production"


def storage_health(config):
    try:
        return analytics_store(config).health_check()
    except Exception as error:
        return {
            "ok": False,
            "backend": config.get("ANALYTICS_STORAGE_BACKEND", "local"),
            "error": str(error),
            "event_count": 0,
            "last_recorded_at": "",
        }


class RemoteAnalyticsStore:
    def __init__(self, base_url, api_token, timeout_seconds=5):
        self.base_url = (base_url or "").rstrip("/")
        self.api_token = api_token or ""
        self.timeout_seconds = float(timeout_seconds or 5)
        if not self.base_url:
            raise ValueError("ANALYTICS_REMOTE_BASE_URL is required for remote analytics storage.")
        if not self.api_token:
            raise ValueError("ANALYTICS_REMOTE_API_TOKEN is required for remote analytics storage.")

    def store_event(self, event):
        result = self._request("POST", "/events", payload=event)
        return bool(result.get("inserted"))

    def store_events(self, events):
        return self._request("POST", "/events/batch", payload=events)

    def query_summary(self, start, end, filters=None):
        return self._request("GET", "/summary", params=remote_params(start, end, filters))

    def query_events(self, start, end, filters=None, page=1, page_size=50):
        params = remote_params(start, end, filters)
        params.update({"page": str(page), "page_size": str(page_size)})
        return self._request("GET", "/events", params=params)

    def export_events(self, start, end, filters=None):
        return self._request("GET", "/events/export", params=remote_params(start, end, filters), raw_text=True)

    def health_check(self):
        return self._request("GET", "/health")

    def _request(self, method, path, payload=None, params=None, raw_text=False):
        query = f"?{urlencode(params or {})}" if params else ""
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request_obj = Request(
            f"{self.base_url}{path}{query}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "text/csv" if raw_text else "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request_obj, timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
                if raw_text:
                    return raw_body
                return json.loads(raw_body or "{}")
        except HTTPError as error:
            try:
                body_json = json.loads(error.read().decode("utf-8"))
                message = body_json.get("message") or body_json.get("error")
            except (json.JSONDecodeError, UnicodeDecodeError):
                message = None
            raise RuntimeError(message or f"Remote analytics request failed with HTTP {error.code}.") from error
        except URLError as error:
            raise RuntimeError("Remote analytics storage could not be reached.") from error


def remote_params(start, end, filters=None):
    params = {"start": to_utc_iso(start), "end": to_utc_iso(end)}
    for key, value in (filters or {}).items():
        if value:
            params[key] = value
    return params


def date_range_from_args(args):
    range_name = (args.get("range") if args else "") or "30d"
    today = datetime.now(timezone.utc).date()
    if range_name == "today":
        start = today
        end = today + timedelta(days=1)
    elif range_name == "7d":
        start = today - timedelta(days=6)
        end = today + timedelta(days=1)
    elif range_name == "90d":
        start = today - timedelta(days=89)
        end = today + timedelta(days=1)
    elif range_name == "this_month":
        start = today.replace(day=1)
        end = today + timedelta(days=1)
    elif range_name == "previous_month":
        first_this = today.replace(day=1)
        end = first_this
        start = (first_this - timedelta(days=1)).replace(day=1)
    elif range_name == "custom":
        start = parse_date(args.get("start"), today - timedelta(days=29))
        end = parse_date(args.get("end"), today) + timedelta(days=1)
    else:
        range_name = "30d"
        start = today - timedelta(days=29)
        end = today + timedelta(days=1)
    return datetime.combine(start, datetime.min.time(), timezone.utc), datetime.combine(end, datetime.min.time(), timezone.utc), range_name


def filters_from_args(args):
    if not args:
        return {}
    return {key: args.get(key, "").strip() for key in FILTER_KEYS if args.get(key, "").strip()}


def parse_event_request(request, config):
    raw = request.get_data(cache=True) or b"{}"
    if len(raw) > MAX_ANALYTICS_PAYLOAD_BYTES:
        raise AnalyticsValidationError("Analytics payload was too large.")
    payload = request.get_json(silent=True)
    if payload is None:
        raise AnalyticsValidationError("Analytics payload was not valid JSON.")
    raw_events = payload if isinstance(payload, list) else payload.get("events") if isinstance(payload, dict) and isinstance(payload.get("events"), list) else [payload]
    if len(raw_events) > MAX_BATCH_SIZE:
        raise AnalyticsValidationError("Too many analytics events in one request.")
    return [normalize_event(event, config) for event in raw_events if isinstance(event, dict)]


def normalize_event(raw, config):
    name = clean_string(raw.get("event_name") or raw.get("name"), 64)
    name = EVENT_NAME_ALIASES.get(name, name)
    if name not in VALID_EVENT_NAMES:
        VALID_EVENT_NAMES.add(name)
    event = {
        "event_id": clean_string(raw.get("event_id") or f"server:{uuid.uuid4().hex}", 96),
        "schema_version": SCHEMA_VERSION,
        "event_name": name,
        "event_category": clean_string(raw.get("event_category") or EVENT_CATEGORIES.get(name, "engagement"), 48),
        "occurred_at": utc_now_iso(),
        "client_occurred_at": clean_string(raw.get("client_occurred_at"), 40),
        "page_path": normalize_path(raw.get("page_path")),
        "page_title": clean_string(raw.get("page_title"), 180),
        "landing_page": normalize_path(raw.get("landing_page")),
        "content_id": clean_string(raw.get("content_id"), 96),
        "content_type": clean_string(raw.get("content_type"), 48),
        "article_slug": clean_string(raw.get("article_slug"), 120),
        "series": clean_string(raw.get("series"), 120),
        "element_id": clean_string(raw.get("element_id"), 120),
        "element_label": clean_string(raw.get("element_label"), 180),
        "element_type": clean_string(raw.get("element_type"), 64),
        "element_position": clean_string(raw.get("element_position") or raw.get("cta_location"), 120),
        "destination_url": clean_string(raw.get("destination_url") or raw.get("destination"), 360),
        "destination_domain": clean_string(raw.get("destination_domain") or domain_for(raw.get("destination_url") or raw.get("destination")), 160),
        "referrer_url": clean_string(raw.get("referrer_url"), 360),
        "referrer_domain": clean_string(raw.get("referrer_domain"), 160),
        "source": clean_string(raw.get("source") or raw.get("utm_source"), 120),
        "medium": clean_string(raw.get("medium") or raw.get("utm_medium"), 120),
        "campaign": clean_string(raw.get("campaign") or raw.get("utm_campaign"), 120),
        "term": clean_string(raw.get("term") or raw.get("utm_term"), 120),
        "campaign_content": clean_string(raw.get("campaign_content") or raw.get("utm_content"), 120),
        "gclid": clean_string(raw.get("gclid"), 180),
        "gbraid": clean_string(raw.get("gbraid"), 180),
        "wbraid": clean_string(raw.get("wbraid"), 180),
        "anonymous_session_id": clean_string(raw.get("anonymous_session_id"), 96),
        "device_category": clean_string(raw.get("device_category") or raw.get("device_type"), 16),
        "environment": clean_string(raw.get("environment") or analytics_environment(config), 32),
        "metadata": safe_metadata(raw.get("metadata") or {}, raw),
    }
    if event["client_occurred_at"]:
        parsed = parse_datetime(event["client_occurred_at"])
        if parsed:
            event["occurred_at"] = to_utc_iso(parsed)
    return event


def enrich_event_with_request(event, request):
    if request.path.startswith("/admin"):
        raise AnalyticsValidationError("Admin analytics events are not collected.")
    if not event.get("referrer_url"):
        event["referrer_url"] = clean_string(request.referrer, 360)
        event["referrer_domain"] = domain_for(request.referrer)
    if not event.get("page_path"):
        event["page_path"] = "/"
    if event["page_path"].startswith("/admin"):
        raise AnalyticsValidationError("Admin page views are not collected.")
    if not event.get("landing_page"):
        event["landing_page"] = event["page_path"]


def same_origin_request(request, site_domain):
    origin = request.headers.get("Origin") or ""
    if not origin:
        return True
    return urlparse(origin).netloc == urlparse(site_domain).netloc or origin.startswith(request.host_url.rstrip("/"))


def build_empty_summary():
    totals = {
        "page_views": 0,
        "anonymous_sessions": 0,
        "meaningful_actions": 0,
        "book_actions": 0,
    }
    return {
        "totals": totals,
        "previous": totals.copy(),
        "comparison": {key: compare_counts(0, 0) for key in totals},
        "top_pages": [],
        "top_landing_pages": [],
        "traffic_sources": [],
        "device_categories": [],
        "cta_performance": [],
        "journey_paths": [],
        "top_content": [],
        "through_lens_content": [],
        "retailer_performance": [],
        "campaign_performance": [],
        "daily_trend": [],
        "events": [],
    }


def parse_date(value, fallback):
    try:
        return datetime.strptime(value or "", "%Y-%m-%d").date()
    except ValueError:
        return fallback


def parse_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def to_utc_iso(value):
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.combine(value, datetime.min.time(), timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def event_from_row(row):
    event = dict(row)
    try:
        event["metadata"] = json.loads(event.get("metadata_json") or "{}")
    except json.JSONDecodeError:
        event["metadata"] = {}
    event["occurred_at_label"] = event.get("occurred_at", "").replace("T", " ").replace("Z", "")
    event["human_label"] = human_event_label(event.get("event_name", ""))
    return event


def clean_string(value, limit):
    value = "" if value is None else str(value)
    value = re.sub(r"[\x00-\x1f\x7f]", "", value).strip()
    return value[:limit]


def normalize_path(value):
    value = clean_string(value, 240)
    if not value:
        return ""
    try:
        parsed = urlparse(value)
        value = parsed.path or value
    except ValueError:
        pass
    return value if value.startswith("/") else f"/{value}"


def safe_metadata(metadata, raw):
    allowed = {
        "retailer",
        "book_language",
        "cta_location",
        "article_slug",
        "series",
        "destination",
        "value",
        "currency",
        "transaction_id",
        "landing_page",
        "checkout_id",
        "order_id",
        "resource_id",
        "event_id",
        "status",
        "reason",
    }
    merged = {}
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            if key in allowed:
                merged[key] = clean_string(value, 240)
    for key in allowed:
        if key in raw and key not in merged:
            merged[key] = clean_string(raw.get(key), 240)
    return merged


def domain_for(url):
    try:
        return urlparse(url or "").netloc.lower()
    except ValueError:
        return ""


def csv_safe(value):
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in {"=", "+", "-", "@"} else text


def count_events(events, name):
    return sum(1 for event in events if event["event_name"] == name)


def count_page_prefix(events, prefix):
    return sum(1 for event in events if event["event_name"] == "page_view" and (event.get("page_path") or "").startswith(prefix))


def group_counts(events, field, event_name=None, limit=10):
    counter = Counter()
    sessions = defaultdict(set)
    for event in events:
        if event_name and event["event_name"] != event_name:
            continue
        label = event.get(field) or "Unknown"
        counter[label] += 1
        if event.get("anonymous_session_id"):
            sessions[label].add(event["anonymous_session_id"])
    return [{"label": label, "count": count, "sessions": len(sessions[label])} for label, count in counter.most_common(limit) if label != "Unknown" or count]


def traffic_sources(events):
    counter = Counter()
    for event in events:
        if event["event_name"] != "page_view":
            continue
        source = classify_source(event)
        counter[source] += 1
    return [{"label": label, "count": count} for label, count in counter.most_common(10)]


def classify_source(event):
    source = (event.get("source") or "").lower()
    medium = (event.get("medium") or "").lower()
    referrer = (event.get("referrer_domain") or "").lower()
    if event.get("gclid") or event.get("gbraid") or event.get("wbraid") or medium in {"cpc", "ppc", "paid", "paid_search"}:
        return "Google CPC" if "google" in source or not source else f"{source.title()} Paid"
    if source in {"google", "google organic"} or "google." in referrer:
        return "Google Organic"
    if "instagram" in source or "instagram" in referrer:
        return "Instagram"
    if "facebook" in source or "facebook" in referrer:
        return "Facebook"
    if "tiktok" in source or "tiktok" in referrer:
        return "TikTok"
    if medium in {"email", "newsletter"} or source in {"newsletter", "mailchimp"}:
        return "Newsletter / Email"
    if source:
        return source.title()
    if referrer:
        return "Referral"
    return "Direct"


def cta_performance(events):
    rows = defaultdict(lambda: {"impressions": 0, "clicks": 0})
    for event in events:
        key = (event.get("element_label") or event.get("event_name"), event.get("page_path"), event.get("element_position"))
        if event["event_name"].endswith("_impression"):
            rows[key]["impressions"] += 1
        elif event["event_name"] in MEANINGFUL_ACTION_EVENTS:
            rows[key]["clicks"] += 1
    result = []
    for (label, page, position), values in rows.items():
        impressions = values["impressions"]
        clicks = values["clicks"]
        if not clicks and not impressions:
            continue
        rate = numeric_rate(clicks, impressions)
        result.append({"label": human_event_label(label), "page": page, "position": position, "impressions": impressions, "clicks": clicks, "click_rate_label": percent_label(rate)})
    return sorted(result, key=lambda row: (row["clicks"], row["impressions"]), reverse=True)[:12]


def journey_paths(events):
    rows = Counter()
    session_events = defaultdict(list)
    for event in events:
        sid = event.get("anonymous_session_id")
        if sid:
            session_events[sid].append(event)
    for sid, items in session_events.items():
        previous_page = ""
        for event in items:
            if event["event_name"] == "page_view":
                previous_page = event.get("page_path") or previous_page
            elif event["event_name"] in MEANINGFUL_ACTION_EVENTS:
                destination = event.get("destination_url") or event.get("metadata", {}).get("destination") or event.get("page_path") or ""
                rows[(previous_page or event.get("page_path") or "-", human_event_label(event["event_name"]), destination)] += 1
    return [{"source_page": src, "action_label": action, "destination": dest, "count": count, "sessions": count} for (src, action, dest), count in rows.most_common(12)]


def content_table(events):
    by_page = defaultdict(lambda: {"views": 0, "sessions": set(), "actions": 0, "book_actions": 0, "newsletter_signups": 0, "donation_clicks": 0, "title": ""})
    for event in events:
        page = event.get("page_path") or "Unknown"
        row = by_page[page]
        row["title"] = row["title"] or event.get("page_title") or page
        if event["event_name"] == "page_view":
            row["views"] += 1
        if event.get("anonymous_session_id"):
            row["sessions"].add(event["anonymous_session_id"])
        if event["event_name"] in MEANINGFUL_ACTION_EVENTS:
            row["actions"] += 1
        if event["event_name"] in BOOK_ACTION_EVENTS:
            row["book_actions"] += 1
        if event["event_name"] == "newsletter_signup":
            row["newsletter_signups"] += 1
        if event["event_name"] == "donation_click":
            row["donation_clicks"] += 1
    result = []
    for page, row in by_page.items():
        result.append({
            "page": page,
            "title": row["title"],
            "purpose": page_purpose(page),
            "views": row["views"],
            "sessions": len(row["sessions"]),
            "meaningful_actions": row["actions"],
            "book_actions": row["book_actions"],
            "newsletter_signups": row["newsletter_signups"],
            "donation_clicks": row["donation_clicks"],
        })
    return sorted(result, key=lambda row: (row["views"], row["meaningful_actions"]), reverse=True)[:30]


def through_lens_table(events):
    rows = [row for row in content_table(events) if is_through_lens_path(row["page"], row)]
    return rows[:12]


def retailer_performance(events):
    names = {
        "retailer_click_barnes_noble": "Barnes & Noble",
        "retailer_click_amazon_us": "Amazon US",
        "retailer_click_amazon_es": "Amazon Spain",
        "signed_copy_checkout_click": "Signed Direct",
    }
    total = sum(1 for event in events if event["event_name"] in names)
    rows = []
    for event_name, label in names.items():
        matching = [event for event in events if event["event_name"] == event_name]
        rows.append({
            "label": label,
            "count": len(matching),
            "share": percent_label(numeric_rate(len(matching), total)),
            "source_pages": ", ".join(row["label"] for row in group_counts(matching, "page_path", limit=3)) or "-",
        })
    return rows


def campaign_performance(events):
    rows = defaultdict(lambda: {"views": 0, "sessions": set(), "book_actions": 0, "checkout_starts": 0, "verified_purchases": 0, "newsletter_signups": 0, "camino_actions": 0, "donation_intent": 0, "actions": 0, "source": "", "medium": ""})
    for event in events:
        label = event.get("campaign") or event.get("source") or ""
        if not label:
            continue
        row = rows[label]
        row["source"] = row["source"] or event.get("source", "")
        row["medium"] = row["medium"] or event.get("medium", "")
        if event["event_name"] == "page_view":
            row["views"] += 1
        if event.get("anonymous_session_id"):
            row["sessions"].add(event["anonymous_session_id"])
        if event["event_name"] in BOOK_ACTION_EVENTS:
            row["book_actions"] += 1
        if event["event_name"] == "direct_checkout_started":
            row["checkout_starts"] += 1
        if event["event_name"] == "verified_direct_purchase_completed":
            row["verified_purchases"] += 1
        if event["event_name"] == "newsletter_signup":
            row["newsletter_signups"] += 1
        if event["event_name"].startswith("camino_"):
            row["camino_actions"] += 1
        if event["event_name"] == "donation_click":
            row["donation_intent"] += 1
        if event["event_name"] in MEANINGFUL_ACTION_EVENTS:
            row["actions"] += 1
    result = []
    for label, row in rows.items():
        result.append({
            "label": label,
            "source": row["source"],
            "medium": row["medium"],
            "views": row["views"],
            "sessions": len(row["sessions"]),
            "book_actions": row["book_actions"],
            "checkout_starts": row["checkout_starts"],
            "verified_purchases": row["verified_purchases"],
            "newsletter_signups": row["newsletter_signups"],
            "camino_actions": row["camino_actions"],
            "donation_intent": row["donation_intent"],
            "meaningful_actions": row["actions"],
            "action_rate_label": percent_label(numeric_rate(row["actions"], row["views"])),
        })
    return sorted(result, key=lambda item: (item["meaningful_actions"], item["views"]), reverse=True)[:20]


def daily_trend(events, start, end):
    days = []
    cursor = start.date()
    last = (end - timedelta(days=1)).date()
    by_day = defaultdict(lambda: Counter())
    sessions = defaultdict(set)
    for event in events:
        parsed = parse_datetime(event.get("occurred_at"))
        if not parsed:
            continue
        day = parsed.date().isoformat()
        name = event["event_name"]
        if name == "page_view":
            by_day[day]["page_views"] += 1
        if name in BOOK_ACTION_EVENTS:
            by_day[day]["book_actions"] += 1
        if name == "newsletter_signup":
            by_day[day]["newsletter_signups"] += 1
        if name == "direct_checkout_started":
            by_day[day]["checkout_starts"] += 1
        if name == "donation_click":
            by_day[day]["donation_clicks"] += 1
        if event.get("anonymous_session_id"):
            sessions[day].add(event["anonymous_session_id"])
    while cursor <= last:
        day = cursor.isoformat()
        row = {"day": day, **by_day[day], "sessions": len(sessions[day])}
        days.append(row)
        cursor += timedelta(days=1)
    return days[-30:]


def is_a_coruna_path(path):
    return (path or "").startswith("/a-coruna") or "/blogs/a-coruna-through-the-lens" in (path or "")


def is_through_lens_path(path, event):
    return "through-the-lens" in (path or "") or event.get("series") == "A Coruña Through the Lens"


def is_a_coruna_event(event):
    return is_a_coruna_path(event.get("page_path", "")) or event["event_name"].startswith("click_coruna") or "through_the_lens" in event["event_name"] or event["event_name"].startswith("view_coruna")


def page_purpose(path):
    if is_a_coruna_path(path):
        return "A Coruña"
    if path in {"/book", "/free-book-preview"}:
        return "Book"
    if path.startswith("/book/signed") or path.startswith("/book/checkout"):
        return "Conversion"
    if path in {"/newsletter", "/novel-subscription"}:
        return "Community"
    if path == "/donate":
        return "Support"
    if path.startswith("/blogs"):
        return "Editorial"
    return "Discovery"


def numeric_rate(value, total):
    total = float(total or 0)
    return None if total <= 0 else float(value or 0) / total


def percent_label(rate):
    if rate is None:
        return "No baseline"
    return f"{rate * 100:.1f}%"


def click_rate(value, total):
    return percent_label(numeric_rate(value, total))


def compare_counts(current, previous):
    current = int(current or 0)
    previous = int(previous or 0)
    if previous == 0 and current == 0:
        return {"label": "No previous activity", "direction": "flat", "percent": None}
    if previous == 0:
        return {"label": f"+{current} from no previous activity", "direction": "up", "percent": None}
    diff = current - previous
    pct = diff / previous
    direction = "up" if diff > 0 else "down" if diff < 0 else "flat"
    sign = "+" if diff > 0 else ""
    return {"label": f"{sign}{diff} ({sign}{pct * 100:.1f}%)", "direction": direction, "percent": pct}


def human_event_label(value):
    return str(value or "").replace("_", " ").strip().title()


def money(value, currency="$"):
    try:
        return f"{currency}{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return f"{currency}0.00"


def build_campaign_url(site_domain, page, source, medium, campaign, content="", term=""):
    page = page or "/"
    if not page.startswith("/"):
        page = f"/{page}"
    query = {
        "utm_source": source,
        "utm_medium": medium,
        "utm_campaign": campaign,
        "utm_content": content,
        "utm_term": term,
    }
    query = {key: value for key, value in query.items() if value}
    return f"{site_domain.rstrip('/')}{page}" + (f"?{urlencode(query)}" if query else "")
