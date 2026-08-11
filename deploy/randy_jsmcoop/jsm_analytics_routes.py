from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, jsonify, request

try:
    from . import jsm_analytics as analytics
except ImportError:
    import jsm_analytics as analytics


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = PROJECT_ROOT / "jsm_analytics.sqlite3"
MAX_PAYLOAD_BYTES = 32_000
MAX_BATCH_SIZE = 20


class ValidationError(ValueError):
    pass


def create_blueprint() -> Blueprint:
    bp = Blueprint("jsm_analytics", __name__, url_prefix="/jsm-coop/analytics")

    @bp.post("/events")
    def store_one_event():
        ok, error = require_token()
        if not ok:
            return error
        try:
            events = parse_payload()
            if len(events) != 1:
                raise ValidationError("Submit one event to this endpoint.")
            result = store().store_events(events)
            return jsonify({"ok": True, **result}), 202
        except ValidationError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

    @bp.post("/events/batch")
    def store_event_batch():
        ok, error = require_token()
        if not ok:
            return error
        try:
            result = store().store_events(parse_payload())
            return jsonify({"ok": True, **result}), 202
        except ValidationError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

    @bp.get("/summary")
    def query_summary():
        ok, error = require_token()
        if not ok:
            return error
        start, end = date_range_from_args()
        filters = filters_from_args(request.args)
        return jsonify(store().query_summary(start, end, filters))

    @bp.get("/events")
    def query_events():
        ok, error = require_token()
        if not ok:
            return error
        start, end = date_range_from_args()
        filters = filters_from_args(request.args)
        page = max(1, int(request.args.get("page", 1)))
        page_size = max(1, min(200, int(request.args.get("page_size", 50))))
        return jsonify(store().query_events(start, end, filters, page=page, page_size=page_size))

    @bp.get("/events/export")
    def export_events():
        ok, error = require_token()
        if not ok:
            return error
        start, end = date_range_from_args()
        filters = filters_from_args(request.args)
        body = store().export_events(start, end, filters)
        filename = f"jsm-analytics-{start.date()}-to-{(end - timedelta(days=1)).date()}.csv"
        return Response(
            body,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
            mimetype="text/csv",
        )

    @bp.post("/cleanup")
    def cleanup_events():
        ok, error = require_token()
        if not ok:
            return error
        payload = request.get_json(silent=True) or {}
        before = parse_timestamp(payload.get("before_date")) or (utc_now() - timedelta(days=int(payload.get("retention_days") or 180)))
        removed = cleanup_before(before)
        return jsonify({"ok": True, "removed": removed})

    @bp.get("/health")
    def health():
        ok, error = require_token()
        if not ok:
            return error
        return jsonify({"ok": True, **store().health_check()})

    return bp


def configured_token() -> str:
    return (
        os.environ.get("JSM_ANALYTICS_API_TOKEN", "").strip()
        or os.environ.get("RANDY_API_TOKEN", "").strip()
        or os.environ.get("MDINC_ANALYTICS_API_TOKEN", "").strip()
        or os.environ.get("PROTAC_BACKUP_TOKEN", "").strip()
    )


def db_path() -> Path:
    return Path(os.environ.get("JSM_ANALYTICS_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()


def store() -> analytics.LocalAnalyticsStore:
    return analytics.LocalAnalyticsStore(db_path())


def require_token():
    token = configured_token()
    if not token:
        return False, (jsonify({"ok": False, "message": "JSM analytics token is not configured."}), 500)
    if request.headers.get("Authorization", "") != f"Bearer {token}":
        return False, (jsonify({"ok": False, "message": "Unauthorized."}), 401)
    return True, None


def parse_payload() -> list[dict[str, Any]]:
    if request.content_length and request.content_length > MAX_PAYLOAD_BYTES:
        raise ValidationError("Analytics payload is too large.")
    if not request.is_json:
        raise ValidationError("Analytics endpoint accepts JSON only.")
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("Analytics payload was not valid JSON.")
    raw_events = payload if isinstance(payload, list) else [payload]
    if len(raw_events) > MAX_BATCH_SIZE:
        raise ValidationError("Analytics event batch is too large.")
    config = {"ANALYTICS_ENVIRONMENT": os.environ.get("JSM_ANALYTICS_ENVIRONMENT", "production")}
    events = []
    for event in raw_events:
        if not isinstance(event, dict):
            raise ValidationError("Each analytics event must be an object.")
        normalized = analytics.normalize_event(event, config)
        if normalized.get("page_path", "").startswith(("/admin", "/analytics", "/static")):
            raise ValidationError("Analytics event path is not public.")
        events.append(normalized)
    return events


def date_range_from_args() -> tuple[datetime, datetime]:
    end = parse_timestamp(request.args.get("end")) or utc_now()
    start = parse_timestamp(request.args.get("start")) or (end - timedelta(days=30))
    if len((request.args.get("end") or "")) == 10:
        end = end + timedelta(days=1)
    return start, end


def filters_from_args(args) -> dict[str, str]:
    return analytics.filters_from_args(args)


def parse_timestamp(value):
    if not value:
        return None
    try:
        if len(str(value)) == 10:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def cleanup_before(before: datetime) -> int:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        cursor = conn.execute("DELETE FROM analytics_events WHERE occurred_at < ?", (analytics.to_utc_iso(before),))
        return int(cursor.rowcount)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
