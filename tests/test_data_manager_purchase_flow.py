import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import app
import jsm_analytics as analytics
from marketing.google_ads import data_manager


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text
        self.headers = {"x-goog-request-id": "request-123"}
        self.ok = 200 <= status_code < 300

    def json(self):
        if self._body == "malformed":
            raise ValueError("malformed")
        return self._body or {}


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response or FakeResponse(200, {"requestId": "dm-123"})
        self.error = error
        self.calls = []

    def post(self, url, json=None, timeout=None):
        if self.error:
            raise self.error
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return self.response


class DataManagerPurchaseFlowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.original_config = app.app.config.copy()
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
            GOOGLE_ADS_CUSTOMER_ID="5924203827",
            GOOGLE_ADS_SIGNED_BOOK_PURCHASE_CONVERSION_ACTION_ID="7718901779",
            GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_ID="",
            GOOGLE_DATA_MANAGER_VALIDATE_ONLY="1",
            GOOGLE_ADS_LEGACY_PURCHASE_UPLOAD_ENABLED=False,
        )
        for key in (
            "GOOGLE_DATA_MANAGER_SERVICE_ACCOUNT_JSON",
            "GOOGLE_DATA_MANAGER_SERVICE_ACCOUNT_JSON_BASE64",
            "GOOGLE_ADS_DEVELOPER_TOKEN",
            "GOOGLE_ADS_CLIENT_ID",
            "GOOGLE_ADS_CLIENT_SECRET",
            "GOOGLE_ADS_REFRESH_TOKEN",
        ):
            os.environ.pop(key, None)
        app.app.config.pop("_JSM_ANALYTICS_STORE", None)
        app.app.config.pop("_JSM_ANALYTICS_STORE_KEY", None)

    def restore_state(self):
        app.app.config.clear()
        app.app.config.update(self.original_config)

    def read_jsonl(self, path):
        if not Path(path).exists():
            return []
        return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

    def paypal_capture_payload(self, checkout_id="checkout-123", capture_id="CAPTURE-123", value="19.99", currency="USD"):
        return {
            "id": f"WH-{capture_id}",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "create_time": "2026-08-13T10:30:00Z",
            "resource": {
                "id": capture_id,
                "status": "COMPLETED",
                "custom_id": checkout_id,
                "invoice_id": checkout_id,
                "amount": {"currency_code": currency, "value": value},
                "supplementary_data": {"related_ids": {"order_id": "ORDER-123"}},
            },
        }

    def seed_checkout(self, checkout_id="checkout-123", **extra):
        record = {
            "checkout_id": checkout_id,
            "landing_page": "/book/signed?utm_source=google",
            "page_path": "/book/signed?utm_source=google",
            "checkout_started_at": "2026-08-13T10:00:00Z",
            "value": "15.00",
            "currency": "USD",
            "gclid": "gclid-123",
            "gbraid": "",
            "wbraid": "",
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "signed-book",
            "utm_content": "hero",
            "utm_term": "signed book",
        }
        record.update(extra)
        app.append_jsonl(app.app.config["BOOK_DIRECT_CHECKOUT_ATTRIBUTION_LOG"], record)
        return record

    def test_checkout_json_persists_landing_page_click_ids_utms_and_returns_checkout_id(self):
        client = app.app.test_client()
        response = client.get(
            "/book/checkout/start?format=json&landing_page=/book/signed"
            "&gclid=g1&gbraid=gb1&wbraid=wb1&utm_source=google&utm_medium=cpc"
            "&utm_campaign=camp&utm_content=content&utm_term=term"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ready")
        self.assertTrue(payload["checkout_id"])
        records = self.read_jsonl(app.app.config["BOOK_DIRECT_CHECKOUT_ATTRIBUTION_LOG"])
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["checkout_id"], payload["checkout_id"])
        self.assertEqual(record["landing_page"], "/book/signed")
        self.assertEqual(record["gclid"], "g1")
        self.assertEqual(record["gbraid"], "gb1")
        self.assertEqual(record["wbraid"], "wb1")
        self.assertEqual(record["utm_source"], "google")
        self.assertEqual(record["utm_medium"], "cpc")
        self.assertEqual(record["utm_campaign"], "camp")
        self.assertEqual(record["utm_content"], "content")
        self.assertEqual(record["utm_term"], "term")
        self.assertTrue(record["checkout_started_at"])

    def test_verified_purchase_records_analytics_and_data_manager_once(self):
        self.seed_checkout()
        result = data_manager.DataManagerResult(
            status="validated",
            http_status=200,
            request_id="dm-123",
            validate_only=True,
            payload_accepted=True,
        )
        client = app.app.test_client()
        with patch.object(app, "verify_paypal_webhook_signature", return_value=(True, "SUCCESS")), patch.object(
            app.data_manager, "ingest_purchase", return_value=result
        ) as ingest:
            response = client.post("/paypal/webhook", json=self.paypal_capture_payload())
            self.assertEqual(response.status_code, 200)
            duplicate = client.post("/paypal/webhook", json=self.paypal_capture_payload())
            self.assertEqual(duplicate.status_code, 200)

        purchases = self.read_jsonl(app.app.config["PAYPAL_VERIFIED_PURCHASE_LOG"])
        self.assertEqual(len(purchases), 1)
        self.assertEqual(purchases[0]["capture_id"], "CAPTURE-123")
        self.assertEqual(purchases[0]["order_id"], "ORDER-123")
        self.assertEqual(purchases[0]["value"], "19.99")
        self.assertEqual(purchases[0]["currency"], "USD")
        self.assertEqual(purchases[0]["gclid"], "gclid-123")
        self.assertEqual(ingest.call_count, 1)

        store = analytics.analytics_store(app.app.config)
        start = datetime(2026, 8, 13, tzinfo=timezone.utc)
        end = datetime(2026, 8, 14, tzinfo=timezone.utc)
        events = store.query_events(start, end, {"environment": "test"}, page_size=20)["events"]
        purchase_events = [event for event in events if event["event_name"] == "verified_direct_purchase_completed"]
        self.assertEqual(len(purchase_events), 1)
        self.assertEqual(purchase_events[0]["metadata"]["checkout_id"], "checkout-123")

        uploads = self.read_jsonl(app.app.config["GOOGLE_ADS_OFFLINE_CONVERSION_LOG"])
        self.assertEqual(uploads[0]["event_name"], "signed_book_purchase_datamanager")
        self.assertEqual(uploads[0]["status"], "validated")
        self.assertEqual(uploads[1]["reason"], "already_sent")

    def test_unverified_webhook_does_not_persist_purchase_or_call_google(self):
        client = app.app.test_client()
        with patch.object(app, "verify_paypal_webhook_signature", return_value=(False, "FAILURE")), patch.object(
            app.data_manager, "ingest_purchase"
        ) as ingest:
            response = client.post("/paypal/webhook", json=self.paypal_capture_payload())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Path(app.app.config["PAYPAL_VERIFIED_PURCHASE_LOG"]).exists())
        ingest.assert_not_called()

    def test_data_manager_failure_does_not_fail_paypal_webhook(self):
        self.seed_checkout()
        result = data_manager.DataManagerResult(
            status="failed",
            http_status=403,
            reason="PERMISSION_DENIED",
            message="The caller does not have permission",
            validate_only=True,
        )
        client = app.app.test_client()
        with patch.object(app, "verify_paypal_webhook_signature", return_value=(True, "SUCCESS")), patch.object(
            app.data_manager, "ingest_purchase", return_value=result
        ):
            response = client.post("/paypal/webhook", json=self.paypal_capture_payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.read_jsonl(app.app.config["PAYPAL_VERIFIED_PURCHASE_LOG"])), 1)
        uploads = self.read_jsonl(app.app.config["GOOGLE_ADS_OFFLINE_CONVERSION_LOG"])
        self.assertEqual(uploads[0]["status"], "failed")
        self.assertEqual(uploads[0]["reason"], "PERMISSION_DENIED")

    def test_data_manager_payload_contains_destination_purchase_fields_and_click_ids(self):
        session = FakeSession()
        record = {
            "capture_id": "CAPTURE-123",
            "completed_at": "2026-08-13T10:30:00Z",
            "value": "19.99",
            "currency": "usd",
            "gclid": "gclid-123",
            "gbraid": "gbraid-123",
            "wbraid": "wbraid-123",
        }
        result = data_manager.ingest_purchase(record, app.app.config, session=session, validate_only=False)
        self.assertEqual(result.status, "uploaded")
        payload = session.calls[0]["json"]
        destination = payload["destinations"][0]
        self.assertEqual(destination["operatingAccount"]["accountType"], "GOOGLE_ADS")
        self.assertEqual(destination["operatingAccount"]["accountId"], "5924203827")
        self.assertEqual(destination["loginAccount"]["accountId"], "5924203827")
        self.assertEqual(destination["productDestinationId"], "7718901779")
        event = payload["events"][0]
        self.assertEqual(event["transactionId"], "CAPTURE-123")
        self.assertEqual(event["eventTimestamp"], "2026-08-13T10:30:00Z")
        self.assertEqual(event["conversionValue"], 19.99)
        self.assertEqual(event["currency"], "USD")
        self.assertEqual(event["adIdentifiers"]["gclid"], "gclid-123")
        self.assertFalse(payload["validateOnly"])

    def test_data_manager_validate_mode_errors_and_no_ad_identifier_are_safe(self):
        no_id = data_manager.ingest_purchase(
            {"capture_id": "CAPTURE-123", "value": "19.99", "currency": "USD"},
            app.app.config,
            session=FakeSession(),
        )
        self.assertEqual(no_id.status, "skipped")
        self.assertEqual(no_id.reason, "missing_ad_identifier")

        error_body = {
            "error": {
                "status": "PERMISSION_DENIED",
                "message": "The caller does not have permission",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "ACCESS_DENIED"},
                    {
                        "@type": "type.googleapis.com/google.rpc.BadRequest",
                        "fieldViolations": [{"field": "destinations[0]", "description": "bad destination"}],
                    },
                ],
            }
        }
        session = FakeSession(FakeResponse(403, error_body))
        result = data_manager.ingest_purchase(
            {"capture_id": "CAPTURE-123", "value": "19.99", "currency": "USD", "gclid": "gclid-123"},
            app.app.config,
            session=session,
        )
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "ACCESS_DENIED")
        self.assertEqual(result.http_status, 403)
        self.assertEqual(result.error["field_violations"][0]["field"], "destinations[0]")
        self.assertNotIn("gclid-123", json.dumps(result.error))

        timeout = data_manager.ingest_purchase(
            {"capture_id": "CAPTURE-123", "value": "19.99", "currency": "USD", "gclid": "gclid-123"},
            app.app.config,
            session=FakeSession(error=TimeoutError("timed out")),
        )
        self.assertTrue(timeout.retryable)

        malformed = data_manager.ingest_purchase(
            {"capture_id": "CAPTURE-123", "value": "19.99", "currency": "USD", "gclid": "gclid-123"},
            app.app.config,
            session=FakeSession(FakeResponse(400, "malformed", "not json")),
        )
        self.assertEqual(malformed.status, "failed")
        self.assertEqual(malformed.http_status, 400)


if __name__ == "__main__":
    unittest.main()
