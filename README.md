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

---

## Google Ads / Analytics Events

The site centralizes conversion events in `static/js/main.js` and preserves visit-level attribution for `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, and `gclid`.

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


## License

All website code, written content, branding assets, and recovered site materials in this repository are maintained by **JSM Cooperative Corporation**, unless otherwise noted.

Reuse of organization-specific branding, copy, book materials, logos, images, and campaign content requires permission from JSM Cooperative Corporation.

---

## Contact

For public inquiries, visit:

**https://jsmcoop.com**

For book, publishing, or JSM Cooperative inquiries, use the contact options provided on the website.
