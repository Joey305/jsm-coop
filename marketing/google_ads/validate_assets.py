#!/usr/bin/env python3
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
TODAY = "2026-08-10"
FUTURE_SLUGS = {
    "a-coruna-through-the-lens-after-dark",
    "a-coruna-through-the-lens-before-the-city-wakes",
}
SENSITIVE = [
    "diabetes", "alzheimer", "patients", "diagnosis", "symptoms", "treatment",
    "cure", "clinical trial", "families with diabetes", "living with diabetes",
]

def read_csv(name):
    with (HERE / name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def error(errors, msg):
    errors.append(msg)

def check_url(url):
    safe = url.replace('{keyword}', 'keyword').replace('{creative}', 'creative')
    req = Request(safe, method='GET', headers={'User-Agent':'Mozilla/5.0 JSMAdsValidator'})
    with urlopen(req, timeout=15) as response:
        return response.status, response.geturl()

def main():
    errors=[]
    rsa=read_csv('responsive_search_ads.csv')
    neg=read_csv('negative_keywords.csv')
    campaigns=json.loads((HERE/'campaigns.yaml').read_text(encoding='utf-8'))['campaigns']
    neg_campaigns={r['Campaign'] for r in neg}

    for row_num,row in enumerate(rsa, start=2):
        campaign=row['campaign']
        final=row['final URL']
        if 'utm_campaign=' not in final:
            error(errors, f'RSA row {row_num}: missing utm_campaign')
        if any(slug in final for slug in FUTURE_SLUGS):
            error(errors, f'RSA row {row_num}: future-dated landing page used')
        for path_field in ['path 1','path 2']:
            if len(row[path_field]) > 15:
                error(errors, f'RSA row {row_num}: {path_field} exceeds 15 chars')
        heads=[row[f'headline {i}'].strip() for i in range(1,16) if row[f'headline {i}'].strip()]
        descs=[row[f'description {i}'].strip() for i in range(1,5) if row[f'description {i}'].strip()]
        if len(heads) < 10:
            error(errors, f'RSA row {row_num}: fewer than 10 headlines')
        if len(descs) != 4:
            error(errors, f'RSA row {row_num}: must have 4 descriptions')
        for h in heads:
            if len(h) > 30:
                error(errors, f'RSA row {row_num}: headline too long ({len(h)}): {h}')
        for d in descs:
            if len(d) > 90:
                error(errors, f'RSA row {row_num}: description too long ({len(d)}): {d}')
        if len(set(h.lower() for h in heads)) < len(heads) - 1:
            error(errors, f'RSA row {row_num}: excessive duplicate headlines')
        text=' '.join(heads+descs).lower()
        bad=[s for s in SENSITIVE if re.search(r'\b' + re.escape(s) + r'\b', text)]
        if bad:
            error(errors, f'RSA row {row_num}: sensitive health language detected: {bad}')
        if campaign not in neg_campaigns:
            error(errors, f'RSA row {row_num}: campaign has no negatives')
        parsed=urlsplit(final)
        if parsed.netloc != 'jsmcoop.com':
            error(errors, f'RSA row {row_num}: final URL outside jsmcoop.com')

    checked=[]
    for c in campaigns:
        url = 'https://jsmcoop.com' + c['primary_landing_page']
        if any(slug in url for slug in FUTURE_SLUGS):
            error(errors, f"{c['name']}: future-dated landing page configured")
            continue
        try:
            status, resolved = check_url(url)
            checked.append((url,status,resolved))
            if status != 200:
                error(errors, f"{c['name']}: URL returned {status}: {url}")
        except Exception as exc:
            error(errors, f"{c['name']}: URL check failed for {url}: {exc}")

    report = ['# Validation Report', '', f'RSA rows checked: {len(rsa)}', f'Landing URLs checked: {len(checked)}', f'Errors: {len(errors)}', '']
    if checked:
        report.append('## URL Checks')
        report += [f'- {status} `{url}` -> `{resolved}`' for url,status,resolved in checked]
        report.append('')
    if errors:
        report.append('## Errors')
        report += [f'- {e}' for e in errors]
    else:
        report.append('All validation checks passed.')
    (HERE/'validation_report.md').write_text('\n'.join(report)+'\n', encoding='utf-8')
    if errors:
        print('\n'.join(errors))
        return 1
    print('All validation checks passed.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
