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


## License

All website code, written content, branding assets, and recovered site materials in this repository are maintained by **JSM Cooperative Corporation**, unless otherwise noted.

Reuse of organization-specific branding, copy, book materials, logos, images, and campaign content requires permission from JSM Cooperative Corporation.

---

## Contact

For public inquiries, visit:

**https://jsmcoop.com**

For book, publishing, or JSM Cooperative inquiries, use the contact options provided on the website.
