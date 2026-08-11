# JSM Cooperative Randy Analytics Receiver

This folder contains the Randy-side Flask route bundle for JSM Cooperative's remote first-party analytics database.

It is meant to be added to the existing Randy Flask service. Do not replace the current Randy app, backup receiver, Mindful Diabetes route, or other tool routes.

Copy these files to Randy:

- `jsm_analytics_routes.py`
- the repository root `jsm_analytics.py`

Suggested Randy location:

```text
/home/jxs794/PROTAC_BUILDER/JSMcoop
```

Suggested environment variables on Randy:

```bash
export JSM_ANALYTICS_DB_PATH="/home/jxs794/PROTAC_BUILDER/JSMcoop/jsm_analytics.sqlite3"
```

Token behavior:

- If Randy already has a shared `RANDY_API_TOKEN`, this route accepts that token automatically.
- If you want a JSM-specific token later, set `JSM_ANALYTICS_API_TOKEN`.
- Heroku's `ANALYTICS_REMOTE_API_TOKEN` must match whichever token Randy is accepting.

Register the blueprint in the Randy Flask app:

```python
from JSMcoop.jsm_analytics_routes import create_blueprint as create_jsm_analytics_blueprint

app.register_blueprint(create_jsm_analytics_blueprint())
```

This adds only the `/jsm-coop/analytics/...` route group.

The blueprint serves:

```text
/jsm-coop/analytics/events
/jsm-coop/analytics/events/batch
/jsm-coop/analytics/summary
/jsm-coop/analytics/events/export
/jsm-coop/analytics/health
```

Heroku should point to:

```text
ANALYTICS_REMOTE_BASE_URL=https://randy.rove-vernier.ts.net/jsm-coop/analytics
```
