# Tracking Plan

## Existing Architecture

The site already loads the Google Ads tag `AW-16512731660` in `templates/base.html`. GA4 can be added through `GA_MEASUREMENT_ID`. `static/js/main.js` captures `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, and `gclid` into session storage and attaches attribution to tracked events.

A minimal tracking fix was made so PayPal checkout-start links can append stored UTM/GCLID fields without throwing a JavaScript reference error.

## Conversion Hierarchy

### Primary

- `verified_direct_purchase_completed` - reserved for future server-side PayPal/API verification; do not fire until technically verified.
- `camino_subscription_completed` - PayPal subscription approval in the Camino flow.
- `newsletter_signup` - strategically primary for discovery/mission campaigns only after Mailchimp submission behavior is verified.

### Secondary

- `direct_checkout_started` - PayPal checkout initiation for signed copy.
- `direct_checkout_returned` - return from PayPal; useful but not proof of payment.
- `signed_copy_checkout_click` - signed direct CTA click.
- `book_preview_click` / `signed_copy_preview_click` / `signed_page_preview_click` - preview engagement.
- `retailer_click_amazon_us`, `retailer_click_barnes_noble`, `retailer_click_amazon_es` - retailer outbound intent.
- `camino_subscription_click` - subscription-start intent.

### Diagnostic

- `pillar_article_view` - currently fired only on the Galicia mystery pillar article.
- `pillar_to_book_click`, `pillar_preview_click`, `pillar_signed_copy_click` - article CTA paths.
- Proposed GA4-only diagnostics: engaged article visit, scroll depth, second page/session, A Coruña series click.

## Google Ads Conversion Recommendations

- Do not mark every page view as a primary conversion.
- Import or create only meaningful primary actions for bidding.
- Keep preview clicks, retailer outbound clicks, signed-copy CTA clicks, and article engagement as secondary or observation-only until value is proven.
- Treat `direct_checkout_returned` as purchase-intent or likely checkout completion, not as a verified completed purchase.
- Add server-side PayPal verification later before using `verified_direct_purchase_completed` as the main purchase conversion.

## UTM / GCLID Standard

Use this final URL suffix on every campaign:

`utm_source=google&utm_medium=cpc&utm_campaign=<campaign_id>&utm_term={keyword}&utm_content={creative}`

Campaign IDs:

- `jsm_acoruna_tower` -> `JSM | Search | ACoruna Tower | EN`
- `jsm_acoruna_old_town` -> `JSM | Search | ACoruna Old Town | EN`
- `jsm_acoruna_coast` -> `JSM | Search | ACoruna Coast | EN`
- `jsm_maria_pita` -> `JSM | Search | Maria Pita | EN`
- `jsm_rainy_galicia` -> `JSM | Search | Rainy Galicia | EN`
- `jsm_galicia_mystery` -> `JSM | Search | Galicia Mystery | EN`
- `jsm_mystery_preview` -> `JSM | Search | Mystery Book Preview | EN`
- `jsm_signed_mystery` -> `JSM | Search | Signed Mystery Book | EN`
- `jsm_misterio_coruna_es` -> `JSM | Search | Misterio Coruna | ES`
- `jsm_stories_impact` -> `JSM | Search | Stories With Impact | EN`

Preserve auto-tagging. Do not introduce redirects that strip `gclid` or UTM parameters. `/book/checkout/start` already forwards recognized attribution parameters to the PayPal payment link when present.

## Limitations

- PayPal Payment Links do not prove purchase completion to the website unless PayPal return/webhook/API verification is implemented.
- Newsletter forms post to Mailchimp; client-side `newsletter_signup` may fire on submit, not on confirmed Mailchimp acceptance.
- Retailer purchases on Amazon/Barnes & Noble cannot be measured as completed purchases from the site without external reporting.
