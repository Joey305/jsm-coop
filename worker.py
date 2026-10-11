"""Background maintenance for the admin command center.

Run this as the Heroku worker process.  It keeps costly analytics aggregation
off the web dyno, so logging into /admin can only read compact cached JSON.
"""

import logging
import os
import time

import app as site


REFRESH_ARGUMENTS = ({"range": "30d"}, {"range": "7d"}, {"range": "90d"}, {"range": "today"})
POLL_SECONDS = max(30, int(os.getenv("ADMIN_DASHBOARD_WORKER_POLL_SECONDS", "60")))


def refresh(args):
    # Some dashboard helpers build links with url_for, so give the worker the
    # same request context it would have on the admin page.
    with site.app.test_request_context("/admin", query_string=args):
        site.refresh_dashboard_cache(site.app.config, args)


def refresh_due_dashboards():
    for args in REFRESH_ARGUMENTS:
        cached = site.read_dashboard_cache(site.app.config, args, allow_stale=True)
        if not cached or not cached["fresh"]:
            refresh(args)


def run_once():
    queued = site.next_dashboard_refresh_job(site.app.config)
    if queued is not None:
        refresh(queued)
    refresh_due_dashboards()
    # Provider APIs are intentionally called from this worker, never /admin.
    start, end, _ = site.analytics.date_range_from_args({"range": "30d"})
    ads_key = f"google_ads:{start.date().isoformat()}:{(end - site.timedelta(days=1)).date().isoformat()}"
    search_key = f"search_console:{start.date().isoformat()}:{(end - site.timedelta(days=1)).date().isoformat()}"
    ads_due = not site.cache_is_fresh(site.read_external_cache(site.app.config, ads_key), site.app.config["GOOGLE_ADS_REPORT_CACHE_SECONDS"])
    search_due = not site.cache_is_fresh(site.read_external_cache(site.app.config, search_key), site.app.config["SEARCH_CONSOLE_REPORT_CACHE_SECONDS"])
    if ads_due or search_due:
        site.refresh_external_reports(site.app.config, start, end)


def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    while True:
        try:
            run_once()
        except Exception:
            site.app.logger.exception("admin dashboard worker cycle failed")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
