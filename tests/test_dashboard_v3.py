import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import app
import jsm_analytics as analytics


class DashboardV3Tests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.original_config = app.app.config.copy()
        self.original_blog_dir = app.BLOG_DIR
        self.addCleanup(self.restore_state)
        app.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret",
            ANALYTICS_DB_PATH=self.root / "analytics.sqlite3",
            ADMIN_VISITS_DB_PATH=self.root / "admin.sqlite3",
            PAYPAL_VERIFIED_PURCHASE_LOG=self.root / "verified.jsonl",
            PAYPAL_WEBHOOK_EVENT_LOG=self.root / "paypal.jsonl",
            GOOGLE_ADS_OFFLINE_CONVERSION_LOG=self.root / "ads_uploads.jsonl",
            BOOK_DIRECT_CHECKOUT_ATTRIBUTION_LOG=self.root / "checkout.jsonl",
            ANALYTICS_ENVIRONMENT="test",
            GOOGLE_SEARCH_CONSOLE_SITE_URL="",
            GOOGLE_SEARCH_CONSOLE_CREDENTIALS_JSON="",
        )
        for key in (
            "GOOGLE_ADS_DEVELOPER_TOKEN",
            "GOOGLE_ADS_CLIENT_ID",
            "GOOGLE_ADS_CLIENT_SECRET",
            "GOOGLE_ADS_REFRESH_TOKEN",
            "GOOGLE_SEARCH_CONSOLE_SITE_URL",
            "GOOGLE_SEARCH_CONSOLE_CREDENTIALS_JSON",
        ):
            os.environ.pop(key, None)
        app.app.config["GOOGLE_ADS_CUSTOMER_ID"] = ""
        app.app.config.pop("_JSM_ANALYTICS_STORE", None)
        app.app.config.pop("_JSM_ANALYTICS_STORE_KEY", None)

    def restore_state(self):
        app.BLOG_DIR = self.original_blog_dir
        app.app.config.clear()
        app.app.config.update(self.original_config)

    def event(self, name, when, session_id="sess-1", page_path="/", **extra):
        payload = {
            "event_id": f"{name}-{session_id}-{when.isoformat()}-{page_path}-{len(extra)}",
            "event_name": name,
            "client_occurred_at": when.isoformat().replace("+00:00", "Z"),
            "page_path": page_path,
            "landing_page": extra.pop("landing_page", page_path),
            "anonymous_session_id": session_id,
            "device_category": "desktop",
            **extra,
        }
        return analytics.normalize_event(payload, {"ANALYTICS_ENVIRONMENT": "test"})

    def test_today_pulse_is_independent_of_selected_range(self):
        store = analytics.analytics_store(app.app.config)
        now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
        old = now - timedelta(days=60)
        store.store_events(
            [
                self.event("page_view", old, "old", "/book"),
                self.event("book_preview_click", old, "old", "/book"),
                self.event("page_view", now, "today", "/book/signed"),
                self.event("engaged_30s", now + timedelta(minutes=1), "today", "/book/signed"),
                self.event("direct_checkout_started", now + timedelta(minutes=2), "today", "/book/signed"),
            ]
        )
        with app.app.test_request_context("/admin?range=90d"):
            dashboard = app.build_admin_dashboard(app.app.config, {"range": "90d"})
        today_metrics = {row["label"]: row["value"] for row in dashboard["today"]["metrics"]}
        self.assertEqual(today_metrics["Visitors Today"], 1)
        self.assertEqual(today_metrics["Page Views Today"], 1)
        self.assertEqual(today_metrics["Checkout Starts Today"], 1)
        self.assertEqual(dashboard["summary"]["totals"]["book_actions"], 1)

    def test_google_ads_missing_config_is_non_fatal_and_cached(self):
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        report = app.fetch_google_ads_report(app.app.config, start, end)
        self.assertEqual(report["status"], "Configuration Missing")
        cached = app.read_external_cache(app.app.config, f"google_ads:{start.date().isoformat()}:{(end - timedelta(days=1)).date().isoformat()}")
        self.assertIsNotNone(cached)
        with app.app.test_request_context("/admin?range=7d"):
            dashboard = app.build_admin_dashboard(app.app.config, {"range": "7d"})
        self.assertIn("google_ads_report", dashboard)

    def test_site_audit_detects_broken_internal_link_and_missing_media(self):
        blog_dir = self.root / "blogs"
        blog_dir.mkdir()
        app.BLOG_DIR = blog_dir
        (blog_dir / "broken.md").write_text(
            """---
title: Broken Link Test
date: 2026-08-11
author: JSM Cooperative
excerpt: A long enough excerpt for the test article to avoid that particular warning in the health checker.
cover: /static/images/missing-test-image.png
tags: Test
---

## Section

This links to [missing](/missing-internal-page) and references ![Alt](/static/images/missing-test-inline.png).
""",
            encoding="utf-8",
        )
        audit = app.run_site_audit(app.app.config, "admin")
        self.assertTrue(audit["results"]["broken_links"])
        self.assertTrue(audit["results"]["missing_media"])

    def test_annotations_are_admin_and_csrf_protected(self):
        client = app.app.test_client()
        response = client.post("/admin/annotations", data={"title": "Launch", "date": "2026-08-11"})
        self.assertEqual(response.status_code, 302)
        with client.session_transaction() as session:
            session["admin_logged_in"] = True
            session["admin_csrf_token"] = "csrf"
        response = client.post("/admin/annotations", data={"title": "Launch", "date": "2026-08-11"})
        self.assertEqual(response.status_code, 400)
        response = client.post(
            "/admin/annotations",
            data={"csrf_token": "csrf", "title": "Launch", "date": "2026-08-11", "category": "Google Ads", "description": "Campaign started."},
        )
        self.assertEqual(response.status_code, 302)
        notes = app.list_annotations(app.app.config)
        self.assertEqual(notes[0]["title"], "Launch")
        response = client.post(f"/admin/annotations/{notes[0]['id']}/delete", data={"csrf_token": "csrf"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(app.list_annotations(app.app.config), [])


if __name__ == "__main__":
    unittest.main()
