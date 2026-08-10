# Google Ads Policy Review

## Current Requirements Checked

- Responsive Search Ads: up to 15 headlines, up to 4 descriptions, 30-character headline limit, 90-character description limit, 15-character path fields, minimum 3 headlines and 2 descriptions.
- Standard Google Ads policies apply to destinations, editorial quality, data collection/use, misrepresentation, healthcare/medicines, and personalized advertising.
- Google Ad Grants rules are stricter if the account is a Grant account: no single-word keywords, no overly generic keywords, quality score 1-2 cleanup, 5% monthly CTR, valid conversion tracking, at least 2 ad groups/campaign, at least 2 sitelinks, and meaningful conversions.

Official references checked:

- Google Ads Help: https://support.google.com/google-ads/answer/6167122
- Google Ads destination requirements: https://support.google.com/adspolicy/answer/6368661
- Google Ads data collection and use: https://support.google.com/adspolicy/answer/6020956
- Google Ad Grants account management policy: https://support.google.com/nonprofits/answer/117827

## Account Type

No Google Ads API credentials or Ad Grants configuration were found in the repository. The live Google Ads UI showed paid spend and daily budgets far above typical Ad Grants patterns, so this plan treats the account as standard paid Google Ads. Confirm in Google Ads before launch.

## Destination Risks

- Selected final URLs return 200 and are on `https://jsmcoop.com`.
- Top-of-funnel articles provide original content and are not thin bridge pages.
- The site has privacy and terms pages.
- Future-dated articles are publicly exposed but excluded from ads.
- Existing account has disapproved ads/destination or certification issues; resolve separately before relying on similar destinations.

## Editorial Risks

- Avoid excessive capitalization, repeated punctuation, unsupported guarantees, fake urgency, or claims that every reader will buy/donate.
- Do not hard-code price outside signed-copy campaign review; current website says `$15 + shipping`.
- Do not imply official Google, Tower of Hercules, A Coruña city, or Galicia tourism endorsement.

## Sensitive / Health Targeting

Some JSM pages mention diabetes, Alzheimer's, brain health, and nonprofit work. This campaign system intentionally avoids targeting medical conditions, patient identities, caregivers, disease symptoms, diagnosis, treatment, prevention, remarketing lists, Customer Match, or advertiser-curated sensitive audiences.

Allowed mission angle: stories, publishing, community, Camino, nonprofit impact.

Avoid ad copy like:

- Living with diabetes?
- Alzheimer's affecting your family?
- Your diabetes may...

## Production Readiness

Ready for account import review, not for automatic launch. Campaigns must remain paused until final human review, budget assignment, conversion setup, and policy checks are complete.
