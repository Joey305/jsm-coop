import os
import re
from datetime import datetime
from pathlib import Path
from functools import wraps
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from werkzeug.utils import secure_filename
import mimetypes


from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
    jsonify,
)
from markupsafe import Markup
import markdown as md


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BLOG_DIR = BASE_DIR / "blogs"

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
app.config["SITE_NAME"] = os.getenv("SITE_NAME", "JSM Cooperative Corporation")
app.config["SITE_DOMAIN"] = os.getenv("SITE_DOMAIN", "https://jsmcoop.com")
app.config["CONTACT_EMAIL"] = os.getenv("CONTACT_EMAIL", "books@jsmcoop.com")
app.config["PAYPAL_DONATE_BUTTON_ID"] = os.getenv("PAYPAL_DONATE_BUTTON_ID", "TLWCSL2KJDZQU")
app.config["BLOG_IMAGE_UPLOAD_DIR"] = BASE_DIR / "static" / "images" / "blog"
app.config["BLOG_VIDEO_UPLOAD_DIR"] = BASE_DIR / "static" / "videos" / "blog"

app.config["BLOG_IMAGE_URL_PREFIX"] = "images/blog"
app.config["BLOG_VIDEO_URL_PREFIX"] = "videos/blog"

app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB upload limit

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}


# Use the exact Mailchimp POST action URL from your embedded form.
# Example:
# https://jsmcoop.us22.list-manage.com/subscribe/post?u=...&id=...&f_id=...
app.config["MAILCHIMP_ACTION_URL"] = os.getenv("MAILCHIMP_ACTION_URL", "").replace("&amp;", "&")
app.config["MAILCHIMP_HONEYPOT_NAME"] = os.getenv("MAILCHIMP_HONEYPOT_NAME", "")

app.config["YOUTUBE_URL"] = os.getenv("YOUTUBE_URL", "https://www.youtube.com/@JSm.cooperative")
app.config["TIKTOK_URL"] = os.getenv("TIKTOK_URL", "https://www.tiktok.com/@jsm.cooperative")
app.config["INSTAGRAM_URL"] = os.getenv("INSTAGRAM_URL", "https://www.instagram.com/jsm.cooperative/")


NAV_ITEMS = [
    ("Home", "home"),
    ("Newsletter", "newsletter_page"),
    ("Blogs", "blogs"),
    ("Our Team", "team"),
    ("Chapter Readings", "chapter_readings"),
    ("Donate", "donate"),
    ("Contact", "contact"),
]





def get_file_extension(filename):
    if "." not in filename:
        return ""

    return filename.rsplit(".", 1)[1].lower().strip()


def make_unique_path(directory, filename):
    directory.mkdir(parents=True, exist_ok=True)

    candidate = directory / filename

    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    return directory / f"{stem}-{timestamp}{suffix}"


def build_safe_upload_filename(original_filename, requested_filename=""):
    original_filename = secure_filename(original_filename or "")
    requested_filename = secure_filename(requested_filename or "")

    original_ext = get_file_extension(original_filename)

    if not original_filename or not original_ext:
        return None, None

    if requested_filename:
        requested_ext = get_file_extension(requested_filename)

        if requested_ext:
            safe_filename = requested_filename
        else:
            safe_filename = f"{requested_filename}.{original_ext}"
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        original_stem = Path(original_filename).stem
        safe_filename = f"{original_stem}-{timestamp}.{original_ext}"

    return safe_filename, original_ext



@app.context_processor
def inject_globals():
    return {
        "nav_items": NAV_ITEMS,
        "site_name": app.config["SITE_NAME"],
        "site_domain": app.config["SITE_DOMAIN"],
        "contact_email": app.config["CONTACT_EMAIL"],
        "paypal_donate_button_id": app.config["PAYPAL_DONATE_BUTTON_ID"],
        "mailchimp_action_url": app.config["MAILCHIMP_ACTION_URL"],
        "mailchimp_honeypot_name": app.config["MAILCHIMP_HONEYPOT_NAME"],
        "current_year": datetime.now().year,
        "social_links": {
            "youtube": app.config["YOUTUBE_URL"],
            "tiktok": app.config["TIKTOK_URL"],
            "instagram": app.config["INSTAGRAM_URL"],
        },
    }


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")



def parse_front_matter(raw):
    metadata = {}
    body = raw

    # Remove invisible BOM if a file was saved from another editor
    raw = raw.lstrip("\ufeff")

    # Match only real front matter delimiters on their own lines
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.DOTALL)

    if match:
        header = match.group(1)
        body = match.group(2).strip()

        for line in header.splitlines():
            line = line.strip()

            if not line or ":" not in line:
                continue

            key, val = line.split(":", 1)

            key = key.strip().lower()
            val = val.strip()

            # Strip wrapping quotes only, not quotes inside the text
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]

            metadata[key] = val

    return metadata, body




def read_blog_file(path):
    raw = path.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(raw)
    slug = path.stem

    html = Markup(
        md.markdown(
            body,
            extensions=["extra", "toc", "tables", "attr_list"],
        )
    )

    return {
        "slug": slug,
        "title": metadata.get("title", slug.replace("-", " ").title()),
        "date": metadata.get("date", "Undated"),
        "author": metadata.get("author", "JSM Cooperative"),
        "excerpt": metadata.get("excerpt", body[:180].replace("\n", " ") + "..."),
        "cover": metadata.get("cover", "/static/images/jsm-placeholder.svg"),
        "tags": [t.strip() for t in metadata.get("tags", "").split(",") if t.strip()],
        "body": body,
        "html": html,
        "path": path,
    }


def get_posts():
    BLOG_DIR.mkdir(exist_ok=True)
    posts = []

    for path in BLOG_DIR.glob("*.md"):
        posts.append(read_blog_file(path))

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def get_post(slug):
    path = BLOG_DIR / f"{slug}.md"

    if not path.exists():
        return None

    return read_blog_file(path)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in first.", "warning")
            return redirect(url_for("admin_login"))

        return view(*args, **kwargs)

    return wrapper


def build_mailto_url(name, email, subject, message):
    contact_email = app.config["CONTACT_EMAIL"]

    safe_subject = subject or "JSM Cooperative Website Inquiry"

    body = f"""Name: {name}
Email: {email}

Message:
{message}
"""

    query = urlencode(
        {
            "subject": safe_subject,
            "body": body,
        },
        quote_via=quote,
    )

    return f"mailto:{contact_email}?{query}"


def build_mailchimp_payload(email, first_name="", last_name="", phone=""):
    payload = {
        "EMAIL": email,
        "FNAME": first_name,
        "LNAME": last_name,
        "PHONE": phone,
    }

    honeypot_name = app.config.get("MAILCHIMP_HONEYPOT_NAME", "").strip()
    if honeypot_name:
        payload[honeypot_name] = ""

    return payload


def submit_to_mailchimp(email, first_name="", last_name="", phone=""):
    action_url = app.config["MAILCHIMP_ACTION_URL"]

    if not action_url:
        raise RuntimeError("MAILCHIMP_ACTION_URL is not configured.")

    payload = build_mailchimp_payload(email, first_name, last_name, phone)
    encoded_payload = urlencode(payload).encode("utf-8")

    req = Request(
        action_url,
        data=encoded_payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 JSMCoop-Flask",
        },
        method="POST",
    )

    with urlopen(req, timeout=12) as response:
        return response.status < 400


def render_mailchimp_forward_form(email, first_name="", last_name="", phone=""):
    action_url = app.config["MAILCHIMP_ACTION_URL"]

    if not action_url:
        flash("Newsletter signup is temporarily unavailable. Please try again soon.", "error")
        return redirect(url_for("newsletter_page"))

    payload = build_mailchimp_payload(email, first_name, last_name, phone)

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Joining The Camino...</title>
          <style>
            body {
              margin: 0;
              min-height: 100vh;
              display: grid;
              place-items: center;
              background:
                radial-gradient(circle at top, rgba(0,234,255,0.15), transparent 35%),
                linear-gradient(180deg, #06101f, #020617);
              color: #e5e7eb;
              font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }

            .card {
              width: min(92vw, 520px);
              padding: 2rem;
              border-radius: 28px;
              background: rgba(255,255,255,0.06);
              border: 1px solid rgba(255,255,255,0.12);
              box-shadow: 0 24px 70px rgba(0,0,0,0.32);
              text-align: center;
            }

            h1 {
              margin: 0 0 0.75rem;
              color: #ffffff;
              letter-spacing: -0.04em;
            }

            p {
              color: rgba(203,213,225,0.82);
              line-height: 1.65;
            }

            button {
              margin-top: 1rem;
              border: 0;
              border-radius: 999px;
              padding: 0.85rem 1.25rem;
              font-weight: 900;
              cursor: pointer;
              color: #031016;
              background: linear-gradient(135deg, #00eaff, #4efedc);
            }
          </style>
        </head>

        <body>
          <main class="card">
            <h1>Joining The Camino...</h1>
            <p>
              We are securely sending your signup to Mailchimp.
              If nothing happens automatically, click the button below.
            </p>

            <form id="mailchimp-forward" action="{{ action_url }}" method="post">
              {% for key, value in payload.items() %}
                <input type="hidden" name="{{ key }}" value="{{ value }}">
              {% endfor %}

              <button type="submit">Continue</button>
            </form>
          </main>

          <script>
            document.addEventListener("DOMContentLoaded", function () {
              document.getElementById("mailchimp-forward").submit();
            });
          </script>
        </body>
        </html>
        """,
        action_url=action_url,
        payload=payload,
    )


@app.route("/")
def home():
    posts = get_posts()[:3]
    return render_template("index.html", title="Home", posts=posts)


@app.route("/about")
def about():
    return render_template("about.html", title="About")


@app.route("/book")
def book():
    return render_template("book.html", title="The Man in the Ball Cap")


@app.route("/blogs")
def blogs():
    posts = get_posts()
    return render_template("blogs.html", title="Blogs", posts=posts)


@app.route("/blogs/<slug>")
def blog_detail(slug):
    post = get_post(slug)

    if not post:
        abort(404)

    return render_template("blog_detail.html", title=post["title"], post=post)


@app.route("/projects")
def projects():
    return render_template("projects.html", title="Community Projects")


@app.route("/donate")
def donate():
    return render_template("donate.html", title="Donate")


@app.route("/team")
def team():
    return render_template("team.html", title="Our Team")


@app.route("/chapter-readings")
def chapter_readings():
    return render_template("chapter_readings.html", title="Chapter Readings")


@app.route("/novel-subscription")
def novel_subscription():
    return render_template("novel_subscription.html", title="Novel Subscription")


@app.route("/instagram")
def instagram():
    return render_template("social.html", title="Instagram", platform="Instagram")


@app.route("/tiktok")
def tiktok():
    return render_template("social.html", title="TikTok", platform="TikTok")


@app.route("/youtube")
def youtube():
    return render_template("social.html", title="YouTube", platform="YouTube")


@app.route("/contactus")
def contactus_alias():
    return redirect(url_for("contact"), code=301)


@app.route("/ns")
def novel_fundraiser_shortlink():
    return redirect(url_for("novel_subscription"), code=302)


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", title="Privacy Policy")


@app.route("/terms")
def terms():
    return render_template("terms.html", title="Terms / Disclaimer")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("Please include your name, email, and message.", "error")
            return redirect(url_for("contact"))

        mailto_url = build_mailto_url(name, email, subject, message)
        return redirect(mailto_url)

    return render_template("contact.html", title="Contact")


@app.route("/newsletter", methods=["GET", "POST"])
def newsletter_page():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        phone = request.form.get("phone", "").strip()

        if not email:
            flash("Please enter your email address.", "error")
            return redirect(url_for("newsletter_page"))

        return render_mailchimp_forward_form(email, first_name, last_name, phone)

    return render_template("newsletter.html", title="Newsletter")


@app.route("/api/health")
def api_health():
    return jsonify(
        {
            "status": "ok",
            "site": app.config["SITE_NAME"],
            "database": "disabled",
            "mailchimp_configured": bool(app.config["MAILCHIMP_ACTION_URL"]),
        }
    )


@app.route("/api/newsletter", methods=["POST"])
def api_newsletter():
    data = request.get_json(silent=True) or request.form

    email = (data.get("email") or "").strip()
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not email:
        return jsonify({"ok": False, "error": "Email is required."}), 400

    if not app.config["MAILCHIMP_ACTION_URL"]:
        return jsonify(
            {
                "ok": False,
                "error": "MAILCHIMP_ACTION_URL is not configured.",
            }
        ), 503

    try:
        submit_to_mailchimp(email, first_name, last_name, phone)
        return jsonify({"ok": True, "message": "Submitted to Mailchimp."})

    except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
        return jsonify(
            {
                "ok": False,
                "error": "Mailchimp submission failed.",
                "detail": str(exc),
            }
        ), 502


@app.route("/admin", methods=["GET"])
@login_required
def admin_dashboard():
    posts = get_posts()

    return render_template(
        "admin/dashboard.html",
        title="Admin Dashboard",
        contacts=[],
        subscribers=[],
        campaign_notes=[],
        posts=posts,
        database_disabled=True,
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        expected_user = os.getenv("ADMIN_USERNAME", "admin")
        expected_pass = os.getenv("ADMIN_PASSWORD", "change-this-password")

        if username == expected_user and password == expected_pass:
            session["admin_logged_in"] = True
            flash("Welcome back.", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Invalid login.", "error")

    return render_template("admin/login.html", title="Admin Login")

@app.route("/admin/media/upload", methods=["POST"])
@login_required
def admin_media_upload():
    uploaded_file = request.files.get("media")
    requested_filename = request.form.get("filename", "").strip()
    alt_text = request.form.get("alt_text", "").strip()

    if not uploaded_file or not uploaded_file.filename:
        return jsonify(
            {
                "ok": False,
                "error": "Please choose an image or video file first.",
            }
        ), 400

    safe_filename, ext = build_safe_upload_filename(
        uploaded_file.filename,
        requested_filename,
    )

    if not safe_filename or not ext:
        return jsonify(
            {
                "ok": False,
                "error": "Invalid filename.",
            }
        ), 400

    if ext in ALLOWED_IMAGE_EXTENSIONS:
        upload_dir = app.config["BLOG_IMAGE_UPLOAD_DIR"]
        url_prefix = app.config["BLOG_IMAGE_URL_PREFIX"]
        media_type = "image"

    elif ext in ALLOWED_VIDEO_EXTENSIONS:
        upload_dir = app.config["BLOG_VIDEO_UPLOAD_DIR"]
        url_prefix = app.config["BLOG_VIDEO_URL_PREFIX"]
        media_type = "video"

    else:
        return jsonify(
            {
                "ok": False,
                "error": "Unsupported file type. Please upload an image or video.",
            }
        ), 400

    target_path = make_unique_path(upload_dir, safe_filename)
    uploaded_file.save(target_path)

    media_url = url_for(
        "static",
        filename=f"{url_prefix}/{target_path.name}",
    )

    clean_alt = alt_text or target_path.stem.replace("-", " ").replace("_", " ").title()

    if media_type == "image":
        embed_code = f"![{clean_alt}]({media_url})"

    else:
        mime_type = mimetypes.guess_type(str(target_path))[0] or "video/mp4"

        embed_code = f"""<video class="blog-video" controls preload="metadata">
  <source src="{media_url}" type="{mime_type}">
  Your browser does not support the video tag.
</video>"""

    return jsonify(
        {
            "ok": True,
            "media_type": media_type,
            "filename": target_path.name,
            "url": media_url,
            "embed_code": embed_code,
        }
    )


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


@app.route("/admin/blog/new", methods=["GET", "POST"])
@login_required
def admin_blog_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = slugify(request.form.get("slug", "").strip() or title)
        excerpt = request.form.get("excerpt", "").strip()
        tags = request.form.get("tags", "").strip()
        body = request.form.get("body", "").strip()
        author = request.form.get("author", "JSM Cooperative").strip()

        if not title or not slug or not body:
            flash("Title, slug, and body are required.", "error")
            return redirect(url_for("admin_blog_new"))

        path = BLOG_DIR / f"{slug}.md"

        if path.exists():
            flash("A blog post with that slug already exists.", "error")
            return redirect(url_for("admin_blog_new"))

        content = f"""---
title: {title}
date: {datetime.utcnow().date().isoformat()}
author: {author}
excerpt: {excerpt}
cover: /static/images/jsm-placeholder.svg
tags: {tags}
---

{body}
"""

        path.write_text(content, encoding="utf-8")

        flash("Blog post created.", "success")
        return redirect(url_for("blog_detail", slug=slug))

    return render_template("admin/blog_form.html", title="New Blog Post", post=None)


@app.route("/admin/blog/<slug>/edit", methods=["GET", "POST"])
@login_required
def admin_blog_edit(slug):
    post = get_post(slug)

    if not post:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        excerpt = request.form.get("excerpt", "").strip()
        tags = request.form.get("tags", "").strip()
        body = request.form.get("body", "").strip()
        author = request.form.get("author", "JSM Cooperative").strip()

        content = f"""---
title: {title}
date: {post['date']}
author: {author}
excerpt: {excerpt}
cover: {post['cover']}
tags: {tags}
---

{body}
"""

        post["path"].write_text(content, encoding="utf-8")

        flash("Blog post updated.", "success")
        return redirect(url_for("blog_detail", slug=slug))

    return render_template("admin/blog_form.html", title="Edit Blog Post", post=post)


@app.route("/admin/analytics")
@login_required
def admin_analytics():
    return render_template(
        "admin/analytics.html",
        title="Analytics",
        campaign_notes=[],
        database_disabled=True,
    )


@app.route("/admin/campaign-note", methods=["POST"])
@login_required
def admin_campaign_note():
    flash("Campaign notes are disabled because the site is running without a database.", "info")
    return redirect(url_for("admin_analytics"))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html", title="Page Not Found"), 404


if __name__ == "__main__":
    app.run(debug=True)