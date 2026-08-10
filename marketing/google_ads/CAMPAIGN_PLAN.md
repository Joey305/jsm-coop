# JSM Cooperative Google Ads Acquisition System

Prepared against `https://jsmcoop.com` on 2026-08-10. All proposed campaigns are configured as `PAUSED` review assets; no live spend was started.

## Strategy

This plan treats Google Search as a set of doors into the JSM ecosystem: A Coruña travel research, Galicia atmosphere, mystery discovery, preview intent, signed-copy purchase intent, Spanish-language readers, and mission/community interest. The top-of-funnel ads promise useful content first, then use sitelinks and internal CTAs to let readers continue toward articles, the book preview, signed copy, newsletter, and Camino.

## Current Site Signals Used

- Flask routes validated: `/book`, `/book/signed`, `/blogs`, `/blogs/the-camino`, `/novel-subscription/`, all selected blog landing pages, `/privacy`, and `/terms`.
- Blog system: Markdown files in `blogs/`, sorted by front-matter date, rendered by Flask with Markdown `extra`, `toc`, `tables`, and `attr_list`.
- Tracking: Google Ads base tag `AW-16512731660`, optional GA4 via `GA_MEASUREMENT_ID`, JSMAnalytics events, UTM/GCLID session storage, PayPal checkout-start attribution preservation, and PayPal return tracking.
- Purchase facts validated in repo: signed physical paperback, personally signed, `#JoinTheCamino` inscription, optional PayPal inscription request, direct from JSM, advertised as `$15 + shipping`.

## Campaign Matrix

### JSM | Search | ACoruna Tower | EN
- Intent: Tower of Hercules / A Coruña travel discovery
- Funnel stage: discovery
- Primary landing page: `/blogs/a-coruna-through-the-lens-tower-of-hercules`
- UTM campaign: `jsm_acoruna_tower`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Travel Lens / Story City
- Recommended geo: Review: United States, United Kingdom, Ireland, Canada, Australia, and English-speaking travelers researching Spain/Galicia; narrow after search-term data.
- Conversion goal: Engaged article visit, second article/session, book-page visit
- Initial bidding: Start with Maximize Clicks or manual CPC cap while learning; move to conversion-focused bidding only after reliable secondary/primary conversions accrue.

### JSM | Search | ACoruna Old Town | EN
- Intent: Ciudad Vieja / historic A Coruña
- Funnel stage: discovery
- Primary landing page: `/blogs/a-coruna-through-the-lens-ciudad-vieja`
- UTM campaign: `jsm_acoruna_old_town`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Historic Walk / Layered City
- Recommended geo: Review: English-speaking travelers researching Spain, Galicia, cruise/rail city trips, and cultural city breaks.
- Conversion goal: Engaged article visit, internal article click, book-page visit
- Initial bidding: Maximize Clicks or traffic-learning strategy initially; defer conversion bidding until engagement goals are imported and stable.

### JSM | Search | ACoruna Coast | EN
- Intent: Paseo Marítimo / Atlantic coastline
- Funnel stage: discovery
- Primary landing page: `/blogs/a-coruna-through-the-lens-paseo-maritimo`
- UTM campaign: `jsm_acoruna_coast`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Coastal Discovery / Atlantic City
- Recommended geo: Review: English-speaking travelers and Galicia/A Coruña researchers in US, UK, Ireland, Canada, Australia, and selected EU markets.
- Conversion goal: Engaged article visit, A Coruña series click, book-page visit
- Initial bidding: Maximize Clicks with close search-term review; no broad match until conversion data supports it.

### JSM | Search | Maria Pita | EN
- Intent: Plaza de María Pita / central A Coruña
- Funnel stage: discovery
- Primary landing page: `/blogs/a-coruna-through-the-lens-maria-pita`
- UTM campaign: `jsm_maria_pita`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Central Square / City Rhythm
- Recommended geo: Review: English-language destination researchers for A Coruña and Galicia; include Spain only if English-language settings are selected.
- Conversion goal: Engaged article visit, A Coruña article depth, book-page visit
- Initial bidding: Maximize Clicks initially; optimize to engaged visits once GA4/Ads secondary conversions are reliable.

### JSM | Search | Rainy Galicia | EN
- Intent: Atmospheric Galicia and rainy A Coruña
- Funnel stage: discovery
- Primary landing page: `/blogs/a-rainy-day-in-a-coruna-through-the-lens`
- UTM campaign: `jsm_rainy_galicia`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Rainy Travel / Atmosphere
- Recommended geo: Review: English-speaking Galicia travelers, photography/culture researchers, and Spain city-break planners.
- Conversion goal: Engaged article visit, article-to-book click, newsletter signup
- Initial bidding: Maximize Clicks with conservative CPC ceiling; do not optimize to weather-forecast traffic.

### JSM | Search | Galicia Mystery | EN
- Intent: Mystery fiction + A Coruña/Galicia
- Funnel stage: mid-funnel
- Primary landing page: `/blogs/mystery-memory-galicia-man-in-the-ball-cap`
- UTM campaign: `jsm_galicia_mystery`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Place Mystery / Character Hook
- Recommended geo: Review: English-speaking mystery readers in US, UK, Ireland, Canada, Australia, and Spain/Galicia interest markets.
- Conversion goal: Book-page visit, preview click, signed-copy CTA click
- Initial bidding: Start Maximize Clicks or Maximize Conversions only if secondary conversions are configured; avoid Target CPA until volume exists.

### JSM | Search | Mystery Book Preview | EN
- Intent: High-intent mystery readers and free preview intent
- Funnel stage: mid/high-funnel
- Primary landing page: `/book`
- UTM campaign: `jsm_mystery_preview`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Preview First / Reader Fit
- Recommended geo: Review: English-speaking book buyers/readers in US, UK, Ireland, Canada, Australia; expand based on conversion quality.
- Conversion goal: Free preview click, retailer outbound click, signed-copy CTA click
- Initial bidding: Use Maximize Conversions if preview/outbound conversions are clean; otherwise Maximize Clicks with tight exact/phrase match.

### JSM | Search | Signed Mystery Book | EN
- Intent: Signed physical mystery edition
- Funnel stage: high-intent
- Primary landing page: `/book/signed`
- UTM campaign: `jsm_signed_mystery`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Signed Gift / Direct Response
- Recommended geo: Review: countries JSM can fulfill signed-copy shipping to reliably; start where PayPal/shipping support is confirmed.
- Conversion goal: Direct checkout start, checkout return, signed-copy CTA click
- Initial bidding: Use conversion-focused bidding only after checkout-start and PayPal-return data are validated; never treat PayPal return as verified purchase.

### JSM | Search | Misterio Coruna | ES
- Intent: Spanish-language mystery novel set in A Coruña
- Funnel stage: mid-funnel
- Primary landing page: `/blogs/el-hombre-con-la-gorra`
- UTM campaign: `jsm_misterio_coruna_es`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Descubrimiento / Lectores ES
- Recommended geo: Review: Spain, Galicia, and Spanish-language markets; use Spanish language setting and avoid English ad copy.
- Conversion goal: Spanish article engagement, Spanish retailer click, preview click
- Initial bidding: Start with exact/phrase and Maximize Clicks or conversion-focused bidding only when Spanish events are separated cleanly.

### JSM | Search | Stories With Impact | EN
- Intent: JSM Cooperative, The Camino, storytelling for social good
- Funnel stage: discovery/mid-funnel
- Primary landing page: `/blogs/the-camino`
- UTM campaign: `jsm_stories_impact`
- Keyword strategy: exact and phrase match first; exploratory phrase terms separated for review; no broad match at launch.
- Messaging angle: Mission Story / Camino Community
- Recommended geo: Review: nonprofit publishing/social-impact readers in US and relevant English-speaking markets; do not target medical-condition audiences.
- Conversion goal: Newsletter signup, Camino subscription click/completed, book preview click
- Initial bidding: If standard Ads: Maximize Clicks until newsletter/subscription conversions are stable; if converted to Ad Grants, use conversion-based Smart Bidding per policy.

## Manual Review Before Launch

- Confirm Google Ads account type in Billing/Account settings before importing. Current UI spend and daily budgets indicate standard paid Ads, not Ad Grants.
- Import campaigns as paused or keep drafts paused.
- Assign real budgets only after owner review.
- Confirm conversion actions in Google Ads and GA4 before using conversion bidding.
- Fix or decide how to handle current disapproved campaigns separately; this plan does not alter existing campaigns.
