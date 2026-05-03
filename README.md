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

## WordPress Recovery Archive

The `wordpress_export/` folder contains recovered public-facing WordPress content from the previous site migration.

It is kept in this repository as a reference archive for rebuilding, auditing, and preserving public site content during the transition from WordPress to Flask.

Before publishing future migration exports, make sure no private drafts, credentials, customer data, contact submissions, or personal information are included.

---

## Local Setup

Clone the repository:

```bash
git clone https://github.com/Joey305/jsm-coop.git
cd jsm-coop
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Run the app locally:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

If your app uses a custom port in `app.py`, use that port instead.

---

## Environment Variables

Create a `.env` file locally for deployment-specific settings.

Example:

```env
SECRET_KEY=replace-with-a-long-random-secret
FLASK_ENV=development
MAILCHIMP_API_KEY=your-mailchimp-api-key
MAILCHIMP_SERVER_PREFIX=us00
MAILCHIMP_AUDIENCE_ID=your-mailchimp-audience-id
PAYPAL_DONATE_URL=https://www.paypal.com/donate/your-donation-link
CONTACT_EMAIL=books@jsmcoop.com
```

Do **not** commit `.env` or production secrets.

A safe `.env.example` may be committed to show required variable names without exposing real credentials.

---

## Recommended `.gitignore`

The repository should ignore local secrets, runtime databases, generated files, and operating system artifacts.

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.venv/
venv/

# Flask/runtime
instance/
*.db
*.sqlite
*.sqlite3

# Local uploads/runtime data
static/uploads/*
!static/uploads/.gitkeep
data/*
!data/.gitkeep

# Environment/secrets
.env
.env.*
!.env.example

# OS/editor
.DS_Store
.vscode/
.idea/
```

---

## Deployment Notes

This repository includes basic deployment files:

- `Procfile` for process-based hosting
- `passenger_wsgi.py` for Passenger/cPanel-style Flask hosting
- `requirements.txt` for Python package installation

Deployment settings may vary by host. Make sure production secrets are configured through the hosting provider’s environment variable system and not committed to GitHub.

---

## Public Repository Safety Checklist

Before making this repository public, confirm:

- No `.env` file is committed
- No API keys, passwords, tokens, or private credentials are committed
- No real SQLite database is committed
- `data/` contains only `.gitkeep` unless intentionally publishing public data
- `static/uploads/` contains only `.gitkeep` unless intentionally publishing public files
- `wordpress_export/` contains only public website recovery content
- `.DS_Store` files are removed
- Contact forms and newsletter integrations do not expose private keys in frontend code
- Admin routes do not contain hardcoded credentials

Useful checks:

```bash
git status
git ls-files
grep -RniE "password|secret|token|api_key|apikey|mailchimp|private|gmail|subscriber|contact|admin" .
```

Remove macOS `.DS_Store` files before publishing:

```bash
find . -name ".DS_Store" -delete
git add -A
git commit -m "Remove macOS system files"
```

---

## License

All website code, written content, branding assets, and recovered site materials in this repository are maintained by **JSM Cooperative Corporation**, unless otherwise noted.

Reuse of organization-specific branding, copy, book materials, logos, images, and campaign content requires permission from JSM Cooperative Corporation.

---

## Contact

For public inquiries, visit:

**https://jsmcoop.com**

For book, publishing, or JSM Cooperative inquiries, use the contact options provided on the website.
