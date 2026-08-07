import os
import re
from datetime import datetime
from pathlib import Path
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


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BLOG_DIR = BASE_DIR / "blogs"
DEFAULT_SIGNED_BOOK_PAYMENT_LINK = "https://www.paypal.com/ncp/payment/SLQDNTABMS9JS"

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
app.config["SITE_NAME"] = os.getenv("SITE_NAME", "JSM Cooperative Corporation")
app.config["SITE_DOMAIN"] = os.getenv("SITE_DOMAIN", "https://jsmcoop.com")
app.config["CONTACT_EMAIL"] = os.getenv("CONTACT_EMAIL", "books@jsmcoop.com")
app.config["PAYPAL_DONATE_BUTTON_ID"] = os.getenv("PAYPAL_DONATE_BUTTON_ID", "TLWCSL2KJDZQU")
app.config["GA_MEASUREMENT_ID"] = os.getenv("GA_MEASUREMENT_ID", "").strip()
app.config["PAYPAL_SIGNED_BOOK_URL"] = os.getenv("PAYPAL_SIGNED_BOOK_URL", DEFAULT_SIGNED_BOOK_PAYMENT_LINK).strip()
app.config["BOOK_DIRECT_CHECKOUT_URL"] = os.getenv(
    "BOOK_DIRECT_CHECKOUT_URL",
    app.config["PAYPAL_SIGNED_BOOK_URL"],
).strip()
app.config["BOOK_DIRECT_PROVIDER"] = os.getenv("BOOK_DIRECT_PROVIDER", "PayPal").strip()
app.config["BOOK_DIRECT_PRICE_AMOUNT"] = os.getenv("BOOK_DIRECT_PRICE_AMOUNT", "15.00").strip()
app.config["BOOK_DIRECT_PRICE_CURRENCY"] = os.getenv("BOOK_DIRECT_PRICE_CURRENCY", "USD").strip().upper()
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

    return {
        "slug": slug,
        "title": metadata.get("title", slug.replace("-", " ").title()),
        "date": metadata.get("date", "Undated"),
        "author": metadata.get("author", "JSM Cooperative"),
        "excerpt": metadata.get("excerpt", body[:180].replace("\n", " ") + "..."),
        "cover": cover,
        "cover_webp": cover_webp,
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


@app.route("/book/checkout/start")
def direct_book_checkout():
    checkout_url = app.config["BOOK_DIRECT_CHECKOUT_URL"]

    if not checkout_url:
        flash("Direct book checkout is not configured yet. Please choose a retailer option.", "info")
        return redirect(url_for("book_signed"))

    attribution = {
        key: request.args.get(key)
        for key in ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid"]
        if request.args.get(key)
    }

    if attribution:
        parsed = urlsplit(checkout_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(attribution)
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
