# JSM Cooperative Flask Starter

A clean full-stack Flask starter for rebuilding **JSMCoop.com** outside WordPress.

This project includes:

- Flask backend in `app.py`
- reusable templates with a global header/footer
- static assets in `static/css`, `static/js`, and `static/images`
- Markdown-based blog system in `blogs/`
- blog listing and blog detail pages
- contact form stored in SQLite
- newsletter signup stored in SQLite and optionally submitted to Mailchimp later
- simple admin login
- admin dashboard for contact submissions, subscribers, and blog drafts
- custom 404 page
- PayPal donation form placeholder using the existing hosted button ID
- deployment-friendly `passenger_wsgi.py`

## Project structure

```text
JSMCoop-Flask-Starter/
├── app.py
├── passenger_wsgi.py
├── requirements.txt
├── .env.example
├── README.md
├── blogs/
│   ├── welcome-to-jsm-cooperative.md
│   ├── the-man-in-the-ballcap.md
│   └── the-camino.md
├── data/
│   └── .gitkeep
├── static/
│   ├── css/
│   │   ├── styles.css
│   │   └── admin.css
│   ├── js/
│   │   └── main.js
│   ├── images/
│   │   └── jsm-placeholder.svg
│   └── uploads/
│       └── .gitkeep
└── templates/
    ├── base.html
    ├── index.html
    ├── about.html
    ├── book.html
    ├── blogs.html
    ├── blog_detail.html
    ├── projects.html
    ├── donate.html
    ├── contact.html
    ├── privacy.html
    ├── terms.html
    ├── 404.html
    └── admin/
        ├── login.html
        ├── dashboard.html
        ├── blog_form.html
        └── analytics.html
```

## Run locally

```bash
cd JSMCoop-Flask-Starter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

Admin:

```text
http://127.0.0.1:5000/admin
```

Default admin credentials come from `.env.example`; change them before deploying.

## Add a blog post

Create a new Markdown file inside `blogs/`.

Example:

```markdown
---
title: My New Update
date: 2026-05-02
author: JSM Cooperative
excerpt: A short teaser that appears on the blog listing.
cover: /static/images/jsm-placeholder.svg
tags: Camino, Books, Nonprofit
---

Your blog content goes here.
```

## Contact form and newsletter data

The app creates a SQLite database at:

```text
data/jsmcoop.db
```

Tables:

- `contacts`
- `newsletter_subscribers`
- `campaign_notes`

## Notes for Hostinger or another host

This package includes `passenger_wsgi.py`, which is commonly used by Python app hosting panels that run WSGI apps. Hosting setups vary, so verify your exact hosting plan supports Python/Flask before deploying.

For VPS deployment, use Gunicorn + Nginx.

Example:

```bash
pip install gunicorn
gunicorn -w 3 -b 127.0.0.1:8000 app:app
```

## Next build steps

Recommended next steps:

1. Replace placeholder SVG/image assets with real JSM visuals.
2. Move any recovered WordPress page copy into the matching templates.
3. Add a real database-backed blog editor if you want richer CMS behavior.
4. Add Google Analytics / Google Ads conversion tracking once the domain is live.
5. Build a Google Ads reporting sync module later using the Google Ads API.
6. Add email sending for the contact form through Gmail SMTP, SendGrid, Mailgun, or Hostinger email.
