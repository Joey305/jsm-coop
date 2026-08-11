import os
import re
import json
import base64
import csv
import io
import uuid
from datetime import datetime, timezone
from datetime import timedelta
from pathlib import Path
from collections import Counter
from functools import wraps
from urllib.parse import urlencode, quote, urlsplit, urlunsplit, parse_qsl
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
    Response,
)
from markupsafe import Markup
import markdown as md
import jsm_analytics as analytics


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BLOG_DIR = BASE_DIR / "blogs"
DEFAULT_SIGNED_BOOK_PAYMENT_LINK = "https://www.paypal.com/ncp/payment/SLQDNTABMS9JS"
THROUGH_THE_LENS_SERIES = "A Coruña Through the Lens"

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
app.config["SITE_NAME"] = os.getenv("SITE_NAME", "JSM Cooperative Corporation")
app.config["SITE_DOMAIN"] = os.getenv("SITE_DOMAIN", "https://jsmcoop.com")
app.config["CONTACT_EMAIL"] = os.getenv("CONTACT_EMAIL", "books@jsmcoop.com")
app.config["PAYPAL_DONATE_BUTTON_ID"] = os.getenv("PAYPAL_DONATE_BUTTON_ID", "TLWCSL2KJDZQU")
app.config["GA_MEASUREMENT_ID"] = os.getenv("GA_MEASUREMENT_ID", "").strip()
app.config["PAYPAL_SIGNED_BOOK_URL"] = os.getenv("PAYPAL_SIGNED_BOOK_URL", DEFAULT_SIGNED_BOOK_PAYMENT_LINK).strip()
app.config["PAYPAL_API_BASE_URL"] = os.getenv("PAYPAL_API_BASE_URL", "https://api-m.paypal.com").rstrip("/")
app.config["PAYPAL_CLIENT_ID"] = os.getenv("PAYPAL_CLIENT_ID", "").strip()
app.config["PAYPAL_CLIENT_SECRET"] = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
app.config["PAYPAL_WEBHOOK_ID"] = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
app.config["BOOK_DIRECT_CHECKOUT_URL"] = os.getenv(
    "BOOK_DIRECT_CHECKOUT_URL",
    app.config["PAYPAL_SIGNED_BOOK_URL"],
).strip()
app.config["BOOK_DIRECT_PROVIDER"] = os.getenv("BOOK_DIRECT_PROVIDER", "PayPal").strip()
app.config["BOOK_DIRECT_PRICE_AMOUNT"] = os.getenv("BOOK_DIRECT_PRICE_AMOUNT", "15.00").strip()
app.config["BOOK_DIRECT_PRICE_CURRENCY"] = os.getenv("BOOK_DIRECT_PRICE_CURRENCY", "USD").strip().upper()
app.config["BLOG_IMAGE_UPLOAD_DIR"] = BASE_DIR / "static" / "images" / "blog"
app.config["BLOG_VIDEO_UPLOAD_DIR"] = BASE_DIR / "static" / "videos" / "blog"
app.config["PAYPAL_WEBHOOK_EVENT_LOG"] = Path(
    os.getenv("PAYPAL_WEBHOOK_EVENT_LOG", BASE_DIR / "data" / "paypal_webhook_events.jsonl")
)
app.config["PAYPAL_VERIFIED_PURCHASE_LOG"] = Path(
    os.getenv("PAYPAL_VERIFIED_PURCHASE_LOG", BASE_DIR / "data" / "paypal_verified_purchases.jsonl")
)
app.config["BOOK_DIRECT_CHECKOUT_ATTRIBUTION_LOG"] = Path(
    os.getenv("BOOK_DIRECT_CHECKOUT_ATTRIBUTION_LOG", BASE_DIR / "data" / "book_checkout_attribution.jsonl")
)
app.config["GOOGLE_ADS_OFFLINE_CONVERSION_LOG"] = Path(
    os.getenv("GOOGLE_ADS_OFFLINE_CONVERSION_LOG", BASE_DIR / "data" / "google_ads_offline_conversions.jsonl")
)
app.config["GOOGLE_ADS_CUSTOMER_ID"] = re.sub(r"\D", "", os.getenv("GOOGLE_ADS_CUSTOMER_ID", ""))
app.config["GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_ID"] = os.getenv(
    "GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_ID", ""
).strip()
app.config["GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_RESOURCE"] = os.getenv(
    "GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_RESOURCE", ""
).strip()
app.config["GOOGLE_ADS_PAYPAL_PURCHASE_CONVERSION_ACTION_ID"] = os.getenv(
    "GOOGLE_ADS_PAYPAL_PURCHASE_CONVERSION_ACTION_ID", ""
).strip()
app.config["GOOGLE_ADS_PAYPAL_PURCHASE_CONVERSION_ACTION_RESOURCE"] = os.getenv(
    "GOOGLE_ADS_PAYPAL_PURCHASE_CONVERSION_ACTION_RESOURCE", ""
).strip()
app.config["ANALYTICS_DB_PATH"] = Path(os.getenv("ANALYTICS_DB_PATH", BASE_DIR / "data" / "jsm_analytics.sqlite3"))
app.config["ANALYTICS_ENABLED"] = os.getenv("ANALYTICS_ENABLED", "1")
app.config["ANALYTICS_ENVIRONMENT"] = os.getenv("ANALYTICS_ENVIRONMENT", os.getenv("FLASK_ENV", "production"))
app.config["ANALYTICS_STORAGE_BACKEND"] = os.getenv("ANALYTICS_STORAGE_BACKEND", "local")
app.config["ANALYTICS_REMOTE_BASE_URL"] = os.getenv("ANALYTICS_REMOTE_BASE_URL", "")
app.config["ANALYTICS_REMOTE_API_TOKEN"] = os.getenv("ANALYTICS_REMOTE_API_TOKEN", "")
app.config["ANALYTICS_REMOTE_TIMEOUT_SECONDS"] = os.getenv("ANALYTICS_REMOTE_TIMEOUT_SECONDS", "10")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}

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
    ("Signed Book", "book_signed"),
    ("Newsletter", "newsletter_page"),
    ("Blogs", "blogs"),
    ("Our Team", "team"),
    ("Chapter Readings", "chapter_readings"),
    ("Donate", "donate"),
    ("Contact", "contact"),
]

BOOK_PRODUCT = {
    "title": "The Man in the Ball Cap",
    "subtitle": "A mystery set in A Coruña, Spain",
    "genre": "Literary mystery",
    "setting": "A Coruña, Spain",
    "author": "JSM Cooperative",
    "description": (
        "A dark mystery set in A Coruña, Spain, where private investigator Pepe Miguel follows "
        "a dangerous case through secrets, occult rituals, and rising danger."
    ),
    "cover": "images/BOOK3D.png",
    "cover_webp": "images/BOOK3D.webp",
    "preview_asin": "B0CPKTVMYX",
    "preview_url": (
        "https://read.amazon.com/kp/card?asin=B0CPKTVMYX&preview=inline&linkCode=kpe&"
        "ref_=cm_sw_r_kb_dp_6ZFC66VA6C4D8CH1W11N"
    ),
}

BOOK_RETAILERS = [
    {
        "key": "barnes_noble",
        "label": "Barnes & Noble",
        "edition": "Paperback edition",
        "retailer": "barnes_noble",
        "book_language": "en",
        "event": "retailer_click_barnes_noble",
        "url": "https://www.barnesandnoble.com/w/the-man-in-the-ballcap-jsm-cooperative/1144453545?ean=9798822929067",
    },
    {
        "key": "amazon_us",
        "label": "Amazon US",
        "edition": "Kindle / English edition",
        "retailer": "amazon_us",
        "book_language": "en",
        "event": "retailer_click_amazon_us",
        "url": "https://www.amazon.com/Man-Ballcap-JSM-Cooperative-ebook/dp/B0CPKTVMYX",
    },
    {
        "key": "amazon_es",
        "label": "Amazon Spain",
        "edition": "Spanish edition",
        "retailer": "amazon_es",
        "book_language": "es",
        "event": "retailer_click_amazon_es",
        "url": "https://www.amazon.es/dp/B0D2MB8JWZ?_encoding=UTF8&psc=1&ref=cm_sw_r_cp_ud_dp_S0G3AYNGCN99JYH66EG9_1&ref_=cm_sw_r_cp_ud_dp_S0G3AYNGCN99JYH66EG9_1&social_share=cm_sw_r_cp_ud_dp_S0G3AYNGCN99JYH66EG9_1",
    },
]

SIGNED_BOOK_IMAGES = {
    "mockup": {
        "src": "images/book-signed/the-man-in-the-ballcap-3d-book-mockup.jpg",
        "webp": "images/book-signed/the-man-in-the-ballcap-3d-book-mockup.webp",
        "alt": "3D mockup of The Man in the Ball Cap signed direct edition",
        "width": 1500,
        "height": 1150,
    },
    "front_cover": {
        "src": "images/book-signed/the-man-in-the-ballcap-front-cover.jpg",
        "webp": "images/book-signed/the-man-in-the-ballcap-front-cover.webp",
        "alt": "Front cover of The Man in the Ball Cap",
        "width": 907,
        "height": 1360,
    },
    "back_cover": {
        "src": "images/book-signed/the-man-in-the-ballcap-back-cover.jpg",
        "webp": "images/book-signed/the-man-in-the-ballcap-back-cover.webp",
        "alt": "Back cover of The Man in the Ball Cap",
        "width": 907,
        "height": 1360,
    },
    "signed_clean": {
        "src": "images/book-signed/the-man-in-the-ballcap-signed-title-page-clean.jpg",
        "webp": "images/book-signed/the-man-in-the-ballcap-signed-title-page-clean.webp",
        "alt": "Signed title page with #JoinTheCamino inscription",
        "width": 1152,
        "height": 1536,
    },
    "signed_author": {
        "src": "images/book-signed/the-man-in-the-ballcap-signed-copy-author-photo.jpg",
        "webp": "images/book-signed/the-man-in-the-ballcap-signed-copy-author-photo.webp",
        "alt": "JSM Cooperative author holding a signed copy of The Man in the Ball Cap",
        "width": 1152,
        "height": 1536,
    },
    "signed_handheld": {
        "src": "images/book-signed/the-man-in-the-ballcap-signed-title-page-handheld.jpg",
        "webp": "images/book-signed/the-man-in-the-ballcap-signed-title-page-handheld.webp",
        "alt": "Handheld signed title page of The Man in the Ball Cap",
        "width": 1152,
        "height": 1536,
    },
}

PAGE_META = {
    "home": {
        "title": "JSM Cooperative Corporation",
        "description": "JSM Cooperative publishes stories, supports mission-aligned nonprofit impact, and invites readers to join creative campaigns that give back.",
    },
    "about": {
        "title": "About JSM Cooperative",
        "description": "Learn how JSM Cooperative uses storytelling, publishing, and community support to advance nonprofit-aligned impact.",
    },
    "book": {
        "title": "The Man in the Ball Cap | Mystery Set in A Coruña, Spain",
        "description": "Read or buy The Man in the Ball Cap, a dark mystery set in A Coruña, Spain, with secrets, occult rituals, and a dangerous case.",
        "image": "images/BOOK3D.png",
    },
    "book_signed": {
        "title": "Signed Copy of The Man in the Ball Cap | Direct From JSM",
        "description": "Order a personally signed physical paperback of The Man in the Ball Cap direct from JSM Cooperative for $15 plus shipping.",
        "image": SIGNED_BOOK_IMAGES["mockup"]["src"],
    },
    "checkout_success": {
        "title": "Thank You for Supporting JSM Cooperative",
        "description": "Thank you for returning from PayPal after ordering The Man in the Ball Cap signed copy.",
        "image": SIGNED_BOOK_IMAGES["signed_clean"]["src"],
    },
    "checkout_cancel": {
        "title": "Checkout Was Not Completed",
        "description": "Return to the signed-copy page, try PayPal checkout again, or read a free preview of The Man in the Ball Cap.",
        "image": SIGNED_BOOK_IMAGES["mockup"]["src"],
    },
    "pillar_article": {
        "title": "Mystery, Memory & Galicia | The World Behind The Man in the Ball Cap",
        "description": "Explore Galicia, A Coruña, mystery fiction, memory, atmosphere, and the world behind The Man in the Ball Cap.",
        "image": SIGNED_BOOK_IMAGES["front_cover"]["src"],
    },
    "blogs": {
        "title": "JSM Cooperative Blog",
        "description": "Read updates from JSM Cooperative about books, nonprofit impact, publishing, and the Camino campaign.",
    },
    "a_coruna_things_to_do": {
        "title": "Things to Do in A Coruña, Spain | JSM Cooperative Corporation",
        "description": "Discover things to do in A Coruña, Galicia, from the Tower of Hercules and Atlantic promenade to beaches, viewpoints, historic streets and stories from the city.",
        "image": "images/Landscape_1.png",
    },
    "a_coruna_literary_walking_tour": {
        "title": "A Coruña Literary Walking Tour | JSM Cooperative Corporation",
        "description": "Explore A Coruña through its streets, coastline, history and stories on a literary walking route inspired by the city and the world behind The Man in the Ball Cap.",
        "image": "images/Landscape_1.png",
    },
    "a_coruna_through_the_lens": {
        "title": "A Coruña Through the Lens | JSM Cooperative Corporation",
        "description": "Explore A Coruña Through the Lens, a collection of photography, places, neighborhoods, coastlines and stories from JSM Cooperative's A Coruña archive.",
        "image": "images/Landscape_1.png",
    },
    "projects": {
        "title": "Community Projects",
        "description": "Explore JSM Cooperative projects connecting creative publishing, education, health, empathy, and community support.",
    },
    "donate": {
        "title": "Donate to JSM Cooperative",
        "description": "Support JSM Cooperative's storytelling, publishing, and nonprofit-aligned work through a secure donation path.",
    },
    "team": {
        "title": "Our Team",
        "description": "Meet the JSM Cooperative team behind the publishing, creative campaigns, and mission-aligned nonprofit work.",
    },
    "chapter_readings": {
        "title": "Chapter Readings",
        "description": "Listen to and explore chapter readings and story updates from The Man in the Ball Cap.",
    },
    "novel_subscription": {
        "title": "Join The Camino Novel Subscription",
        "description": "Join JSM Cooperative's monthly novel subscription campaign supporting books, readers, and nonprofit-aligned impact.",
    },
    "newsletter_page": {
        "title": "JSM Cooperative Newsletter",
        "description": "Join The Camino newsletter for updates on books, blogs, community campaigns, and nonprofit impact.",
    },
    "contact": {
        "title": "Contact JSM Cooperative",
        "description": "Contact JSM Cooperative about books, publishing, donations, partnerships, and community campaigns.",
    },
    "privacy": {
        "title": "Privacy Policy",
        "description": "Read the JSM Cooperative privacy policy for website, newsletter, and contact form information.",
    },
    "terms": {
        "title": "Terms and Disclaimer",
        "description": "Read JSM Cooperative terms, disclaimers, and website use information.",
    },
    "instagram": {
        "title": "JSM Cooperative on Instagram",
        "description": "Find JSM Cooperative's Instagram profile for book updates, creative campaigns, and community impact.",
    },
    "tiktok": {
        "title": "JSM Cooperative on TikTok",
        "description": "Find JSM Cooperative's TikTok profile for book updates, creative campaigns, and community impact.",
    },
    "youtube": {
        "title": "JSM Cooperative on YouTube",
        "description": "Find JSM Cooperative's YouTube channel for chapter readings, videos, and creative campaign updates.",
    },
}

LANDING_PAGES = {
    "mystery_book_spain": {
        "path": "/mystery-book-spain",
        "lang": "en",
        "eyebrow": "Literary Mystery Set In Spain",
        "headline": "A dark mystery set on the Galician coast.",
        "lede": "Private investigator Pepe Miguel follows a dangerous case through A Coruña, where occult rituals, buried secrets, and rising danger point toward a killer who may strike again.",
        "primary_label": "Order the Signed Edition",
        "secondary_label": "Read Free Preview",
        "signed_primary": True,
        "impact": "Your purchase also supports JSM Cooperative's mission-aligned nonprofit work.",
        "story_heading": "Follow the clues through A Coruña.",
        "story_intro": "This page is for readers who want an atmospheric mystery with a real sense of place. The case begins with Pepe Miguel and grows darker as secrets, symbols, and danger gather around the investigation.",
        "audience": [
            "Atmospheric mystery readers",
            "Readers drawn to books set in Spain and Galicia",
            "Readers who like clue-driven suspense with a darker edge",
        ],
        "meta": {
            "title": "Mystery Book Set in Spain | The Man in the Ball Cap",
            "description": "Discover The Man in the Ball Cap, a literary mystery set in A Coruña, Spain, with a free preview and purchase options.",
        },
    },
    "book_that_gives_back": {
        "path": "/book-that-gives-back",
        "lang": "en",
        "eyebrow": "A Novel With Impact",
        "headline": "A signed mystery novel whose purchase supports nonprofit work.",
        "lede": "Order a signed copy of The Man in the Ball Cap and read a dark A Coruña mystery while helping JSM Cooperative fund mission-aligned impact.",
        "primary_label": "Buy Directly from JSM",
        "secondary_label": "Read the Preview",
        "signed_primary": True,
        "impact": "100% of novel profits donated.",
        "story_heading": "A book gift with a story behind it.",
        "story_intro": "The signed direct edition gives readers a physical paperback, a personal inscription, and a clear connection to the cooperative's work.",
        "audience": [
            "Mission-driven gift buyers",
            "Readers who want a suspense novel with a concrete giving connection",
            "Supporters of books, storytelling, and nonprofit impact",
        ],
        "meta": {
            "title": "Book That Gives Back | The Man in the Ball Cap",
            "description": "Buy The Man in the Ball Cap and support JSM Cooperative's mission-aligned nonprofit work through impact-centered publishing.",
        },
    },
    "free_book_preview": {
        "path": "/free-book-preview",
        "lang": "en",
        "eyebrow": "Free Kindle Preview",
        "headline": "Read the opening before deciding.",
        "lede": "Sample The Man in the Ball Cap in your browser and see whether Pepe Miguel's A Coruña case pulls you in.",
        "primary_label": "Start Free Preview",
        "secondary_label": "Order the Signed Copy",
        "signed_after_preview": True,
        "impact": "If the preview pulls you into the story, you can choose the retailer edition or order a signed copy directly from JSM.",
        "story_heading": "Start with the first pages.",
        "story_intro": "No pressure, no guesswork. Read a sample, get a feel for the mystery, and choose your edition only if the case has you turning pages.",
        "preview_first": True,
        "audience": [
            "Readers who want to sample before buying",
            "Mystery fans comparing their next read",
            "Gift buyers checking the tone before ordering",
        ],
        "meta": {
            "title": "Free Book Preview | The Man in the Ball Cap",
            "description": "Read a free Kindle preview of The Man in the Ball Cap, then choose your preferred purchase option.",
        },
    },
    "spanish_ballcap": {
        "path": "/es/el-hombre-de-la-gorra",
        "lang": "es",
        "eyebrow": "Misterio Literario En A Coruña",
        "headline": "Un misterio en A Coruña donde la memoria deja señales.",
        "lede": "El Hombre de la Gorra invita al lector a entrar en una historia de símbolos, sombras y recuerdos en la costa gallega.",
        "primary_label": "Comprar edición española",
        "secondary_label": "Leer muestra gratis",
        "impact": "Tu compra también apoya la misión de JSM Cooperative y su trabajo creativo con impacto social.",
        "audience_heading": "Para lectores que buscan",
        "audience": [
            "Misterios atmosféricos con sentido literario",
            "Historias ambientadas en España y Galicia",
            "Novelas donde el lugar, la memoria y los símbolos importan",
        ],
        "meta": {
            "title": "El Hombre de la Gorra | Misterio literario en A Coruña",
            "description": "Compra o lee una muestra de El Hombre de la Gorra, la edición en español de The Man in the Ball Cap.",
        },
        "primary_retailer": "amazon_es",
    },
}





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


def absolute_url(path):
    if path.startswith("http://") or path.startswith("https://"):
        return path

    root = app.config["SITE_DOMAIN"].rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"

    return f"{root}{path}"


def static_absolute_url(filename):
    return absolute_url(url_for("static", filename=filename))


def get_organization_schema():
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": app.config["SITE_NAME"],
        "url": app.config["SITE_DOMAIN"].rstrip("/"),
        "logo": static_absolute_url("images/Logo.png"),
        "email": app.config["CONTACT_EMAIL"],
        "sameAs": [
            app.config["YOUTUBE_URL"],
            app.config["TIKTOK_URL"],
            app.config["INSTAGRAM_URL"],
        ],
    }


def get_book_schema():
    return {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": BOOK_PRODUCT["title"],
        "author": {
            "@type": "Organization",
            "name": BOOK_PRODUCT["author"],
        },
        "genre": BOOK_PRODUCT["genre"],
        "description": BOOK_PRODUCT["description"],
        "image": static_absolute_url(BOOK_PRODUCT["cover"]),
        "inLanguage": ["en", "es"],
        "offers": [
            {
                "@type": "Offer",
                "url": retailer["url"],
                "availability": "https://schema.org/InStock",
                "seller": {
                    "@type": "Organization",
                    "name": retailer["label"],
                },
            }
            for retailer in BOOK_RETAILERS
        ],
    }


def get_signed_book_offer_schema():
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Signed Copy of The Man in the Ball Cap",
        "description": "A personally signed physical paperback ordered directly from JSM Cooperative.",
        "image": static_absolute_url(SIGNED_BOOK_IMAGES["mockup"]["src"]),
        "brand": {
            "@type": "Organization",
            "name": app.config["SITE_NAME"],
        },
        "offers": {
            "@type": "Offer",
            "url": absolute_url("/book/signed"),
            "price": app.config["BOOK_DIRECT_PRICE_AMOUNT"],
            "priceCurrency": app.config["BOOK_DIRECT_PRICE_CURRENCY"],
            "availability": "https://schema.org/InStock",
            "seller": {
                "@type": "Organization",
                "name": app.config["SITE_NAME"],
            },
        },
    }


def get_article_schema(post, canonical_path):
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["title"],
        "description": post["excerpt"],
        "author": {
            "@type": "Organization",
            "name": post["author"],
        },
        "publisher": {
            "@type": "Organization",
            "name": app.config["SITE_NAME"],
            "logo": {
                "@type": "ImageObject",
                "url": static_absolute_url("images/Logo.png"),
            },
        },
        "datePublished": post["date"],
        "mainEntityOfPage": absolute_url(canonical_path),
        "image": absolute_url(post["cover"]) if post["cover"].startswith("/") else static_absolute_url(post["cover"]),
    }


def get_breadcrumb_schema(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "name": item["name"],
                "item": absolute_url(item["url"]),
            }
            for index, item in enumerate(items)
        ],
    }


def get_webpage_schema(title, description, path):
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": absolute_url(path),
        "isPartOf": {
            "@type": "WebSite",
            "name": app.config["SITE_NAME"],
            "url": app.config["SITE_DOMAIN"].rstrip("/"),
        },
    }


def build_page_meta(endpoint, path=None, overrides=None):
    base = PAGE_META.get(endpoint, {}).copy()
    overrides = overrides or {}
    base.update(overrides)

    if path is None:
        path = request.path

    base.setdefault("title", app.config["SITE_NAME"])
    base.setdefault("description", "Stories that fund a better world through publishing and nonprofit-aligned impact.")
    base.setdefault("canonical_url", absolute_url(path))
    base.setdefault("og_title", base["title"])
    base.setdefault("og_description", base["description"])

    image = base.get("image") or "images/Logo.png"
    base.setdefault("og_image", static_absolute_url(image))

    return base


def render_public_template(template_name, endpoint, **context):
    meta_overrides = context.pop("meta", None)
    context["page_meta"] = build_page_meta(endpoint, overrides=meta_overrides)
    return render_template(template_name, **context)


def campaign_module_html(kind):
    modules = {
        "discover": {
            "kicker": "Discover the Novel",
            "title": "Meet Pepe Miguel in A Coruña.",
            "copy": "Start with the book page for the full mystery hook, free preview, and available editions.",
            "href": url_for("book"),
            "label": "Explore the Book",
            "event": "pillar_to_book_click",
            "style": "article-btn-cyan",
        },
        "preview": {
            "kicker": "Read a Free Preview",
            "title": "Sample the opening before you buy.",
            "copy": "The Kindle preview lets you step into the atmosphere of the story in your browser.",
            "href": f"{url_for('book')}#preview",
            "label": "Read the Preview",
            "event": "pillar_preview_click",
            "style": "article-btn-outline",
        },
        "signed": {
            "kicker": "Signed #JoinTheCamino Edition",
            "title": "Order a signed physical copy direct from JSM.",
            "copy": "$15 + shipping. Direct-order copies are personally signed and include the #JoinTheCamino inscription.",
            "href": url_for("book_signed"),
            "label": "Order the Signed Edition",
            "event": "pillar_signed_copy_click",
            "style": "article-btn-gold",
        },
        "impact": {
            "kicker": "About JSM Cooperative",
            "title": "Stories that fund a better world.",
            "copy": "Learn how JSM Cooperative connects publishing, community, and mission-aligned nonprofit impact.",
            "href": url_for("about"),
            "label": "Learn About JSM",
            "event": "pillar_to_book_click",
            "style": "article-btn-outline",
        },
    }

    module = modules.get(kind)
    if not module:
        return ""

    return f"""
<aside class="article-conversion-card">
  <p class="article-conversion-kicker">{module["kicker"]}</p>
  <h3>{module["title"]}</h3>
  <p>{module["copy"]}</p>
  <a class="article-btn {module["style"]}" href="{module["href"]}" data-analytics-event="{module["event"]}" data-cta-location="pillar_article_{kind}">{module["label"]}</a>
</aside>
"""


def render_campaign_modules(body):
    return re.sub(
        r"\{\{\s*campaign_cta:([a-z_]+)\s*\}\}",
        lambda match: campaign_module_html(match.group(1)),
        body,
    )


def public_sitemap_routes():
    routes = [
        ("home", {}),
        ("about", {}),
        ("book", {}),
        ("blogs", {}),
        ("a_coruna_things_to_do", {}),
        ("a_coruna_literary_walking_tour", {}),
        ("a_coruna_through_the_lens", {}),
        ("projects", {}),
        ("donate", {}),
        ("team", {}),
        ("chapter_readings", {}),
        ("novel_subscription", {}),
        ("newsletter_page", {}),
        ("contact", {}),
        ("privacy", {}),
        ("terms", {}),
        ("instagram", {}),
        ("tiktok", {}),
        ("youtube", {}),
        ("book_signed", {}),
        ("mystery_book_spain", {}),
        ("book_that_gives_back", {}),
        ("free_book_preview", {}),
        ("spanish_ballcap", {}),
    ]

    for post in get_posts():
        endpoint = "blog_article" if post["slug"] == "mystery-memory-galicia-man-in-the-ball-cap" else "blog_detail"
        routes.append((endpoint, {"slug": post["slug"]}))

    return routes


@app.context_processor
def inject_globals():
    return {
        "nav_items": NAV_ITEMS,
        "site_name": app.config["SITE_NAME"],
        "site_domain": app.config["SITE_DOMAIN"],
        "contact_email": app.config["CONTACT_EMAIL"],
        "paypal_donate_button_id": app.config["PAYPAL_DONATE_BUTTON_ID"],
        "ga_measurement_id": app.config["GA_MEASUREMENT_ID"],
        "book_product": BOOK_PRODUCT,
        "book_retailers": BOOK_RETAILERS,
        "direct_checkout_configured": bool(app.config["BOOK_DIRECT_CHECKOUT_URL"]),
        "direct_checkout_provider": app.config["BOOK_DIRECT_PROVIDER"],
        "direct_checkout_price_amount": app.config["BOOK_DIRECT_PRICE_AMOUNT"],
        "direct_checkout_price_currency": app.config["BOOK_DIRECT_PRICE_CURRENCY"],
        "signed_book_images": SIGNED_BOOK_IMAGES,
        "signed_book_price_display": "$15 + shipping",
        "organization_schema": get_organization_schema(),
        "mailchimp_action_url": app.config["MAILCHIMP_ACTION_URL"],
        "mailchimp_honeypot_name": app.config["MAILCHIMP_HONEYPOT_NAME"],
        "admin_csrf_token": admin_csrf_token,
        "analytics_browser_config": {
            "enabled": analytics.analytics_enabled(app.config),
            "endpoint": url_for("collect_analytics_events") if request.endpoint and not request.path.startswith("/admin") else "",
            "environment": analytics.analytics_environment(app.config),
        },
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


def parse_tag_list(tags):
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]

    return [str(t).strip() for t in tags if str(t).strip()]


def infer_blog_series(tags, existing_series=""):
    parsed_tags = parse_tag_list(tags)
    if existing_series == THROUGH_THE_LENS_SERIES or THROUGH_THE_LENS_SERIES in parsed_tags:
        return THROUGH_THE_LENS_SERIES

    return existing_series.strip()




def read_blog_file(path):
    raw = path.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(raw)
    slug = path.stem
    rendered_body = render_campaign_modules(body)
    cover = metadata.get("cover", "/static/images/jsm-placeholder.svg")
    cover_webp = ""

    if cover.startswith("/static/"):
        cover_path = BASE_DIR / cover.removeprefix("/static/")
        webp_path = cover_path.with_suffix(".webp")
        if webp_path.exists():
            cover_webp = f"/static/{webp_path.relative_to(BASE_DIR / 'static')}"

    html = Markup(
        md.markdown(
            rendered_body,
            extensions=["extra", "toc", "tables", "attr_list"],
        )
    )

    tags = parse_tag_list(metadata.get("tags", ""))
    series = infer_blog_series(tags, metadata.get("series", "").strip())
    is_through_lens = series == THROUGH_THE_LENS_SERIES or THROUGH_THE_LENS_SERIES in tags

    generic_tags = {
        "A Coruña",
        "Galicia",
        THROUGH_THE_LENS_SERIES,
        "Travel",
        "City Life",
        "Storytelling",
        "Neighborhoods",
    }
    location = metadata.get("location", "").strip()
    if not location:
        location = next((tag for tag in tags if tag not in generic_tags), "")

    return {
        "slug": slug,
        "title": metadata.get("title", slug.replace("-", " ").title()),
        "date": metadata.get("date", "Undated"),
        "author": metadata.get("author", "JSM Cooperative"),
        "excerpt": metadata.get("excerpt", body[:180].replace("\n", " ") + "..."),
        "cover": cover,
        "cover_webp": cover_webp,
        "tags": tags,
        "series": series,
        "is_through_lens": is_through_lens,
        "location": location,
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


def get_through_the_lens_posts():
    return [post for post in get_posts() if post["is_through_lens"]]


def get_posts_by_slug(slugs):
    wanted = set(slugs)
    return {post["slug"]: post for post in get_posts() if post["slug"] in wanted}


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


def admin_csrf_token():
    token = session.get("admin_csrf_token")
    if not token:
        token = uuid.uuid4().hex
        session["admin_csrf_token"] = token
    return token


def validate_admin_csrf():
    expected = session.get("admin_csrf_token")
    submitted = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not expected or not submitted or submitted != expected:
        abort(400)


def read_jsonl_records(path, limit=None):
    path = Path(path)
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records[-limit:] if limit else records


def parse_record_datetime(record):
    for key in ("received_at", "attempted_at", "event_create_time", "conversion_date_time"):
        value = record.get(key)
        if not value:
            continue
        try:
            if key == "conversion_date_time":
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S%z")
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            continue
    return None


def records_in_range(records, start, end):
    filtered = []
    for record in records:
        dt = parse_record_datetime(record)
        if dt and start <= dt.astimezone(timezone.utc) < end:
            filtered.append(record)
    return filtered


def verified_purchase_summary(config, start, end):
    records = records_in_range(read_jsonl_records(config["PAYPAL_VERIFIED_PURCHASE_LOG"]), start, end)
    deduped = {}
    for record in records:
        key = record.get("resource_id") or record.get("order_id") or record.get("event_id") or record.get("checkout_id")
        if key:
            deduped[key] = record
    purchases = list(deduped.values())
    revenue = 0.0
    attributed = 0
    organic = 0
    google_cpc = 0
    for record in purchases:
        try:
            revenue += float(record.get("value") or 0)
        except (TypeError, ValueError):
            pass
        if any(record.get(key) for key in ("gclid", "gbraid", "wbraid", "utm_source", "utm_medium", "utm_campaign")):
            attributed += 1
        if record.get("gclid") or record.get("gbraid") or record.get("wbraid") or str(record.get("utm_medium", "")).lower() in {"cpc", "ppc", "paid_search"}:
            google_cpc += 1
        elif str(record.get("utm_source", "")).lower() in {"google", "organic"} or str(record.get("utm_medium", "")).lower() == "organic":
            organic += 1
    return {
        "records": purchases,
        "count": len(purchases),
        "revenue": revenue,
        "revenue_label": analytics.money(revenue),
        "average_order_value": analytics.money(revenue / len(purchases)) if purchases else "$0.00",
        "attributed": attributed,
        "organic": organic,
        "google_cpc": google_cpc,
        "unattributed": max(0, len(purchases) - attributed),
    }


def google_ads_upload_summary(config, start, end):
    records = records_in_range(read_jsonl_records(config["GOOGLE_ADS_OFFLINE_CONVERSION_LOG"]), start, end)
    statuses = Counter(record.get("status", "unknown") for record in records)
    rows = [
        {"label": "Attempted", "count": len(records)},
        {"label": "Uploaded", "count": statuses.get("uploaded", 0)},
        {"label": "Partial Failure", "count": statuses.get("partial_failure", 0)},
        {"label": "Failed", "count": statuses.get("failed", 0)},
        {"label": "Skipped", "count": statuses.get("skipped", 0)},
    ]
    return {"rows": rows, "recent": records[-8:], "has_failures": bool(statuses.get("failed") or statuses.get("partial_failure"))}


def paypal_webhook_health(config):
    configured = bool(config.get("PAYPAL_WEBHOOK_ID") and config.get("PAYPAL_CLIENT_ID") and config.get("PAYPAL_CLIENT_SECRET"))
    records = read_jsonl_records(config["PAYPAL_WEBHOOK_EVENT_LOG"], limit=1)
    return {
        "configured": configured,
        "last_event": parse_record_datetime(records[-1]).isoformat(timespec="seconds") if records and parse_record_datetime(records[-1]) else "",
        "event_count": len(read_jsonl_records(config["PAYPAL_WEBHOOK_EVENT_LOG"])),
    }


def dashboard_stat(label, value, summary, key, help_text):
    comparison = summary.get("comparison", {}).get(key, {})
    return {
        "label": label,
        "value": value,
        "previous": summary.get("previous", {}).get(key, 0),
        "change": comparison.get("label", "No previous activity"),
        "direction": comparison.get("direction", "flat"),
        "help": help_text,
    }


def ranked_chart_rows(rows, label_key="label", value_key="count"):
    max_value = max([int(row.get(value_key) or 0) for row in rows] or [1])
    return [
        {
            "label": row.get(label_key) or row.get("page") or row.get("label") or "Untitled",
            "value": int(row.get(value_key) or 0),
            "width": max(4, round((int(row.get(value_key) or 0) / max(max_value, 1)) * 100, 1)),
        }
        for row in rows[:8]
    ]


def donut_chart(rows):
    colors = ["#00eaff", "#4efedc", "#facc15", "#38bdf8", "#22c55e", "#fb7185", "#a78bfa"]
    total = sum(int(row.get("count") or 0) for row in rows)
    if total <= 0:
        return {"segments": [], "gradient": "conic-gradient(rgba(148,163,184,.25) 0 100%)"}
    cursor = 0
    segments = []
    parts = []
    for index, row in enumerate(rows[:7]):
        value = int(row.get("count") or 0)
        if not value:
            continue
        percent = (value / total) * 100
        color = colors[index % len(colors)]
        parts.append(f"{color} {cursor:.2f}% {cursor + percent:.2f}%")
        cursor += percent
        segments.append({"label": row.get("label") or "Unknown", "count": value, "percent": f"{percent:.1f}%", "color": color})
    return {"segments": segments, "gradient": f"conic-gradient({', '.join(parts)})"}


def build_funnel(title, raw_steps, note):
    first = int(raw_steps[0][1] or 0) if raw_steps else 0
    previous = None
    steps = []
    for label, count, availability in raw_steps:
        count = int(count or 0)
        conversion = "Start" if previous is None else analytics.percent_label(analytics.numeric_rate(count, previous))
        steps.append(
            {
                "label": label,
                "count": count,
                "availability": availability,
                "conversion": conversion,
                "overall": analytics.percent_label(analytics.numeric_rate(count, first)) if first else "No starting activity",
                "dropoff": max(0, (previous or count) - count) if previous is not None else 0,
                "width": max(4, round((count / max(first, 1)) * 100, 1)) if count else 4,
            }
        )
        previous = count
    finding = "More activity is needed before this funnel can say anything useful."
    if first and steps[-1]["count"]:
        finding = f"{steps[-1]['label']} reached {steps[-1]['overall']} of the starting audience."
    return {"title": title, "steps": steps, "note": note, "finding": finding}


def dashboard_funnels(summary, verified):
    totals = summary["totals"]
    return {
        "signed_book": build_funnel(
            "Signed book funnel",
            [
                ("Signed-book exposure", totals.get("signed_copy_page_views", 0) + totals.get("signed_promo_impressions", 0), "Trackable interest"),
                ("Signed CTA / promo click", totals.get("signed_cta_clicks", 0) + totals.get("signed_promo_clicks", 0), "Interest only"),
                ("Checkout started", totals.get("direct_checkout_starts", 0), "Entered PayPal flow"),
                ("PayPal return", totals.get("paypal_returns", 0), "Return visit; not proof of payment"),
                ("Verified purchase", verified["count"], "PayPal webhook verified"),
            ],
            "Checkout starts and PayPal returns are intent signals. Only verified webhook purchases count as sales.",
        ),
        "book_discovery": build_funnel(
            "Book discovery funnel",
            [
                ("Book page view", totals.get("book_page_views", 0), "Trackable"),
                ("Preview / modal engagement", totals.get("book_preview_clicks", 0) + totals.get("purchase_modal_opens", 0), "Engagement"),
                ("Purchase option click", totals.get("retailer_clicks", 0) + totals.get("signed_cta_clicks", 0), "Outbound or direct intent"),
                ("Direct checkout started", totals.get("direct_checkout_starts", 0), "Signed-copy checkout only"),
            ],
            "External retailer clicks are outbound interest, not verified purchases.",
        ),
        "a_coruna": build_funnel(
            "A Coruña content journey",
            [
                ("A Coruña content", totals.get("a_coruna_page_views", 0), "Page views"),
                ("Through the Lens article", totals.get("through_lens_views", 0), "Series activity"),
                ("Guide / tour click", totals.get("literary_tour_clicks", 0) + totals.get("through_lens_article_clicks", 0), "Exploration"),
                ("Book click", totals.get("book_clicks_from_coruna", 0), "Book intent"),
                ("Signed-copy click", totals.get("signed_clicks_from_coruna", 0), "Signed-copy intent"),
                ("Checkout", totals.get("direct_checkout_starts", 0), "Entered checkout"),
            ],
            "This shows common movement signals; visitors do not have to follow the exact order.",
        ),
        "newsletter": build_funnel(
            "Newsletter funnel",
            [
                ("Form viewed", totals.get("newsletter_form_views", 0), "Trackable when form view is emitted"),
                ("Signup attempted", totals.get("newsletter_signup_attempts", 0), "Submitted form"),
                ("Successful signup event", totals.get("newsletter_signups", 0), "Only when submission success is known"),
            ],
            "The dashboard does not read Mailchimp subscribers unless a real API integration exists.",
        ),
        "camino": build_funnel(
            "Camino subscription funnel",
            [
                ("Subscription page view", totals.get("camino_page_views", 0), "Trackable"),
                ("Subscription CTA click", totals.get("camino_clicks", 0), "Intent"),
                ("PayPal approval callback", totals.get("camino_completions", 0), "Client approval signal; not ongoing subscription verification"),
            ],
            "Camino completions are PayPal approval callbacks from the current client integration.",
        ),
    }


def growth_scorecard(label, current, previous, explanation, action):
    comparison = analytics.compare_counts(current, previous)
    if int(current or 0) >= 25:
        status = "Strong"
    elif comparison["direction"] == "up":
        status = "Improving"
    elif int(current or 0) > 0:
        status = "Watch"
    else:
        status = "Insufficient data"
    return {
        "label": label,
        "status": status,
        "tone": "good" if status in {"Strong", "Improving"} else "watch" if status == "Watch" else "low",
        "current": current,
        "previous": previous,
        "change": comparison["label"],
        "explanation": explanation,
        "action": action,
    }


def dashboard_growth_goals(config, summary, verified):
    totals = summary["totals"]
    defaults = [
        ("Monthly website sessions", totals.get("anonymous_sessions", 0), int(os.getenv("JSM_GOAL_MONTHLY_SESSIONS", "500")), "sessions", "Audience growth creates more chances for readers to find the book and Camino."),
        ("Newsletter signups", totals.get("newsletter_signups", 0), int(os.getenv("JSM_GOAL_NEWSLETTER_SIGNUPS", "50")), "signups", "Email gives JSM a repeatable relationship with readers."),
        ("Signed checkout starts", totals.get("direct_checkout_starts", 0), int(os.getenv("JSM_GOAL_CHECKOUT_STARTS", "25")), "starts", "Checkout starts show signed-copy buying intent."),
        ("Verified signed-copy sales", verified["count"], int(os.getenv("JSM_GOAL_VERIFIED_SALES", "10")), "sales", "Only verified PayPal webhook records count as direct sales."),
        ("A Coruña guide readers", totals.get("a_coruna_page_views", 0), int(os.getenv("JSM_GOAL_CORUNA_READERS", "300")), "views", "A Coruña content is a major discovery path into the book world."),
        ("Camino subscription approvals", totals.get("camino_completions", 0), int(os.getenv("JSM_GOAL_CAMINO_APPROVALS", "10")), "approvals", "Approvals show subscription-flow completion, pending provider verification."),
    ]
    goals = []
    for label, value, target, unit, why in defaults:
        progress = min(100, round((int(value or 0) / max(target, 1)) * 100))
        goals.append({"label": label, "value": value, "target": target, "unit": unit, "why": why, "progress": progress, "status": "On track" if progress >= 70 else "Building" if value else "No data"})
    return goals


def dashboard_opportunities(summary, verified, google_uploads):
    totals = summary["totals"]
    opportunities = []
    for row in summary.get("top_content", [])[:10]:
        if row["views"] >= 10 and row["book_actions"] == 0:
            opportunities.append({"priority": "High", "confidence": "High" if row["views"] >= 25 else "Medium", "title": f"High traffic / weak book conversion: {row['title']}", "metric": f"{row['views']} views; 0 book actions", "why": "This page is attracting attention without sending readers toward the book.", "action": "Test a stronger contextual book CTA.", "url": url_for("admin_analytics_page_report", page_path=row["page"])})
        if row["views"] >= 10 and row["newsletter_signups"] == 0 and row["purpose"] in {"Editorial", "A Coruña"}:
            opportunities.append({"priority": "Medium", "confidence": "Medium", "title": f"Newsletter opportunity: {row['title']}", "metric": f"{row['views']} views; 0 newsletter signups", "why": "Useful long-form traffic can become repeat readership.", "action": "Test an article-specific Camino newsletter CTA.", "url": url_for("admin_analytics_page_report", page_path=row["page"])})
    if totals.get("direct_checkout_starts", 0) >= 5 and verified["count"] < max(1, totals["direct_checkout_starts"] * 0.25):
        opportunities.append({"priority": "High", "confidence": "Medium", "title": "Signed-copy checkout leakage", "metric": f"{totals['direct_checkout_starts']} checkout starts; {verified['count']} verified purchases", "why": "The dashboard sees checkout intent but few verified sales.", "action": "Inspect PayPal completion, webhook delivery, and mobile checkout friction.", "url": url_for("admin_analytics") + "#books"})
    for row in summary.get("through_lens_content", [])[:5]:
        if row["views"] >= 8 and row["book_actions"] == 0:
            opportunities.append({"priority": "Medium", "confidence": "Medium", "title": f"A Coruña story can work harder: {row['title']}", "metric": f"{row['views']} series views; 0 book actions", "why": "Through the Lens traffic can bridge travel discovery into the book.", "action": "Strengthen the guide, tour, or book card in this article.", "url": url_for("admin_analytics_page_report", page_path=row["page"])})
    if google_uploads["has_failures"]:
        opportunities.append({"priority": "High", "confidence": "High", "title": "Google Ads upload failures", "metric": "Recent partial failures or failed uploads", "why": "Offline conversion health affects ad optimization diagnostics.", "action": "Open the Google Ads conversion log and fix the latest failure reason.", "url": url_for("admin_analytics") + "#campaigns"})
    if not opportunities:
        opportunities.append({"priority": "Low", "confidence": "Low", "title": "Keep building the baseline", "metric": "No urgent opportunity yet", "why": "The dashboard needs more public visitor behavior before ranking opportunities confidently.", "action": "Review after the next campaign, newsletter, or social push.", "url": ""})
    order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(opportunities, key=lambda item: (order.get(item["priority"], 9), item["title"]))[:10]


def dashboard_health_scores(config, storage, verified, google_uploads):
    paypal = paypal_webhook_health(config)
    return [
        {"label": "Analytics Storage", "status": "Healthy" if storage.get("ok") else "Needs Attention", "value": storage.get("backend", "local"), "tone": "good" if storage.get("ok") else "watch", "help": "Durable SQLite event storage."},
        {"label": "First-Party Event Tracking", "status": "Configured" if analytics.analytics_enabled(config) else "Not Configured", "value": f"{storage.get('event_count', 0)} events", "tone": "good" if analytics.analytics_enabled(config) else "low", "help": "Browser events post to the local analytics endpoint."},
        {"label": "PayPal Webhook", "status": "Configured" if paypal["configured"] else "Needs Attention", "value": paypal["last_event"] or "No recent events", "tone": "good" if paypal["configured"] else "watch", "help": "Webhook verifies signed-copy purchases."},
        {"label": "Verified Purchase Tracking", "status": "Active" if verified["count"] else "No Recent Data", "value": f"{verified['count']} purchases", "tone": "good" if verified["count"] else "low", "help": "Only completed PayPal webhook records."},
        {"label": "Google Ads API", "status": "Configured" if os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN") and config.get("GOOGLE_ADS_CUSTOMER_ID") else "Not Configured", "value": "Read panel optional", "tone": "good" if os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN") and config.get("GOOGLE_ADS_CUSTOMER_ID") else "low", "help": "Credential presence only; no secrets shown."},
        {"label": "Google Ads Uploads", "status": "Needs Attention" if google_uploads["has_failures"] else "Operational", "value": f"{sum(row['count'] for row in google_uploads['rows'][1:])} recent records", "tone": "watch" if google_uploads["has_failures"] else "good", "help": "Offline conversion upload attempts."},
        {"label": "Mailchimp", "status": "Configured" if config.get("MAILCHIMP_ACTION_URL") else "Not Configured", "value": "Forward form only", "tone": "good" if config.get("MAILCHIMP_ACTION_URL") else "low", "help": "No subscriber list is shown without API access."},
        {"label": "GA Measurement", "status": "Configured" if config.get("GA_MEASUREMENT_ID") else "Ads tag only", "value": "No secrets exposed", "tone": "good" if config.get("GA_MEASUREMENT_ID") else "watch", "help": "Public Google tag remains separate from first-party analytics."},
        {"label": "Blog Storage", "status": "Healthy" if BLOG_DIR.exists() else "Needs Attention", "value": f"{len(get_posts())} Markdown posts", "tone": "good" if BLOG_DIR.exists() else "watch", "help": "Markdown files remain the source of truth."},
        {"label": "Public Site Health", "status": "Healthy", "value": "Routes render via Flask", "tone": "good", "help": "Basic app health is available at /api/health."},
    ]


def dashboard_report_links(args):
    clean = {key: args.get(key) for key in ("range", "start", "end") if args.get(key)}
    return {
        "print": url_for("admin_analytics_report", **clean),
        "board": url_for("admin_analytics_board_report", **clean),
        "daily": url_for("admin_analytics_named_export", kind="daily", **clean),
        "book": url_for("admin_analytics_named_export", kind="book", **clean),
        "content": url_for("admin_analytics_named_export", kind="content", **clean),
        "coruna": url_for("admin_analytics_named_export", kind="coruna", **clean),
        "campaigns": url_for("admin_analytics_named_export", kind="campaigns", **clean),
        "purchases": url_for("admin_analytics_named_export", kind="purchases", **clean),
        "opportunities": url_for("admin_analytics_named_export", kind="opportunities", **clean),
        "events": url_for("admin_analytics_export", **clean),
    }


def dashboard_campaign_builder(config, args):
    page = args.get("campaign_page", "/book/signed")
    source = args.get("campaign_source", "newsletter")
    medium = args.get("campaign_medium", "email")
    campaign = args.get("campaign_name", "camino_reader_push")
    content = args.get("campaign_content", "signed_copy_cta")
    term = args.get("campaign_term", "")
    return {"page_path": page, "source": source, "medium": medium, "campaign": campaign, "content": content, "term": term, "url": analytics.build_campaign_url(config["SITE_DOMAIN"], page, source, medium, campaign, content, term)}


def dashboard_metric_definitions():
    return [
        "Page View: a first-party public page_view event; admin pages are excluded.",
        "Anonymous Session: a browser session identifier with no name or email attached.",
        "Meaningful Action: a tracked book, newsletter, Camino, donation-intent, checkout, or A Coruña journey action.",
        "Checkout Start: the visitor entered the PayPal signed-copy checkout flow. It is not a sale.",
        "PayPal Return: PayPal sent the visitor back to JSM. It is not proof of payment.",
        "Verified Purchase: a deduplicated completed-payment record from the verified PayPal webhook.",
        "Verified Revenue: gross value from verified signed-copy purchase records only.",
        "Donation Intent: donation buttons or PayPal donation opens. JSM does not currently verify donation revenue here.",
        "Newsletter Signup: counted only when the public implementation reports a successful provider submission.",
        "Camino Completion: current client-side PayPal approval callback, not verified ongoing subscription status.",
    ]


def dashboard_pages_by_purpose(summary):
    buckets = []
    for purpose in ("Discovery", "Book", "Conversion", "A Coruña", "Editorial", "Community", "Support"):
        items = [row for row in summary.get("top_content", []) if row.get("purpose") == purpose]
        buckets.append({"label": purpose, "items": [{"page": row["page"], "title": row["title"], "count": row["views"]} for row in items[:5]]})
    return buckets


def dashboard_csv_export(kind, dashboard):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["JSM Cooperative analytics export"])
    writer.writerow(["Report", kind])
    writer.writerow(["Start", dashboard["start"]])
    writer.writerow(["End", dashboard["end"]])
    writer.writerow([])
    kind = re.sub(r"[^a-z_]", "", kind.lower())
    if kind == "daily":
        writer.writerow(["Date", "Page views", "Sessions", "Book actions", "Checkout starts", "Newsletter signups", "Donation clicks"])
        for row in dashboard["summary"].get("daily_trend", []):
            writer.writerow([row.get("day"), row.get("page_views", 0), row.get("sessions", 0), row.get("book_actions", 0), row.get("checkout_starts", 0), row.get("newsletter_signups", 0), row.get("donation_clicks", 0)])
    elif kind == "book":
        writer.writerow(["Metric", "Value"])
        for key in ("book_page_views", "signed_copy_page_views", "book_preview_clicks", "purchase_modal_opens", "signed_promo_impressions", "signed_promo_clicks", "retailer_clicks", "direct_checkout_starts", "paypal_returns"):
            writer.writerow([key, dashboard["summary"]["totals"].get(key, 0)])
        writer.writerow(["verified_purchases", dashboard["verified_purchases"]["count"]])
        writer.writerow(["verified_revenue", dashboard["verified_purchases"]["revenue_label"]])
    elif kind == "content":
        writer.writerow(["Page", "Title", "Purpose", "Views", "Sessions", "Book actions", "Newsletter signups", "Donation intent", "Meaningful actions"])
        for row in dashboard["summary"].get("top_content", []):
            writer.writerow([row.get("page"), row.get("title"), row.get("purpose"), row.get("views"), row.get("sessions"), row.get("book_actions"), row.get("newsletter_signups"), row.get("donation_clicks"), row.get("meaningful_actions")])
    elif kind == "coruna":
        writer.writerow(["Page", "Title", "Views", "Sessions", "Book actions", "Meaningful actions"])
        for row in dashboard["summary"].get("through_lens_content", []):
            writer.writerow([row.get("page"), row.get("title"), row.get("views"), row.get("sessions"), row.get("book_actions"), row.get("meaningful_actions")])
    elif kind == "campaigns":
        writer.writerow(["Campaign", "Source", "Medium", "Views", "Sessions", "Book actions", "Checkout starts", "Verified purchases", "Newsletter signups", "Camino actions", "Donation intent", "Meaningful actions", "Action rate"])
        for row in dashboard["summary"].get("campaign_performance", []):
            writer.writerow([row.get("label"), row.get("source"), row.get("medium"), row.get("views"), row.get("sessions"), row.get("book_actions"), row.get("checkout_starts"), row.get("verified_purchases"), row.get("newsletter_signups"), row.get("camino_actions"), row.get("donation_intent"), row.get("meaningful_actions"), row.get("action_rate_label")])
    elif kind == "purchases":
        writer.writerow(["Order ID", "Checkout ID", "Event ID", "Value", "Currency", "Attributed", "Click ID type"])
        for row in dashboard["verified_purchases"].get("records", []):
            click_id = next((key for key in ("gclid", "gbraid", "wbraid") if row.get(key)), "")
            writer.writerow([row.get("order_id"), row.get("checkout_id"), row.get("event_id"), row.get("value"), row.get("currency"), "yes" if any(row.get(key) for key in ("utm_source", "utm_campaign", "gclid", "gbraid", "wbraid")) else "no", click_id])
    elif kind == "opportunities":
        writer.writerow(["Priority", "Confidence", "Title", "Metric", "Why", "Recommended action"])
        for row in dashboard["opportunities"]:
            writer.writerow([row.get("priority"), row.get("confidence"), row.get("title"), row.get("metric"), row.get("why"), row.get("action")])
    return output.getvalue()


def build_admin_dashboard(config, args=None):
    args = args or {}
    start, end, range_name = analytics.date_range_from_args(args)
    filters = analytics.filters_from_args(args)
    filters.setdefault("environment", analytics.analytics_environment(config))
    store = analytics.analytics_store(config)
    storage = analytics.storage_health(config)
    try:
        summary = store.query_summary(start, end, filters)
        recent = store.query_events(start, end, filters, page=1, page_size=20)
    except Exception as error:
        summary = analytics.build_empty_summary()
        recent = {"events": [], "total": 0, "page": 1, "pages": 1}
        storage = {**storage, "ok": False, "error": str(error)}
    verified = verified_purchase_summary(config, start, end)
    google_uploads = google_ads_upload_summary(config, start, end)
    totals = summary["totals"]
    opportunities = dashboard_opportunities(summary, verified, google_uploads)
    growth_goals = dashboard_growth_goals(config, summary, verified)
    health_scores = dashboard_health_scores(config, storage, verified, google_uploads)
    insights = [
        f"This period reached {totals.get('anonymous_sessions', 0)} anonymous sessions and {totals.get('page_views', 0)} public page views.",
        f"Book interest produced {totals.get('book_actions', 0)} book actions and {totals.get('direct_checkout_starts', 0)} signed-copy checkout starts.",
        f"Verified signed-copy sales are {verified['count']} with {verified['revenue_label']} verified revenue.",
    ]
    if summary.get("top_pages"):
        top_page = summary["top_pages"][0]
        insights.append(f"Top page: {top_page['label']} with {top_page['count']} views.")
    if opportunities:
        insights.append(f"Top opportunity: {opportunities[0]['title']}.")
    stats = [
        dashboard_stat("Page Views", totals.get("page_views", 0), summary, "page_views", "Public first-party page views."),
        dashboard_stat("Anonymous Sessions", totals.get("anonymous_sessions", 0), summary, "anonymous_sessions", "Anonymous browser sessions, not identified people."),
        dashboard_stat("Meaningful Actions", totals.get("meaningful_actions", 0), summary, "meaningful_actions", "Book, newsletter, Camino, donation-intent, and journey actions."),
        dashboard_stat("Newsletter Signups", totals.get("newsletter_signups", 0), summary, "newsletter_signups", "Successful signup events only."),
        dashboard_stat("Signed Checkout Starts", totals.get("direct_checkout_starts", 0), summary, "direct_checkout_starts", "Entered signed-copy checkout flow."),
        dashboard_stat("Verified Signed-Book Sales", verified["count"], {"previous": {}, "comparison": {}}, "verified", "PayPal webhook verified purchases only."),
        dashboard_stat("Verified Book Revenue", verified["revenue_label"], {"previous": {}, "comparison": {}}, "verified_revenue", "Revenue from verified purchase records only."),
        dashboard_stat("Camino Completions", totals.get("camino_completions", 0), summary, "camino_completions", "PayPal approval callbacks, not ongoing subscription verification."),
    ]
    for event in recent["events"]:
        event["human_label"] = analytics.human_event_label(event["event_name"])
    return {
        "storage_backend": storage.get("backend", "local sqlite"),
        "storage": storage,
        "range_name": range_name,
        "start": start.date().isoformat(),
        "end": (end - timedelta(days=1)).date().isoformat(),
        "filters": filters,
        "summary": summary,
        "verified_purchases": verified,
        "google_uploads": google_uploads,
        "stats": stats,
        "insights": insights,
        "growth_scorecards": [
            growth_scorecard("Audience Growth", totals.get("anonymous_sessions", 0), summary["previous"].get("anonymous_sessions", 0), "Anonymous sessions in this period.", "Share the strongest page through the best current source."),
            growth_scorecard("Book Interest", totals.get("book_actions", 0), summary["previous"].get("book_actions", 0), "Preview, modal, retailer, signed-copy, and book journey actions.", "Promote the page with the strongest book-action rate."),
            growth_scorecard("Signed Copy Conversion", verified["count"], 0, "Verified PayPal sales only.", "Reduce checkout leakage before scaling paid traffic."),
            growth_scorecard("Content Discovery", len(summary.get("top_content", [])), 0, "Pages with measurable activity.", "Strengthen CTAs on high-traffic low-action pages."),
            growth_scorecard("Newsletter Growth", totals.get("newsletter_signups", 0), summary["previous"].get("newsletter_signups", 0), "Successful newsletter signup events.", "Test a clearer Camino promise on editorial pages."),
            growth_scorecard("A Coruña Engagement", totals.get("a_coruna_page_views", 0), summary["previous"].get("a_coruna_page_views", 0), "A Coruña pages and series views.", "Bridge the strongest A Coruña article into the book."),
            growth_scorecard("Camino Interest", totals.get("camino_clicks", 0), summary["previous"].get("camino_clicks", 0), "Subscription CTA clicks.", "Clarify subscription status and next steps near PayPal."),
            growth_scorecard("Campaign Efficiency", sum(row.get("meaningful_actions", 0) for row in summary.get("campaign_performance", [])), 0, "Meaningful actions from tracked campaigns.", "Use campaign links for every newsletter and social push."),
        ],
        "growth_goals": growth_goals,
        "weekly_brief": insights[:4],
        "monthly_brief": insights + [f"Next step: {opportunities[0]['action']}"],
        "recommended_actions": [{"priority": item["priority"], "title": item["title"], "why": item["why"], "next_step": item["action"], "page": ""} for item in opportunities[:4]],
        "growth_experiments": [
            {"status": "Ready", "title": "Signed-copy CTA on A Coruña pages", "why": "A Coruña content can bridge discovery into the novel.", "action": "Test contextual signed-copy copy on top Through the Lens articles.", "measure": "Book actions and checkout starts."},
            {"status": "Ready", "title": "Newsletter promise on long-form posts", "why": "Editorial readers may subscribe before buying.", "action": "Move the Camino signup higher on high-traffic articles.", "measure": "Newsletter signup rate by page."},
            {"status": "Backlog", "title": "Literary tour as middle CTA", "why": "Travel readers may need one more A Coruña step before the book.", "action": "Compare tour CTA versus direct book CTA.", "measure": "Tour clicks, book clicks, and signed-copy starts."},
        ],
        "opportunities": opportunities,
        "anomaly_alerts": [{"title": "No analytics events recorded recently", "detail": "No first-party events exist yet for this date range.", "action": "Visit a public page after deployment or confirm the analytics endpoint.", "tone": "watch"}] if not totals.get("page_views") else ([{"title": "Google Ads upload issue", "detail": "Recent offline conversion uploads failed or partially failed.", "action": "Review the latest upload log entries.", "tone": "watch"}] if google_uploads["has_failures"] else [{"title": "No unusual warnings", "detail": "Nothing crossed the dashboard's lightweight alert thresholds.", "action": "Keep collecting baseline activity.", "tone": "good"}]),
        "health_scores": health_scores,
        "top_paths": [{"path": row["label"], "count": row["count"]} for row in summary.get("top_pages", [])],
        "chart_blocks": {"top_pages": ranked_chart_rows(summary.get("top_pages", [])), "traffic_sources": donut_chart(summary.get("traffic_sources", [])), "devices": donut_chart(summary.get("device_categories", [])), "top_content": ranked_chart_rows(summary.get("top_content", []), "title", "views")},
        "funnels": dashboard_funnels(summary, verified),
        "pages_by_purpose": dashboard_pages_by_purpose(summary),
        "missed_opportunities": [row for row in summary.get("top_content", []) if row["views"] >= 10 and row["meaningful_actions"] == 0][:10],
        "device_insights": [f"{row['label'].title()} represents {row['count']} tracked events." for row in summary.get("device_categories", [])[:3]] or ["Device insights will appear after public activity is recorded."],
        "recent_events": recent["events"],
        "metric_definitions": dashboard_metric_definitions(),
        "report_links": dashboard_report_links(args),
        "campaign_builder": dashboard_campaign_builder(config, args),
        "board_update": [
            {"label": "Audience", "value": totals.get("anonymous_sessions", 0), "note": "Anonymous sessions, not identified people."},
            {"label": "Book engagement", "value": totals.get("book_actions", 0), "note": "Book actions are interest signals."},
            {"label": "Verified direct sales", "value": verified["count"], "note": f"{verified['revenue_label']} verified revenue."},
            {"label": "Newsletter", "value": totals.get("newsletter_signups", 0), "note": "Successful signup events only."},
            {"label": "Camino activity", "value": totals.get("camino_clicks", 0), "note": "CTA clicks and approvals are separate from subscription verification."},
            {"label": "Support intent", "value": totals.get("donation_clicks", 0), "note": "Donation clicks are not verified donations."},
            {"label": "Top opportunity", "value": opportunities[0]["title"], "note": opportunities[0]["action"]},
        ],
        "trend_max": max(1, max([row.get("page_views", 0) + row.get("book_actions", 0) for row in summary.get("daily_trend", [])] or [1])),
        "rates": {
            "newsletter": analytics.click_rate(totals.get("newsletter_signups", 0), totals.get("newsletter_signup_attempts", 0)),
            "donation": analytics.click_rate(totals.get("donation_clicks", 0), totals.get("donation_page_views", 0)),
            "camino": analytics.click_rate(totals.get("camino_completions", 0), totals.get("camino_clicks", 0)),
            "purchase": analytics.click_rate(verified["count"], totals.get("direct_checkout_starts", 0)),
        },
    }


def save_blog_revision(post, actor="admin"):
    if not post or not post.get("path") or not Path(post["path"]).exists():
        return None
    revision_dir = BASE_DIR / "data" / "blog_revisions" / post["slug"]
    revision_dir.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now().strftime("%Y%m%d%H%M%S")
    target = revision_dir / f"{timestamp}.md"
    target.write_text(Path(post["path"]).read_text(encoding="utf-8"), encoding="utf-8")
    metadata = revision_dir / f"{timestamp}.json"
    metadata.write_text(json.dumps({"created_at": utc_now().isoformat(timespec="seconds"), "actor": actor}, sort_keys=True), encoding="utf-8")
    return target


def blog_revisions(slug):
    revision_dir = BASE_DIR / "data" / "blog_revisions" / slug
    if not revision_dir.exists():
        return []
    revisions = []
    for path in sorted(revision_dir.glob("*.md"), reverse=True):
        metadata_path = path.with_suffix(".json")
        metadata = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {}
        revisions.append({"id": path.stem, "path": path, "created_at": metadata.get("created_at", path.stem), "actor": metadata.get("actor", "admin")})
    return revisions


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
    return render_public_template("index.html", "home", title="Home", posts=posts)


@app.route("/about")
def about():
    return render_public_template("about.html", "about", title="About")


@app.route("/book")
def book():
    page_meta = {
        "hreflang": {
            "en": absolute_url("/book"),
            "es": absolute_url("/es/el-hombre-de-la-gorra"),
        },
    }
    schemas = [
        get_book_schema(),
        get_breadcrumb_schema(
            [
                {"name": "Home", "url": "/"},
                {"name": BOOK_PRODUCT["title"], "url": "/book"},
            ]
        ),
    ]
    return render_public_template(
        "book.html",
        "book",
        title=BOOK_PRODUCT["title"],
        meta=page_meta,
        structured_data=schemas,
    )


@app.route("/blogs")
def blogs():
    posts = get_posts()
    return render_public_template("blogs.html", "blogs", title="Blogs", posts=posts)


@app.route("/a-coruna/things-to-do")
def a_coruna_things_to_do():
    featured_posts = get_posts_by_slug(
        [
            "a-coruna-through-the-lens-tower-of-hercules",
            "a-coruna-through-the-lens-paseo-maritimo",
            "a-coruna-through-the-lens-maria-pita",
            "a-coruna-through-the-lens-ciudad-vieja",
            "a-coruna-through-the-lens-riazor",
            "a-coruna-through-the-lens-orzan",
            "a-coruna-through-the-lens-monte-de-san-pedro",
            "a-coruna-through-the-lens-after-dark",
            "a-coruna-through-the-lens-before-the-city-wakes",
            "a-coruna-through-the-lens-plaza-de-lugo-market-streets",
            "a-rainy-day-in-a-coruna-through-the-lens",
        ]
    )
    meta = {
        "canonical_url": absolute_url("/a-coruna/things-to-do"),
        "og_type": "website",
    }
    schemas = [
        get_webpage_schema(
            PAGE_META["a_coruna_things_to_do"]["title"],
            PAGE_META["a_coruna_things_to_do"]["description"],
            "/a-coruna/things-to-do",
        ),
        get_breadcrumb_schema(
            [
                {"name": "Home", "url": "/"},
                {"name": "Things to Do in A Coruña", "url": "/a-coruna/things-to-do"},
            ]
        ),
    ]
    return render_public_template(
        "a_coruna_things_to_do.html",
        "a_coruna_things_to_do",
        title="Things to Do in A Coruña",
        posts_by_slug=featured_posts,
        meta=meta,
        structured_data=schemas,
    )


@app.route("/a-coruna/literary-walking-tour")
def a_coruna_literary_walking_tour():
    route_posts = get_posts_by_slug(
        [
            "a-coruna-through-the-lens-maria-pita",
            "a-coruna-through-the-lens-ciudad-vieja",
            "a-coruna-through-the-lens-marina-glass-galleries",
            "a-coruna-through-the-lens-orzan",
            "a-coruna-through-the-lens-riazor",
            "a-coruna-through-the-lens-paseo-maritimo",
            "a-coruna-through-the-lens-tower-of-hercules",
        ]
    )
    meta = {
        "canonical_url": absolute_url("/a-coruna/literary-walking-tour"),
        "og_type": "website",
    }
    schemas = [
        get_webpage_schema(
            PAGE_META["a_coruna_literary_walking_tour"]["title"],
            PAGE_META["a_coruna_literary_walking_tour"]["description"],
            "/a-coruna/literary-walking-tour",
        ),
        get_breadcrumb_schema(
            [
                {"name": "Home", "url": "/"},
                {"name": "A Coruña Literary Walking Tour", "url": "/a-coruna/literary-walking-tour"},
            ]
        ),
    ]
    return render_public_template(
        "a_coruna_literary_walking_tour.html",
        "a_coruna_literary_walking_tour",
        title="A Coruña Literary Walking Tour",
        posts_by_slug=route_posts,
        meta=meta,
        structured_data=schemas,
    )


@app.route("/a-coruna/through-the-lens")
def a_coruna_through_the_lens():
    posts = get_through_the_lens_posts()
    meta = {
        "canonical_url": absolute_url("/a-coruna/through-the-lens"),
        "og_type": "website",
    }
    schemas = [
        get_webpage_schema(
            PAGE_META["a_coruna_through_the_lens"]["title"],
            PAGE_META["a_coruna_through_the_lens"]["description"],
            "/a-coruna/through-the-lens",
        ),
        get_breadcrumb_schema(
            [
                {"name": "Home", "url": "/"},
                {"name": THROUGH_THE_LENS_SERIES, "url": "/a-coruna/through-the-lens"},
            ]
        ),
    ]
    return render_public_template(
        "a_coruna_through_the_lens.html",
        "a_coruna_through_the_lens",
        title=THROUGH_THE_LENS_SERIES,
        posts=posts,
        meta=meta,
        structured_data=schemas,
    )


@app.route("/blogs/<slug>")
def blog_detail(slug):
    return render_blog_post(slug, canonical_prefix="/blogs")


@app.route("/blog/<slug>")
def blog_article(slug):
    return render_blog_post(slug, canonical_prefix="/blog")


def render_blog_post(slug, canonical_prefix="/blogs"):
    post = get_post(slug)

    if not post:
        abort(404)

    canonical_path = f"{canonical_prefix}/{post['slug']}"
    meta = {
        "title": post["title"],
        "description": post["excerpt"],
        "canonical_url": absolute_url(canonical_path),
        "image": post["cover"].replace("/static/", "") if post["cover"].startswith("/static/") else "images/jsm-placeholder.svg",
    }
    schemas = [
        get_article_schema(post, canonical_path),
        get_breadcrumb_schema(
            [
                {"name": "Home", "url": "/"},
                {"name": "Blogs", "url": "/blogs"},
                {"name": post["title"], "url": canonical_path},
            ]
        )
    ]
    return render_public_template(
        "blog_detail.html",
        "blogs",
        title=post["title"],
        post=post,
        meta=meta,
        structured_data=schemas,
    )


@app.route("/projects")
def projects():
    return render_public_template("projects.html", "projects", title="Community Projects")


@app.route("/donate")
def donate():
    return render_public_template("donate.html", "donate", title="Donate")


@app.route("/team")
def team():
    return render_public_template("team.html", "team", title="Our Team")


@app.route("/chapter-readings")
def chapter_readings():
    return render_public_template("chapter_readings.html", "chapter_readings", title="Chapter Readings")


@app.route("/novel-subscription")
def novel_subscription():
    return render_public_template("novel_subscription.html", "novel_subscription", title="Novel Subscription")


@app.route("/instagram")
def instagram():
    return render_public_template("social.html", "instagram", title="Instagram", platform="Instagram")


@app.route("/tiktok")
def tiktok():
    return render_public_template("social.html", "tiktok", title="TikTok", platform="TikTok")


@app.route("/youtube")
def youtube():
    return render_public_template("social.html", "youtube", title="YouTube", platform="YouTube")


@app.route("/contactus")
def contactus_alias():
    return redirect(url_for("contact"), code=301)


@app.route("/ns")
def novel_fundraiser_shortlink():
    return redirect(url_for("novel_subscription"), code=302)


@app.route("/privacy")
def privacy():
    return render_public_template("privacy.html", "privacy", title="Privacy Policy")


@app.route("/terms")
def terms():
    return render_public_template("terms.html", "terms", title="Terms / Disclaimer")


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

    return render_public_template("contact.html", "contact", title="Contact")


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

    return render_public_template("newsletter.html", "newsletter_page", title="Newsletter")


@app.route("/book/signed")
def book_signed():
    meta = {
        "canonical_url": absolute_url("/book/signed"),
        "image": SIGNED_BOOK_IMAGES["mockup"]["src"],
    }
    schemas = [
        get_book_schema(),
        get_signed_book_offer_schema(),
        get_breadcrumb_schema(
            [
                {"name": "Home", "url": "/"},
                {"name": BOOK_PRODUCT["title"], "url": "/book"},
                {"name": "Signed Copy", "url": "/book/signed"},
            ]
        ),
    ]
    return render_public_template(
        "book_signed.html",
        "book_signed",
        title="Signed Copy",
        meta=meta,
        structured_data=schemas,
    )


@app.route("/signed-copy")
def signed_copy_alias():
    return redirect(url_for("book_signed"), code=301)


def render_landing_page(key):
    landing = LANDING_PAGES[key]
    path = landing["path"]
    meta = landing["meta"].copy()
    meta.update(
        {
            "canonical_url": absolute_url(path),
            "image": BOOK_PRODUCT["cover"],
            "lang": landing["lang"],
            "hreflang": {
                "en": absolute_url("/book"),
                "es": absolute_url("/es/el-hombre-de-la-gorra"),
            },
        }
    )
    schemas = [
        get_book_schema(),
        get_breadcrumb_schema(
            [
                {"name": "Home", "url": "/"},
                {"name": BOOK_PRODUCT["title"], "url": "/book"},
                {"name": landing["meta"]["title"].split("|")[0].strip(), "url": path},
            ]
        ),
    ]
    primary_retailer_key = landing.get("primary_retailer", "amazon_us")
    primary_retailer = next(
        (retailer for retailer in BOOK_RETAILERS if retailer["key"] == primary_retailer_key),
        BOOK_RETAILERS[1],
    )
    return render_template(
        "book_landing.html",
        title=landing["meta"]["title"].split("|")[0].strip(),
        page_meta=build_page_meta(key, path=path, overrides=meta),
        structured_data=schemas,
        landing=landing,
        primary_retailer=primary_retailer,
        page_lang=landing["lang"],
        reduced_nav=True,
    )


@app.route("/mystery-book-spain")
def mystery_book_spain():
    return render_landing_page("mystery_book_spain")


@app.route("/book-that-gives-back")
def book_that_gives_back():
    return render_landing_page("book_that_gives_back")


@app.route("/free-book-preview")
def free_book_preview():
    return render_landing_page("free_book_preview")


@app.route("/es/el-hombre-de-la-gorra")
def spanish_ballcap():
    return render_landing_page("spanish_ballcap")


def append_jsonl(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def utc_now():
    return datetime.now(timezone.utc)


def google_ads_conversion_time(dt):
    timestamp = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
    return f"{timestamp[:-2]}:{timestamp[-2:]}"


def read_latest_checkout_attribution(checkout_id):
    if not checkout_id:
        return None

    path = Path(app.config["BOOK_DIRECT_CHECKOUT_ATTRIBUTION_LOG"])
    if not path.exists():
        return None

    found = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("checkout_id") == checkout_id:
                found = record
    return found


def google_ads_conversion_action_resource(event_name):
    customer_id = app.config["GOOGLE_ADS_CUSTOMER_ID"]
    if event_name == "paypal_checkout_started":
        resource = app.config["GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_RESOURCE"]
        action_id = app.config["GOOGLE_ADS_PAYPAL_CHECKOUT_STARTED_CONVERSION_ACTION_ID"]
    elif event_name == "paypal_payment_completed":
        resource = app.config["GOOGLE_ADS_PAYPAL_PURCHASE_CONVERSION_ACTION_RESOURCE"]
        action_id = app.config["GOOGLE_ADS_PAYPAL_PURCHASE_CONVERSION_ACTION_ID"]
    else:
        return ""

    if resource:
        return resource
    if customer_id and action_id:
        return f"customers/{customer_id}/conversionActions/{action_id}"
    return ""


def google_ads_click_id(record):
    for field in ("gclid", "gbraid", "wbraid"):
        value = (record.get(field) or "").strip()
        if value:
            return field, value
    return "", ""


def load_google_ads_client_from_env():
    required = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip(),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", "").strip(),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "").strip(),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing Google Ads API config: {', '.join(missing)}")

    config = {**required, "use_proto_plus": True}
    login_customer_id = re.sub(r"\D", "", os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""))
    if login_customer_id:
        config["login_customer_id"] = login_customer_id

    from google.ads.googleads.client import GoogleAdsClient

    return GoogleAdsClient.load_from_dict(config)


def upload_google_ads_click_conversion(event_name, record):
    click_field, click_value = google_ads_click_id(record)
    customer_id = app.config["GOOGLE_ADS_CUSTOMER_ID"]
    conversion_action = google_ads_conversion_action_resource(event_name)

    upload_record = {
        "attempted_at": utc_now().isoformat(timespec="seconds").replace("+00:00", "Z"),
        "event_name": event_name,
        "checkout_id": record.get("checkout_id", ""),
        "order_id": record.get("order_id", record.get("checkout_id", "")),
        "click_id_type": click_field,
        "conversion_action": conversion_action,
        "status": "skipped",
    }

    if not customer_id or not conversion_action or not click_field:
        upload_record["reason"] = "missing_google_ads_config_or_click_id"
        append_jsonl(app.config["GOOGLE_ADS_OFFLINE_CONVERSION_LOG"], upload_record)
        return upload_record

    try:
        client = load_google_ads_client_from_env()
        conversion_upload_service = client.get_service("ConversionUploadService")
        click_conversion = client.get_type("ClickConversion")
        setattr(click_conversion, click_field, click_value)
        click_conversion.conversion_action = conversion_action
        click_conversion.conversion_date_time = record["conversion_date_time"]
        click_conversion.conversion_value = float(record.get("value") or 0)
        click_conversion.currency_code = record.get("currency") or app.config["BOOK_DIRECT_PRICE_CURRENCY"]
        if upload_record["order_id"]:
            click_conversion.order_id = upload_record["order_id"]

        request_obj = client.get_type("UploadClickConversionsRequest")
        request_obj.customer_id = customer_id
        request_obj.conversions.append(click_conversion)
        request_obj.partial_failure = True
        response = conversion_upload_service.upload_click_conversions(request=request_obj)

        upload_record["status"] = "uploaded"
        upload_record["job_id"] = str(response.job_id)
        if response.partial_failure_error and response.partial_failure_error.message:
            upload_record["status"] = "partial_failure"
            upload_record["reason"] = response.partial_failure_error.message
    except Exception as error:
        upload_record["status"] = "failed"
        upload_record["reason"] = f"{type(error).__name__}: {error}"

    append_jsonl(app.config["GOOGLE_ADS_OFFLINE_CONVERSION_LOG"], upload_record)
    return upload_record


def paypal_access_token():
    client_id = app.config["PAYPAL_CLIENT_ID"]
    client_secret = app.config["PAYPAL_CLIENT_SECRET"]
    if not client_id or not client_secret:
        raise RuntimeError("PayPal API credentials are not configured.")

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    request_body = urlencode({"grant_type": "client_credentials"}).encode("utf-8")
    token_request = Request(
        f"{app.config['PAYPAL_API_BASE_URL']}/v1/oauth2/token",
        data=request_body,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    with urlopen(token_request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))

    token = payload.get("access_token")
    if not token:
        raise RuntimeError("PayPal did not return an access token.")
    return token


def verify_paypal_webhook_signature(event_payload):
    webhook_id = app.config["PAYPAL_WEBHOOK_ID"]
    if not webhook_id:
        return False, "missing_webhook_id"

    verification_payload = {
        "auth_algo": request.headers.get("PAYPAL-AUTH-ALGO", ""),
        "cert_url": request.headers.get("PAYPAL-CERT-URL", ""),
        "transmission_id": request.headers.get("PAYPAL-TRANSMISSION-ID", ""),
        "transmission_sig": request.headers.get("PAYPAL-TRANSMISSION-SIG", ""),
        "transmission_time": request.headers.get("PAYPAL-TRANSMISSION-TIME", ""),
        "webhook_id": webhook_id,
        "webhook_event": event_payload,
    }

    token = paypal_access_token()
    verify_request = Request(
        f"{app.config['PAYPAL_API_BASE_URL']}/v1/notifications/verify-webhook-signature",
        data=json.dumps(verification_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(verify_request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))

    status = payload.get("verification_status", "")
    return status == "SUCCESS", status or "unknown"


def extract_paypal_payment_record(event_payload, verified):
    resource = event_payload.get("resource") or {}
    amount = resource.get("amount") or resource.get("seller_receivable_breakdown", {}).get("gross_amount") or {}

    return {
        "received_at": utc_now().isoformat(timespec="seconds").replace("+00:00", "Z"),
        "verified": verified,
        "event_id": event_payload.get("id", ""),
        "event_type": event_payload.get("event_type", ""),
        "event_create_time": event_payload.get("create_time", ""),
        "resource_id": resource.get("id", ""),
        "resource_status": resource.get("status", ""),
        "invoice_id": resource.get("invoice_id", ""),
        "custom_id": resource.get("custom_id", ""),
        "currency": amount.get("currency_code", app.config["BOOK_DIRECT_PRICE_CURRENCY"]),
        "value": amount.get("value", app.config["BOOK_DIRECT_PRICE_AMOUNT"]),
    }


@app.route("/paypal/webhook", methods=["POST"])
def paypal_webhook():
    event_payload = request.get_json(silent=True)
    if not isinstance(event_payload, dict):
        return jsonify({"status": "ignored", "reason": "invalid_json"}), 400

    verified = False
    verification_status = "not_checked"
    try:
        verified, verification_status = verify_paypal_webhook_signature(event_payload)
    except (RuntimeError, HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        verification_status = f"verification_error:{type(error).__name__}"

    record = extract_paypal_payment_record(event_payload, verified)
    record["verification_status"] = verification_status
    append_jsonl(app.config["PAYPAL_WEBHOOK_EVENT_LOG"], record)

    if verified and event_payload.get("event_type") == "PAYMENT.CAPTURE.COMPLETED":
        checkout_id = record.get("custom_id") or record.get("invoice_id") or ""
        checkout_record = read_latest_checkout_attribution(checkout_id)
        purchase_record = {
            **(checkout_record or {}),
            **record,
            "checkout_id": checkout_id,
            "order_id": record.get("resource_id") or record.get("event_id") or checkout_id,
            "event_name": "paypal_payment_completed",
            "conversion_date_time": google_ads_conversion_time(utc_now()),
        }
        append_jsonl(app.config["PAYPAL_VERIFIED_PURCHASE_LOG"], purchase_record)
        try:
            analytics.analytics_store(app.config).store_event(
                {
                    "event_id": f"paypal:{purchase_record.get('order_id') or purchase_record.get('event_id') or uuid.uuid4().hex}",
                    "schema_version": 1,
                    "event_name": "verified_direct_purchase_completed",
                    "event_category": "sales",
                    "occurred_at": utc_now().isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "client_occurred_at": "",
                    "page_path": purchase_record.get("page_path", ""),
                    "page_title": "Verified signed-copy purchase",
                    "landing_page": purchase_record.get("landing_page", ""),
                    "content_id": "",
                    "content_type": "book",
                    "article_slug": "",
                    "series": "",
                    "element_id": "",
                    "element_label": "PayPal webhook",
                    "element_type": "server",
                    "element_position": "paypal_webhook",
                    "destination_url": "",
                    "destination_domain": "",
                    "referrer_url": "",
                    "referrer_domain": "",
                    "source": purchase_record.get("utm_source", ""),
                    "medium": purchase_record.get("utm_medium", ""),
                    "campaign": purchase_record.get("utm_campaign", ""),
                    "term": purchase_record.get("utm_term", ""),
                    "campaign_content": purchase_record.get("utm_content", ""),
                    "gclid": purchase_record.get("gclid", ""),
                    "gbraid": purchase_record.get("gbraid", ""),
                    "wbraid": purchase_record.get("wbraid", ""),
                    "anonymous_session_id": "",
                    "device_category": "",
                    "environment": analytics.analytics_environment(app.config),
                    "metadata": {
                        "checkout_id": purchase_record.get("checkout_id", ""),
                        "order_id": purchase_record.get("order_id", ""),
                        "value": purchase_record.get("value", ""),
                        "currency": purchase_record.get("currency", ""),
                    },
                }
            )
        except Exception:
            pass
        upload_google_ads_click_conversion("paypal_payment_completed", purchase_record)

    return jsonify({"status": "received", "verified": verified}), 200


@app.route("/book/checkout/start")
def direct_book_checkout():
    checkout_url = app.config["BOOK_DIRECT_CHECKOUT_URL"]

    if not checkout_url:
        flash("Direct book checkout is not configured yet. Please choose a retailer option.", "info")
        return redirect(url_for("book_signed"))

    checkout_id = uuid.uuid4().hex
    conversion_time = google_ads_conversion_time(utc_now())
    attribution = {
        key: request.args.get(key)
        for key in ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "gbraid", "wbraid"]
        if request.args.get(key)
    }
    checkout_record = {
        "checkout_id": checkout_id,
        "order_id": f"paypal-checkout-{checkout_id}",
        "event_name": "paypal_checkout_started",
        "conversion_date_time": conversion_time,
        "value": app.config["BOOK_DIRECT_PRICE_AMOUNT"],
        "currency": app.config["BOOK_DIRECT_PRICE_CURRENCY"],
        "page_path": request.referrer or "",
        **attribution,
    }
    append_jsonl(app.config["BOOK_DIRECT_CHECKOUT_ATTRIBUTION_LOG"], checkout_record)
    upload_google_ads_click_conversion("paypal_checkout_started", checkout_record)

    parsed = urlsplit(checkout_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(attribution)
    query.update(
        {
            "custom": checkout_id,
            "custom_id": checkout_id,
            "invoice": checkout_id,
            "invoice_id": checkout_id,
        }
    )
    checkout_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )

    return redirect(checkout_url, code=302)


@app.route("/book/checkout/success")
@app.route("/book/signed/thank-you")
def direct_book_checkout_success():
    meta = {
        "title": "Thank You for Returning from PayPal",
        "description": "Thank you for returning from PayPal after ordering The Man in the Ball Cap signed copy.",
    }
    return render_public_template(
        "checkout_success.html",
        "checkout_success",
        title="Thank You",
        meta=meta,
    )


@app.route("/book/checkout/cancel")
def direct_book_checkout_cancel():
    meta = {
        "title": "Your Checkout Was Not Completed",
        "description": "Return to the signed-copy page, try PayPal checkout again, or read a free preview.",
        "canonical_url": absolute_url("/book/checkout/cancel"),
        "image": SIGNED_BOOK_IMAGES["mockup"]["src"],
    }
    return render_public_template(
        "checkout_cancel.html",
        "checkout_cancel",
        title="Checkout Not Completed",
        meta=meta,
    )


@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /admin/",
        "Disallow: /api/",
        f"Sitemap: {absolute_url('/sitemap.xml')}",
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    entries = []

    for endpoint, values in public_sitemap_routes():
        entries.append(
            {
                "loc": absolute_url(url_for(endpoint, **values)),
                "lastmod": datetime.utcnow().date().isoformat(),
            }
        )

    xml = render_template("sitemap.xml", entries=entries)
    return Response(xml, mimetype="application/xml")


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
        try:
            analytics.analytics_store(app.config).store_event(
                {
                    "event_id": f"server:newsletter:{uuid.uuid4().hex}",
                    "schema_version": 1,
                    "event_name": "newsletter_signup",
                    "event_category": "newsletter",
                    "occurred_at": utc_now().isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "client_occurred_at": "",
                    "page_path": "/newsletter",
                    "page_title": "Newsletter",
                    "landing_page": "/newsletter",
                    "content_id": "",
                    "content_type": "",
                    "article_slug": "",
                    "series": "",
                    "element_id": "",
                    "element_label": "Mailchimp signup",
                    "element_type": "server",
                    "element_position": "api_newsletter",
                    "destination_url": "",
                    "destination_domain": "",
                    "referrer_url": "",
                    "referrer_domain": "",
                    "source": "",
                    "medium": "",
                    "campaign": "",
                    "term": "",
                    "campaign_content": "",
                    "gclid": "",
                    "gbraid": "",
                    "wbraid": "",
                    "anonymous_session_id": "",
                    "device_category": "",
                    "environment": analytics.analytics_environment(app.config),
                    "metadata": {"status": "mailchimp_submitted"},
                }
            )
        except Exception:
            pass
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
    dashboard = build_admin_dashboard(app.config, request.args)
    return render_template("admin/dashboard.html", title="Command Center", dashboard=dashboard, admin_user=os.getenv("ADMIN_USERNAME", "admin"))


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
    validate_admin_csrf()
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
        validate_admin_csrf()
        title = request.form.get("title", "").strip()
        slug = slugify(request.form.get("slug", "").strip() or title)
        excerpt = request.form.get("excerpt", "").strip()
        tags = request.form.get("tags", "").strip()
        body = request.form.get("body", "").strip()
        author = request.form.get("author", "JSM Cooperative").strip()
        series = request.form.get("series", "").strip() or infer_blog_series(tags)
        series_line = f"series: {series}\n" if series else ""

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
{series_line}---

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
        validate_admin_csrf()
        title = request.form.get("title", "").strip()
        excerpt = request.form.get("excerpt", "").strip()
        tags = request.form.get("tags", "").strip()
        body = request.form.get("body", "").strip()
        author = request.form.get("author", "JSM Cooperative").strip()
        series = request.form.get("series", "").strip() or infer_blog_series(tags, post.get("series", ""))
        series_line = f"series: {series}\n" if series else ""

        content = f"""---
title: {title}
date: {post['date']}
author: {author}
excerpt: {excerpt}
cover: {post['cover']}
tags: {tags}
{series_line}---

{body}
"""

        save_blog_revision(post, actor=os.getenv("ADMIN_USERNAME", "admin"))
        post["path"].write_text(content, encoding="utf-8")

        flash("Blog post updated.", "success")
        return redirect(url_for("blog_detail", slug=slug))

    return render_template("admin/blog_form.html", title="Edit Blog Post", post=post)


@app.route("/admin/analytics")
@login_required
def admin_analytics():
    dashboard = build_admin_dashboard(app.config, request.args)
    return render_template("admin/dashboard.html", title="Analytics", dashboard=dashboard, admin_user=os.getenv("ADMIN_USERNAME", "admin"), analytics_page=True)


@app.route("/admin/analytics/events")
@login_required
def admin_analytics_events():
    start, end, range_name = analytics.date_range_from_args(request.args)
    filters = analytics.filters_from_args(request.args)
    result = analytics.analytics_store(app.config).query_events(start, end, filters, page=request.args.get("page", 1), page_size=50)
    return render_template(
        "admin/analytics_events.html",
        title="Event Explorer",
        result=result,
        filters=filters,
        range_name=range_name,
        start=start.date().isoformat(),
        end=(end - timedelta(days=1)).date().isoformat(),
        storage=analytics.storage_health(app.config),
    )


@app.route("/admin/analytics/export.csv")
@login_required
def admin_analytics_export():
    start, end, _range_name = analytics.date_range_from_args(request.args)
    filters = analytics.filters_from_args(request.args)
    body = analytics.analytics_store(app.config).export_events(start, end, filters)
    filename = f"jsm-analytics-events-{start.date()}-to-{(end - timedelta(days=1)).date()}.csv"
    return body, {"Content-Type": "text/csv; charset=utf-8", "Content-Disposition": f"attachment; filename={filename}"}


@app.route("/admin/analytics/export/<kind>.csv")
@login_required
def admin_analytics_named_export(kind):
    dashboard = build_admin_dashboard(app.config, request.args)
    body = dashboard_csv_export(kind, dashboard)
    filename = f"jsm-{re.sub(r'[^a-z0-9-]', '-', kind.lower())}-{dashboard['start']}-to-{dashboard['end']}.csv"
    return body, {"Content-Type": "text/csv; charset=utf-8", "Content-Disposition": f"attachment; filename={filename}"}


@app.route("/admin/analytics/report")
@login_required
def admin_analytics_report():
    dashboard = build_admin_dashboard(app.config, request.args)
    return render_template("admin/analytics_report.html", title="Printable Report", dashboard=dashboard, admin_user=os.getenv("ADMIN_USERNAME", "admin"))


@app.route("/admin/analytics/board")
@login_required
def admin_analytics_board_report():
    dashboard = build_admin_dashboard(app.config, request.args)
    return render_template("admin/analytics_board.html", title="Board Summary", dashboard=dashboard, admin_user=os.getenv("ADMIN_USERNAME", "admin"))


@app.route("/admin/analytics/page")
@login_required
def admin_analytics_page_report():
    page_path = request.args.get("page_path", "/")
    start, end, range_name = analytics.date_range_from_args(request.args)
    filters = {"page_path": page_path, "environment": analytics.analytics_environment(app.config)}
    summary = analytics.analytics_store(app.config).query_summary(start, end, filters)
    events = analytics.analytics_store(app.config).query_events(start, end, filters, page=1, page_size=25)
    recommendations = []
    totals = summary["totals"]
    if totals.get("page_views", 0) >= 10 and not totals.get("book_actions", 0):
        recommendations.append("This page has traffic but no recorded book action. Test a contextual book or signed-copy CTA.")
    if totals.get("newsletter_signup_attempts", 0) and totals.get("newsletter_signups", 0) == 0:
        recommendations.append("Signup attempts are not becoming successful signup events. Check the Mailchimp flow for this page.")
    if not recommendations:
        recommendations.append("No page-specific opportunity stands out yet. More activity will improve this readout.")
    return render_template(
        "admin/analytics_page.html",
        title="Page Analytics",
        page_path=page_path,
        summary=summary,
        events=events,
        recommendations=recommendations,
        range_name=range_name,
        start=start.date().isoformat(),
        end=(end - timedelta(days=1)).date().isoformat(),
    )


@app.route("/analytics/events", methods=["POST"])
def collect_analytics_events():
    if not analytics.analytics_enabled(app.config):
        return jsonify({"ok": True, "stored": 0, "disabled": True}), 202
    if not analytics.same_origin_request(request, app.config["SITE_DOMAIN"]):
        return jsonify({"ok": False, "message": "Analytics request was not accepted."}), 403
    try:
        events = analytics.parse_event_request(request, app.config)
        for event in events:
            analytics.enrich_event_with_request(event, request)
        result = analytics.analytics_store(app.config).store_events(events)
    except analytics.AnalyticsValidationError as error:
        return jsonify({"ok": False, "message": str(error)}), 400
    except Exception:
        return jsonify({"ok": False, "message": "Analytics event could not be recorded."}), 202
    return jsonify({"ok": True, "stored": result["inserted"], "duplicates": result["duplicates"]}), 202


@app.route("/admin/content")
@login_required
def admin_content_index():
    posts = get_posts()
    query = request.args.get("q", "").strip().lower()
    series = request.args.get("series", "").strip()
    tag = request.args.get("tag", "").strip().lower()
    author = request.args.get("author", "").strip().lower()
    if query:
        posts = [post for post in posts if query in post["title"].lower() or query in post["slug"].lower() or query in post["excerpt"].lower()]
    if series:
        posts = [post for post in posts if post.get("series") == series]
    if tag:
        posts = [post for post in posts if tag in [item.lower() for item in post.get("tags", [])]]
    if author:
        posts = [post for post in posts if author in post.get("author", "").lower()]
    for post in posts:
        try:
            post["updated"] = datetime.fromtimestamp(post["path"].stat().st_mtime).date().isoformat()
        except OSError:
            post["updated"] = ""
    all_posts = get_posts()
    return render_template(
        "admin/content.html",
        title="Content Studio",
        posts=posts,
        series_options=sorted({post.get("series") for post in all_posts if post.get("series")}),
        tag_options=sorted({tag for post in all_posts for tag in post.get("tags", [])})[:80],
        filters={"q": request.args.get("q", ""), "series": series, "tag": request.args.get("tag", ""), "author": request.args.get("author", "")},
    )


@app.route("/admin/content/<slug>/revisions")
@login_required
def admin_content_revisions(slug):
    post = get_post(slug)
    if not post:
        abort(404)
    return render_template("admin/revisions.html", title="Revisions", post=post, revisions=blog_revisions(slug))


@app.route("/admin/campaign-note", methods=["POST"])
@login_required
def admin_campaign_note():
    validate_admin_csrf()
    flash("Campaign notes were replaced by first-party campaign attribution and the campaign link builder.", "info")
    return redirect(url_for("admin_analytics"))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html", title="Page Not Found"), 404


if __name__ == "__main__":
    app.run(debug=True)
