# 🎭 JSM Cooperative Flask Site

<p align="center">
  <strong>Stories that fund a better world.</strong>
</p>

<p align="center">
  <em>A custom Flask rebuild of the JSM Cooperative website, replacing the old WordPress/Page Builder setup with a clean, portable, Markdown-powered platform for books, blogs, donations, newsletters, and community impact.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Framework-Flask-blue?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Blog-Markdown-success?style=for-the-badge&logo=markdown" alt="Markdown Blog">
  <img src="https://img.shields.io/badge/Database-SQLite-lightgrey?style=for-the-badge&logo=sqlite" alt="SQLite">
  <img src="https://img.shields.io/badge/Status-Rebuild%20in%20Progress-orange?style=for-the-badge" alt="Rebuild in Progress">
</p>

<p align="center">
  <a href="https://jsmcoop.com">
    <img src="https://img.shields.io/badge/Website-JSMCoop.com-00eaff?style=for-the-badge&logo=googlechrome" alt="JSMCoop.com">
  </a>
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

## 🚀 Overview

**JSM Cooperative Flask Site** is the custom web platform for **JSM Cooperative Corporation**.

The site was rebuilt outside WordPress to create a faster, cleaner, more flexible foundation for:

- publishing books and creative campaigns
- hosting a Markdown-powered blog archive
- showcasing *The Man in the Ball Cap*
- collecting newsletter subscribers
- receiving contact form submissions
- supporting PayPal donation flows
- managing recovered WordPress content
- building future admin and analytics tools

This project is designed to replace the old WordPress/Page Builder setup with a site that is easier to version-control, customize, deploy, and expand.

---

## 🧭 Repository Navigation

- [Project Summary](#-project-summary)
- [Current Site Features](#-current-site-features)
- [Repository Structure](#-repository-structure)
- [Important Static Assets](#-important-static-assets)
- [Installation](#-installation)
- [Environment Variables](#-environment-variables)
- [Run Locally](#-run-locally)
- [Markdown Blog System](#-markdown-blog-system)
- [Database](#-database)
- [Admin Area](#-admin-area)
- [WordPress Recovery Archive](#-wordpress-recovery-archive)
- [Deployment Notes](#-deployment-notes)
- [Pre-Launch Checklist](#-pre-launch-checklist)
- [Common Commands](#-common-commands)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 📖 Project Summary

JSM Cooperative Corporation uses storytelling, publishing, and community campaigns to support mission-aligned nonprofit impact.

This Flask site is built around the current JSM ecosystem:

| Area | Purpose |
|---|---|
| Homepage | High-impact public landing page for the Co-op mission |
| Book page | Public page for *The Man in the Ball Cap* |
| Purchase modal | Clean popup for Amazon, Barnes & Noble, and Spanish edition purchase options |
| Blog archive | Filterable Markdown-powered blog archive |
| Blog detail pages | Polished long-form article layout with inline image support |
| Newsletter page | Camino newsletter signup and Mailchimp integration path |
| Novel subscription page | Camino subscription concept and support pathway |
| Donate page | PayPal donation integration |
| Contact page | Contact form and email action buttons |
| Team page | Public-facing JSM Cooperative team page |
| Admin area | Login-protected dashboard for contacts, subscribers, drafts, and analytics |
| WordPress archive | Local recovery folder for old raw WordPress pages/posts |

---

## ✨ Current Site Features

### Public-facing features

- Flask-powered routing
- Global header and footer
- Tron-inspired visual design language
- Responsive desktop/mobile navigation
- Purchase modal for book buying options
- Kindle preview embed support
- Markdown blog cards and article pages
- Blog filtering, search, and 6-post pagination
- Inline blog images with polished formatting
- Newsletter signup flow
- Contact form
- Donation page
- Privacy and terms pages
- Custom 404 page

### Admin/back-office features

- Simple admin login
- SQLite-backed contacts table
- SQLite-backed newsletter subscribers table
- Campaign notes table
- Blog draft/admin templates
- Analytics admin template placeholder

### Recovery/migration features

- Old WordPress export preserved
- Raw recovered pages stored locally
- Raw recovered posts stored locally
- Rewritten blog posts converted into clean Markdown
- Selected image assets migrated into `static/images/`

---

## 📁 Repository Structure

```text
JSMCoop-Flask-Starter/
├── app.py
├── passenger_wsgi.py
├── requirements.txt
├── README.md
├── blogs/
│   ├── welcome-to-jsm-cooperative.md
│   ├── the-man-in-the-ballcap.md
│   ├── the-camino.md
│   ├── the-man-in-the-ballcap-goes-spanish-a-new-chapter-in-our-journey.md
│   ├── empowering-change-how-every-book-purchase-fuels-our-mission.md
│   ├── marching-together-the-power-of-community-in-the-fight-against-alzheimers.md
│   ├── turning-pages-making-changes-jsm-cooperatives-leap-to-tax-exempt-status.md
│   ├── embracing-the-journey.md
│   ├── thanks-from-the-jsm-cooperative.md
│   ├── first-blog-post-for-jsm-cooperative-announcing-the-man-in-the-ballcap.md
│   ├── el-hombre-con-la-gorra.md
│   └── ...
├── data/
│   └── jsmcoop.db
├── static/
│   ├── css/
│   │   ├── styles.css
│   │   └── admin.css
│   ├── js/
│   │   └── main.js
│   ├── images/
│   │   ├── BOOK3D.png
│   │   ├── camino.png
│   │   ├── Logo.png
│   │   ├── jsm-placeholder.svg
│   │   └── team/
│   │       ├── esther-cora-rivera.jpg
│   │       ├── j-michael-schulz.jpeg
│   │       ├── jack-herman.jpg
│   │       ├── jack-scilla.jpg
│   │       ├── jacob-geller.png
│   │       ├── robert-suchor.gif
│   │       └── sdg.png
│   └── uploads/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── book.html
│   ├── blogs.html
│   ├── blog_detail.html
│   ├── newsletter.html
│   ├── novel_subscription.html
│   ├── donate.html
│   ├── contact.html
│   ├── team.html
│   ├── privacy.html
│   ├── terms.html
│   ├── 404.html
│   ├── partials/
│   │   └── purchase_modal.html
│   └── admin/
│       ├── login.html
│       ├── dashboard.html
│       ├── blog_form.html
│       └── analytics.html
└── wordpress_export/
    ├── pages_raw/
    ├── posts_raw/
    ├── RECOVERED_SITE_AUDIT.md
    └── wordpress_content_audit.csv# jsm-coop
