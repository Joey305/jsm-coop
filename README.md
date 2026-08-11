# 🎭 JSM Cooperative Flask Site

<p align="center">
  <strong>Stories that fund a better world.</strong>
</p>

<p align="center">
  <em>A custom Flask website for JSM Cooperative Corporation, built to publish stories, support book campaigns, share community updates, and connect readers with nonprofit impact.</em>
</p>

<p align="center">
  <a href="https://jsmcoop.com">
    <img src="https://img.shields.io/badge/Website-jsmcoop.com-00eaff?style=for-the-badge&logo=googlechrome" alt="JSMCoop.com">
  </a>
  <img src="https://img.shields.io/badge/Framework-Flask-blue?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Blog-Markdown-success?style=for-the-badge&logo=markdown" alt="Markdown Blog">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge" alt="Active">
</p>

<p align="center">
  <a href="https://www.instagram.com/jsm.cooperative/">
    <img src="https://img.shields.io/badge/Instagram-jsm.cooperative-E4405F?style=for-the-badge&logo=instagram" alt="Instagram">
  </a>
  <a href="https://www.tiktok.com/@jsm.cooperative">
    <img src="https://img.shields.io/badge/TikTok-jsm.cooperative-black?style=for-the-badge&logo=tiktok" alt="TikTok">
  </a>
  <a href="https://www.youtube.com/@JSm.cooperative">
    <img src="https://img.shields.io/badge/YouTube-JSM%20Cooperative-red?style=for-the-badge&logo=youtube" alt="YouTube">
  </a>
</p>

---

## Overview

**JSM Cooperative Flask Site** is the public website codebase for **JSM Cooperative Corporation**.

JSM Cooperative uses storytelling, publishing, and community-centered creative campaigns to support meaningful nonprofit impact. This site provides a lightweight, maintainable Flask foundation for the organization’s public-facing pages, book updates, blog posts, newsletter flow, donation pathway, and community resources.

The project was rebuilt from a previous WordPress/Page Builder setup into a cleaner Flask structure that is easier to version-control, customize, deploy, and expand.

---

## Current Features

- Flask-powered routing
- Responsive public website layout
- Global header and footer
- Public homepage for the JSM Cooperative mission
- Book page for *The Man in the Ball Cap*
- Purchase modal for book links
- Markdown-powered blog archive
- Individual blog detail pages
- Newsletter signup page
- Donation page
- Contact page
- Team page
- Privacy policy and terms pages
- Custom 404 page
- Static assets for branding, books, team images, and page visuals
- Basic deployment support through `Procfile` and `passenger_wsgi.py`

---

## Repository Structure

```text
jsm-coop/
├── app.py
├── passenger_wsgi.py
├── Procfile
├── requirements.txt
├── README.md
├── blogs/
│   └── Markdown blog posts
├── data/
│   └── .gitkeep
├── static/
│   ├── css/
│   │   ├── admin.css
│   │   └── styles.css
│   ├── images/
│   │   ├── BOOK3D.png
│   │   ├── Logo.png
│   │   ├── camino.png
│   │   ├── jsm-placeholder.svg
│   │   └── team/
│   ├── js/
│   │   └── main.js
│   └── uploads/
│       └── .gitkeep
├── templates/
│   ├── 404.html
│   ├── about.html
│   ├── base.html
│   ├── blog_detail.html
│   ├── blogs.html
│   ├── book.html
│   ├── chapter_readings.html
│   ├── contact.html
│   ├── donate.html
│   ├── index.html
│   ├── newsletter.html
│   ├── novel_subscription.html
│   ├── privacy.html
│   ├── projects.html
│   ├── social.html
│   ├── team.html
│   ├── terms.html
│   ├── admin/
│   └── partials/
└── wordpress_export/
    ├── pages_raw/
    ├── posts_raw/
    ├── RECOVERED_SITE_AUDIT.md
    └── wordpress_content_audit.csv
```

---

## Public Pages

The site currently includes templates for:

- Home
- About
- Book
- Blog archive
- Blog detail
- Chapter readings
- Contact
- Donate
- Newsletter
- Novel subscription
- Privacy
- Projects
- Social links
- Team
- Terms
- 404

---



## Deployment Notes

This repository includes basic deployment files:

- `Procfile` for process-based hosting
- `passenger_wsgi.py` for Passenger/cPanel-style Flask hosting
- `requirements.txt` for Python package installation

Deployment settings may vary by host. Make sure production secrets are configured through the hosting provider’s environment variable system and not committed to GitHub.

---

## Environment Variables

Core site configuration:

- `SECRET_KEY`: Flask session secret for production.
- `SITE_NAME`: Public site name. Defaults to `JSM Cooperative Corporation`.
- `SITE_DOMAIN`: Canonical public domain, used for sitemap, canonical URLs, Open Graph, and schema. Defaults to `https://jsmcoop.com`.
- `CONTACT_EMAIL`: Public contact email.
- `PAYPAL_DONATE_BUTTON_ID`: Hosted PayPal donation button ID.
- `MAILCHIMP_ACTION_URL`: Mailchimp form POST URL for newsletter signup.
- `MAILCHIMP_HONEYPOT_NAME`: Mailchimp anti-bot field name.
- `YOUTUBE_URL`, `TIKTOK_URL`, `INSTAGRAM_URL`: Public social profile URLs.

Analytics and advertising:

- `GA_MEASUREMENT_ID`: Optional GA4 Measurement ID. Leave blank until GA4 is ready; the existing Google Ads tag remains active.
- `GOOGLE_ADS_CUSTOMER_ID`: Google Ads customer ID without dashes, for example `6517122239`.
- `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`: Google Ads API credentials used for server-side conversion uploads.
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID`: Optional manager account ID if using an MCC.
- `GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_ID`: Google Ads conversion action ID for the primary `PayPal checkout started` import-from-clicks conversion.
- `GOOGLE_ADS_PAYPAL_PURCHASE_CONVERSION_ACTION_ID`: Optional Google Ads conversion action ID for verified PayPal purchases after webhook matching.
- `GOOGLE_ADS_OFFLINE_CONVERSION_LOG`: Optional path for Google Ads upload attempts. Defaults to `data/google_ads_offline_conversions.jsonl`.

Signed-copy PayPal checkout:

- `PAYPAL_SIGNED_BOOK_URL`: PayPal Payment Link for the signed physical edition. Production value for this release: `https://www.paypal.com/ncp/payment/SLQDNTABMS9JS`.
- `BOOK_DIRECT_CHECKOUT_URL`: Central checkout URL used by `/book/checkout/start`. Production value for this release: `https://www.paypal.com/ncp/payment/SLQDNTABMS9JS`.
- `BOOK_DIRECT_PROVIDER`: Checkout provider label. Production value for this release: `PayPal`.
- `BOOK_DIRECT_PRICE_AMOUNT`: Book price before shipping for analytics display. Production value for this release: `15.00`.
- `BOOK_DIRECT_PRICE_CURRENCY`: Currency code for direct checkout analytics. Production value for this release: `USD`.
- `PAYPAL_API_BASE_URL`: PayPal REST API base URL. Defaults to `https://api-m.paypal.com` for live mode.
- `PAYPAL_CLIENT_ID`: Live PayPal REST app client ID for webhook verification.
- `PAYPAL_CLIENT_SECRET`: Live PayPal REST app secret for webhook verification. Keep this private and rotate it if it is ever exposed.
- `PAYPAL_WEBHOOK_ID`: PayPal webhook ID created after adding `https://jsmcoop.com/paypal/webhook` in the PayPal developer dashboard.
- `PAYPAL_WEBHOOK_EVENT_LOG`: Optional path for sanitized PayPal webhook event records. Defaults to `data/paypal_webhook_events.jsonl`.
- `PAYPAL_VERIFIED_PURCHASE_LOG`: Optional path for verified completed capture records. Defaults to `data/paypal_verified_purchases.jsonl`.

The signed-copy website copy should describe price as `$15 + shipping` because shipping is configured inside PayPal. Configure PayPal return URLs to `/book/checkout/success` and `/book/checkout/cancel`, and configure the live PayPal webhook listener URL as `https://jsmcoop.com/paypal/webhook`. Subscribe the webhook to `PAYMENT.CAPTURE.COMPLETED` for verified paid-purchase tracking.

When a visitor starts direct PayPal checkout, `/book/checkout/start` creates a local checkout ID, stores the Google Ads click attribution, passes that ID toward PayPal, and uploads a `PayPal checkout started` click conversion to Google Ads when the conversion action and Ads API credentials are configured. Create that Google Ads action as an import/offline conversion from clicks, then set its ID in `GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_ID`.

---

## Google Ads / Analytics Events

The site centralizes conversion events in `static/js/main.js` and preserves visit-level attribution for `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `gclid`, `gbraid`, and `wbraid`.

Implemented events:

- `purchase_modal_open`
- `book_preview_click`
- `retailer_click_amazon_us`
- `retailer_click_barnes_noble`
- `retailer_click_amazon_es`
- `direct_checkout_started`
- `direct_checkout_returned`
- `verified_direct_purchase_completed` is reserved for a future server-side PayPal/API verification flow and is not fired by the Payment Link MVP.
- `signed_copy_page_view`
- `signed_copy_checkout_click`
- `signed_copy_preview_click`
- `signed_page_preview_click`
- `signed_copy_gallery_interaction`
- `signed_copy_inscription_info_view`
- `pillar_article_view`
- `pillar_to_book_click`
- `pillar_preview_click`
- `pillar_signed_copy_click`
- `newsletter_signup`
- `donation_click`
- `camino_subscription_click`
- `camino_subscription_completed`

Recommended Google Ads conversion actions:

- Primary candidates: `direct_checkout_returned`, `camino_subscription_completed`, and future verified transactions such as `verified_direct_purchase_completed` after server-side verification exists.
- Secondary signals: `direct_checkout_started`, `retailer_click_amazon_us`, `retailer_click_barnes_noble`, `retailer_click_amazon_es`, `book_preview_click`, `signed_copy_preview_click`, `newsletter_signup`, `purchase_modal_open`.

Retailer outbound clicks and PayPal return visits should not be described as confirmed purchases.

---

## Admin Command Center Analytics

The Command Center uses first-party analytics for public visitor behavior and keeps admin pages out of tracking. Dashboard comparisons are gated by analytics coverage:

- `No Data`: no first-party events have been recorded.
- `Learning`: fewer than 7 tracked days.
- `Limited History`: 7 to 29 tracked days.
- `Full Comparison Available`: 30+ tracked days, with period comparison shown only when the selected previous window is actually covered.

Canonical page traffic is based on `page_view`. Exact page metrics such as `Book Page Views` count `/book` only; broader family metrics are labeled as ecosystem metrics. Legacy explicit view events remain accepted for compatibility, but they do not inflate canonical page-view counts.

Engagement events are lightweight and first-party: `engaged_30s`, `scroll_50`, `scroll_75`, and `scroll_90`. Each fires at most once per page view. Engagement Rate means unique page sessions with `engaged_30s` or `scroll_75` divided by page sessions.

Conversion rates are session-aware where possible:

- Visitor -> Action: sessions with at least one meaningful action divided by anonymous sessions.
- Book Visitor -> Action: book ecosystem sessions that produce a book action.
- Signed Page -> Checkout: `/book/signed` sessions that produce `direct_checkout_started`.
- Checkout -> Verified: verified PayPal purchases divided by unique checkout-start sessions, with an identity-linkage caveat.
- Newsletter Form -> Signup: successful signup sessions divided by newsletter form sessions.
- Camino Visit -> Approval: PayPal approval callbacks divided by subscription-page sessions.

Acquisition -> Outcome attributes each session from its first usable landing UTM, Google click identifier, referrer, or page-view source context, then attributes downstream actions in that session to the same source. Unknown event names are stored as `unknown_event` diagnostics with the original event name in metadata.

`Since Your Last Visit` uses a small admin SQLite visit table containing only admin username and timestamps. It calculates recent activity before recording the current visit. Google Ads offline upload health is shown from the local upload log.

Command Center V3 adds operating-focused sections without replacing the existing analytics system:

- `Today at JSM` is calculated from the current UTC day and remains independent from the selected 30/90-day reporting range.
- `Live Activity` shows recent meaningful actions only; routine page views remain in Event Explorer.
- Timeline annotations are stored in the admin SQLite database and can be added, edited, or deleted by authenticated admins with CSRF protection.
- `Site Audit` is an authenticated, on-demand check. It inspects bounded public routes, local Markdown/internal links, local static media references, editorial metadata, and publication warnings. It does not crawl external websites on normal admin page loads.
- `Editorial Health` is an internal completeness score for Markdown content. It is not a Google ranking score and does not automatically edit or publish content.
- Public 404s can be recorded as sanitized first-party `page_not_found` events with path and referrer domain context only.

Google Ads read reporting is separate from offline conversion upload:

- `GOOGLE_ADS_REPORT_CACHE_SECONDS`: optional cache TTL for read-only campaign reports. Defaults to `900`.
- Google Ads reporting uses `GOOGLE_ADS_CUSTOMER_ID`, optional `GOOGLE_ADS_LOGIN_CUSTOMER_ID`, `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, and `GOOGLE_ADS_REFRESH_TOKEN`.
- Connection states are shown as Connected, Authentication Error, Developer Token Pending, Insufficient Permissions, Configuration Missing, or API Unavailable.
- Campaign economics use Google Ads spend and JSM first-party outcomes where campaign attribution is defensible. ROAS uses verified direct book revenue only.
- Google Ads reported conversions and JSM verified purchases are shown as separate systems because attribution windows, conversion definitions, upload timing, and cross-device behavior can differ.

Search Console reporting is optional and cached:

- `GOOGLE_SEARCH_CONSOLE_SITE_URL`: Search Console property URL.
- `GOOGLE_SEARCH_CONSOLE_CREDENTIALS_JSON`: either a service-account JSON string or a path to a JSON file with Search Console read access.
- `SEARCH_CONSOLE_REPORT_CACHE_SECONDS`: optional cache TTL. Defaults to `900`.
- When Search Console is not connected, the Search & SEO tab still shows editorial health, metadata health, internal-link health, and setup status.

---


## License

All website code, written content, branding assets, and recovered site materials in this repository are maintained by **JSM Cooperative Corporation**, unless otherwise noted.

Reuse of organization-specific branding, copy, book materials, logos, images, and campaign content requires permission from JSM Cooperative Corporation.

---

## Contact

For public inquiries, visit:

**https://jsmcoop.com**

For book, publishing, or JSM Cooperative inquiries, use the contact options provided on the website.
