import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import app
import jsm_analytics as analytics


class DashboardV2Tests(unittest.TestCase):
    def make_store(self):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        return analytics.LocalAnalyticsStore(Path(tempdir.name) / "analytics.sqlite3")

    def event(self, name, day, session_id="sess-1", page_path="/", **extra):
        payload = {
            "event_id": f"{name}-{session_id}-{day.isoformat()}-{len(extra)}-{extra.get('page_path', page_path)}",
            "event_name": name,
            "client_occurred_at": day.isoformat().replace("+00:00", "Z"),
            "page_path": page_path,
            "landing_page": extra.pop("landing_page", page_path),
            "anonymous_session_id": session_id,
            "device_category": "desktop",
            **extra,
        }
        return analytics.normalize_event(payload, {"ANALYTICS_ENVIRONMENT": "test"})

    def test_coverage_states_and_comparison_gate(self):
        now = datetime(2026, 8, 11, tzinfo=timezone.utc)
        empty = app.dashboard_analytics_coverage({"event_count": 0}, now - timedelta(days=29), now + timedelta(days=1))
        self.assertEqual(empty["status"], "No Data")
        self.assertFalse(empty["comparison_available"])

        learning = app.dashboard_analytics_coverage(
            {"event_count": 4, "first_recorded_at": "2026-08-11T01:00:00Z", "last_recorded_at": "2026-08-11T02:00:00Z", "tracking_days": 1},
            now - timedelta(days=29),
            now + timedelta(days=1),
        )
        self.assertEqual(learning["status"], "Learning")
        self.assertIn("Tracking began", learning["comparison_label"])

        full = app.dashboard_analytics_coverage(
            {"event_count": 60, "first_recorded_at": "2026-06-01T00:00:00Z", "last_recorded_at": "2026-08-11T02:00:00Z", "tracking_days": 72},
            now - timedelta(days=29),
            now + timedelta(days=1),
        )
        self.assertEqual(full["status"], "Full Comparison Available")
        self.assertTrue(full["comparison_available"])

    def test_metric_semantics_are_exact_and_session_based(self):
        store = self.make_store()
        day = datetime(2026, 8, 11, 12, tzinfo=timezone.utc)
        store.store_events(
            [
                self.event("page_view", day, "s1", "/book"),
                self.event("page_view", day, "s1", "/book/signed"),
                self.event("signed_copy_page_view", day, "s1", "/book/signed"),
                self.event("direct_checkout_started", day, "s1", "/book/signed"),
                self.event("book_preview_click", day, "s1", "/book"),
                self.event("signed_copy_preview_click", day, "s1", "/book"),
            ]
        )
        summary = store.query_summary(day - timedelta(hours=1), day + timedelta(hours=1), {"environment": "test"})
        totals = summary["totals"]
        self.assertEqual(totals["book_page_views"], 1)
        self.assertEqual(totals["book_ecosystem_page_views"], 2)
        self.assertEqual(totals["signed_copy_page_views"], 1)
        self.assertEqual(totals["signed_copy_legacy_view_events"], 1)
        self.assertEqual(totals["meaningful_action_sessions"], 1)
        self.assertEqual(totals["meaningful_actions"], 3)

    def test_unknown_events_are_diagnostic(self):
        event = analytics.normalize_event({"event_name": "typo_checkout", "page_path": "/"}, {"ANALYTICS_ENVIRONMENT": "test"})
        self.assertEqual(event["event_name"], "unknown_event")
        self.assertEqual(event["metadata"]["original_event_name"], "typo_checkout")

    def test_session_source_attribution_flows_downstream(self):
        store = self.make_store()
        day = datetime(2026, 8, 11, 12, tzinfo=timezone.utc)
        store.store_events(
            [
                self.event("page_view", day, "paid", "/a-coruna/things-to-do", gclid="abc123", source="google", medium="cpc"),
                self.event("page_view", day + timedelta(minutes=1), "paid", "/book/signed"),
                self.event("direct_checkout_started", day + timedelta(minutes=2), "paid", "/book/signed"),
            ]
        )
        summary = store.query_summary(day - timedelta(hours=1), day + timedelta(hours=1), {"environment": "test"})
        row = summary["acquisition_outcomes"][0]
        self.assertEqual(row["source"], "Google CPC")
        self.assertEqual(row["checkout_starts"], 1)


if __name__ == "__main__":
    unittest.main()
