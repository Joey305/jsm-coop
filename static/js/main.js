(function () {
  const ATTRIBUTION_KEY = "jsm_campaign_attribution";
  window.JSM_ATTRIBUTION_FIELDS = window.JSM_ATTRIBUTION_FIELDS || [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "gbraid",
    "wbraid",
  ];
  const ADS_CONVERSION_EVENTS = new Set([
    "direct_checkout_returned",
    "verified_direct_purchase_completed",
    "camino_subscription_completed",
  ]);

  const readAttribution = () => {
    try {
      return JSON.parse(window.sessionStorage.getItem(ATTRIBUTION_KEY) || "{}");
    } catch (error) {
      return {};
    }
  };

  const writeAttribution = (data) => {
    try {
      window.sessionStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(data));
    } catch (error) {
      return false;
    }
    return true;
  };

  const captureAttribution = () => {
    const params = new URLSearchParams(window.location.search);
    const current = readAttribution();
    let changed = false;

    window.JSM_ATTRIBUTION_FIELDS.forEach((field) => {
      const value = params.get(field);
      if (value) {
        current[field] = value;
        changed = true;
      }
    });

    if (!current.landing_page) {
      current.landing_page = window.location.pathname;
      changed = true;
    }

    if (changed) writeAttribution(current);
    return current;
  };

  const attribution = captureAttribution();
  const firstPartyConfig = window.__JSM_FIRST_PARTY_ANALYTICS__ || {};
  const FIRST_PARTY_SESSION_KEY = "jsm_first_party_session_id";

  const randomId = () => {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return Math.random().toString(36).slice(2) + Date.now().toString(36);
  };

  const firstPartySessionId = () => {
    try {
      const existing = window.sessionStorage.getItem(FIRST_PARTY_SESSION_KEY);
      if (existing) return existing;
      const generated = "sess_" + randomId();
      window.sessionStorage.setItem(FIRST_PARTY_SESSION_KEY, generated);
      return generated;
    } catch (error) {
      return "sess_" + randomId();
    }
  };

  const deviceCategory = () => {
    const width = window.innerWidth || document.documentElement.clientWidth || 1200;
    if (width < 760) return "mobile";
    if (width < 1100) return "tablet";
    return "desktop";
  };

  const domainFor = (url) => {
    try {
      return url ? new URL(url, window.location.href).hostname : "";
    } catch (error) {
      return "";
    }
  };

  const buildPayload = (extra) => ({
    page_path: window.location.pathname,
    landing_page: attribution.landing_page || window.location.pathname,
    utm_source: attribution.utm_source || "",
    utm_medium: attribution.utm_medium || "",
    utm_campaign: attribution.utm_campaign || "",
    utm_term: attribution.utm_term || "",
    utm_content: attribution.utm_content || "",
    gclid: attribution.gclid || "",
    gbraid: attribution.gbraid || "",
    wbraid: attribution.wbraid || "",
    ...extra,
  });

  const firstPartyEventName = (eventName, payload) => {
    if (eventName === "newsletter_signup" && payload.first_party_success !== true) {
      return "newsletter_signup_attempt";
    }
    return eventName;
  };

  const sendFirstParty = (eventName, payload) => {
    if (!firstPartyConfig.enabled || !firstPartyConfig.endpoint || window.location.pathname.startsWith("/admin")) {
      return;
    }

    const firstPartyName = firstPartyEventName(eventName, payload || {});
    const event = {
      event_id: "client:" + randomId(),
      schema_version: 1,
      event_name: firstPartyName,
      client_occurred_at: new Date().toISOString(),
      page_path: window.location.pathname || "/",
      page_title: document.title || "",
      landing_page: payload.landing_page || attribution.landing_page || window.location.pathname || "/",
      referrer_url: document.referrer || "",
      referrer_domain: domainFor(document.referrer),
      source: payload.utm_source || attribution.utm_source || "",
      medium: payload.utm_medium || attribution.utm_medium || "",
      campaign: payload.utm_campaign || attribution.utm_campaign || "",
      term: payload.utm_term || attribution.utm_term || "",
      campaign_content: payload.utm_content || attribution.utm_content || "",
      gclid: payload.gclid || attribution.gclid || "",
      gbraid: payload.gbraid || attribution.gbraid || "",
      wbraid: payload.wbraid || attribution.wbraid || "",
      anonymous_session_id: firstPartySessionId(),
      device_category: deviceCategory(),
      environment: firstPartyConfig.environment || "",
      article_slug: payload.article_slug || "",
      series: payload.series || "",
      element_position: payload.cta_location || payload.position || "",
      destination_url: payload.destination || "",
      destination_domain: domainFor(payload.destination || ""),
      metadata: {
        retailer: payload.retailer || "",
        book_language: payload.book_language || "",
        cta_location: payload.cta_location || "",
        value: payload.value || "",
        currency: payload.currency || "",
        transaction_id: payload.transaction_id || "",
        checkout_id: payload.checkout_id || ""
      }
    };

    const body = JSON.stringify(event);
    try {
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: "application/json" });
        if (navigator.sendBeacon(firstPartyConfig.endpoint, blob)) return;
      }
      window.fetch(firstPartyConfig.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        credentials: "same-origin",
        keepalive: true
      }).catch(() => {});
    } catch (error) {}
  };

  const sendAdsConversion = (eventName, payload, callback) => {
    if (!ADS_CONVERSION_EVENTS.has(eventName) || typeof window.gtag !== "function") {
      if (callback) callback();
      return;
    }

    let called = false;
    const done = () => {
      if (called) return;
      called = true;
      if (callback) callback();
    };

    window.gtag("event", "conversion", {
      send_to: "AW-16512731660/mdXICPyLzaAZEIyU8cE9",
      value: payload.value || undefined,
      currency: payload.currency || undefined,
      transaction_id: payload.transaction_id || undefined,
      event_callback: done,
    });

    window.setTimeout(done, 700);
  };

  const track = (eventName, data, callback) => {
    const payload = buildPayload(data || {});

    if (typeof window.gtag === "function") {
      window.gtag("event", eventName, payload);
    }

    sendFirstParty(eventName, payload);
    sendAdsConversion(eventName, payload, callback);
  };

  const trackMany = (eventNames, data, callback) => {
    const uniqueEvents = [...new Set(eventNames.filter(Boolean))];
    if (!uniqueEvents.length) {
      if (callback) callback();
      return;
    }

    let remaining = uniqueEvents.length;
    const done = () => {
      remaining -= 1;
      if (remaining <= 0 && callback) callback();
    };

    uniqueEvents.forEach((eventName) => track(eventName, data, done));
  };

  window.JSMAnalytics = {
    track,
    trackMany,
    attribution: () => ({ ...attribution }),
  };

  sendFirstParty("page_view", buildPayload({}));

  const engagementEvents = new Set();
  const trackEngagementOnce = (eventName) => {
    if (engagementEvents.has(eventName)) return;
    engagementEvents.add(eventName);
    track(eventName, { cta_location: "engagement_depth" });
  };

  let activeSeconds = 0;
  let lastTick = Date.now();
  const engagementTimer = window.setInterval(() => {
    const now = Date.now();
    if (!document.hidden && document.hasFocus()) {
      activeSeconds += Math.min(5, Math.max(0, (now - lastTick) / 1000));
      if (activeSeconds >= 30) {
        trackEngagementOnce("engaged_30s");
        window.clearInterval(engagementTimer);
      }
    }
    lastTick = now;
  }, 1000);

  const checkScrollDepth = () => {
    const doc = document.documentElement;
    const body = document.body;
    const scrollTop = window.scrollY || doc.scrollTop || body.scrollTop || 0;
    const viewport = window.innerHeight || doc.clientHeight || 0;
    const height = Math.max(doc.scrollHeight, body.scrollHeight, doc.offsetHeight, body.offsetHeight) - viewport;
    if (height <= 0) return;
    const depth = (scrollTop / height) * 100;
    if (depth >= 50) trackEngagementOnce("scroll_50");
    if (depth >= 75) trackEngagementOnce("scroll_75");
    if (depth >= 90) trackEngagementOnce("scroll_90");
  };
  window.addEventListener("scroll", checkScrollDepth, { passive: true });
  window.addEventListener("resize", checkScrollDepth, { passive: true });
  checkScrollDepth();

  window.gtag_report_conversion = function (url) {
    track("retailer_click_amazon_us", { cta_location: "legacy_helper" }, () => {
      if (url) window.location = url;
    });
    return false;
  };
})();

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("[data-menu-toggle]");
  const menu = document.querySelector("[data-mobile-menu]");

  if (toggle && menu) {
    toggle.addEventListener("click", () => {
      const isOpen = menu.classList.toggle("open");
      menu.setAttribute("aria-hidden", String(!isOpen));
      toggle.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
    });
  }

  const header = document.querySelector("[data-header]");
  const onScroll = () => {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 20);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  const revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.14 });
    revealEls.forEach(el => observer.observe(el));
  } else {
    revealEls.forEach(el => el.classList.add("in-view"));
  }
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-analytics-event]").forEach((element) => {
    const eventNames = [
      element.dataset.analyticsEvent,
      ...(element.dataset.analyticsEvents || "").split(/\s+/),
    ].filter(Boolean);
    const eventName = eventNames[0] || "";
    const payload = () => ({
      retailer: element.dataset.retailer || "",
      book_language: element.dataset.bookLanguage || "",
      cta_location: element.dataset.ctaLocation || "",
      article_slug: element.dataset.articleSlug || "",
      series: element.dataset.series || "",
      destination: element.dataset.destination || "",
      value: element.dataset.value || undefined,
      currency: element.dataset.currency || undefined,
      transaction_id: element.dataset.transactionId || undefined,
      checkout_id: element.dataset.checkoutId || undefined,
    });

    if (element.tagName === "FORM") {
      element.addEventListener("submit", () => {
        window.JSMAnalytics.trackMany(eventNames, payload());
      });
      return;
    }

    if (element.matches("a[href]")) {
      element.addEventListener("click", (event) => {
        let href = element.getAttribute("href");
        const opensNewTab = element.target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey;
        const eventPayload = payload();

        if (eventNames.includes("direct_checkout_started") && href && href.includes("/book/checkout/start")) {
          const url = new URL(href, window.location.origin);
          const campaign = window.JSMAnalytics.attribution();
          window.JSM_ATTRIBUTION_FIELDS.forEach((field) => {
            if (campaign[field]) url.searchParams.set(field, campaign[field]);
          });
          if (campaign.landing_page) url.searchParams.set("landing_page", campaign.landing_page);
          href = url.pathname + url.search + url.hash;

          if (!opensNewTab) {
            event.preventDefault();
            const jsonUrl = new URL(href, window.location.origin);
            jsonUrl.searchParams.set("format", "json");
            window.fetch(jsonUrl.pathname + jsonUrl.search, {
              method: "GET",
              headers: { "Accept": "application/json" },
              credentials: "same-origin",
            })
              .then((response) => response.ok ? response.json() : Promise.reject(new Error("checkout_prepare_failed")))
              .then((data) => {
                const preparedPayload = {
                  ...eventPayload,
                  checkout_id: data.checkout_id || "",
                  transaction_id: data.checkout_id || eventPayload.transaction_id,
                };
                window.JSMAnalytics.trackMany(eventNames, preparedPayload, () => {
                  window.location.href = data.checkout_url || href;
                });
              })
              .catch(() => {
                window.JSMAnalytics.trackMany(eventNames, eventPayload, () => {
                  window.location.href = href;
                });
              });
            return;
          }
        }

        if (opensNewTab || !href || href.startsWith("#") || href.startsWith("mailto:")) {
          window.JSMAnalytics.trackMany(eventNames, eventPayload);
          return;
        }

        event.preventDefault();
        window.JSMAnalytics.trackMany(eventNames, eventPayload, () => {
          window.location.href = href;
        });
      });
      return;
    }

    element.addEventListener("click", () => {
      window.JSMAnalytics.trackMany(eventNames, payload());
    });
  });

  document.querySelectorAll("[data-preview-zone]").forEach((zone) => {
    let tracked = false;
    const trackPreview = () => {
      if (tracked) return;
      tracked = true;
      const previewEvent = zone.dataset.previewEvent || "book_preview_click";
      const previewEvents = previewEvent === "signed_copy_preview_click"
        ? ["signed_copy_preview_click", "signed_page_preview_click", "book_preview_click"]
        : [previewEvent];
      window.JSMAnalytics.trackMany(previewEvents, {
        book_language: zone.dataset.bookLanguage || "",
        cta_location: zone.dataset.ctaLocation || "preview_embed",
      });
    };
    zone.addEventListener("pointerenter", trackPreview, { once: true });
    zone.addEventListener("focusin", trackPreview, { once: true });
    zone.addEventListener("click", trackPreview, { once: true });
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const purchaseModal = document.getElementById("purchase-modal");
  const openButtons = document.querySelectorAll("[data-purchase-open]");
  const closeButtons = document.querySelectorAll("[data-purchase-close]");
  const mobileMenu = document.querySelector("[data-mobile-menu]");
  const menuToggle = document.querySelector("[data-menu-toggle]");

  if (!purchaseModal || !openButtons.length) return;

  let lastFocusedElement = null;

  const openPurchaseModal = (button) => {
    lastFocusedElement = document.activeElement;

    window.JSMAnalytics.track("purchase_modal_open", {
      cta_location: button.dataset.ctaLocation || "unknown",
      book_language: button.dataset.bookLanguage || "en",
    });

    purchaseModal.classList.add("is-open");
    purchaseModal.setAttribute("aria-hidden", "false");
    document.body.classList.add("purchase-modal-open");

    if (mobileMenu) {
      mobileMenu.setAttribute("aria-hidden", "true");
      mobileMenu.classList.remove("is-open", "open", "active");
    }

    if (menuToggle) {
      menuToggle.classList.remove("is-open", "open", "active");
      menuToggle.setAttribute("aria-expanded", "false");
    }

    const closeButton = purchaseModal.querySelector("[data-purchase-close]");
    if (closeButton) closeButton.focus();
  };

  const closePurchaseModal = () => {
    purchaseModal.classList.remove("is-open");
    purchaseModal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("purchase-modal-open");

    if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
      lastFocusedElement.focus();
    }
  };

  openButtons.forEach((button) => {
    button.addEventListener("click", () => openPurchaseModal(button));
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", closePurchaseModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && purchaseModal.classList.contains("is-open")) {
      closePurchaseModal();
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const promo = document.querySelector("[data-signed-promo]");
  const promoTab = document.querySelector("[data-signed-promo-tab]");
  if (!promo) return;

  const DISMISS_KEY = "jsm_signed_copy_promo_dismissed";
  const DISMISS_DURATION_MS = 7 * 24 * 60 * 60 * 1000;
  const SHOW_DELAY_MS = 9000;
  const REOPEN_DELAY_MS = 2400;
  const mobileQuery = window.matchMedia("(max-width: 767px)");
  const suppressMobile = promo.dataset.suppressMobile === "true";

  if (suppressMobile && mobileQuery.matches) {
    promo.remove();
    if (promoTab) promoTab.remove();
    return;
  }

  const deviceType = () => mobileQuery.matches ? "mobile" : "desktop";
  const promoPayload = () => ({
    cta_location: "floating_signed_copy",
    device_type: deviceType(),
  });

  const readDismissedUntil = () => {
    try {
      return Number(window.localStorage.getItem(DISMISS_KEY) || 0);
    } catch (error) {
      return 0;
    }
  };

  const writeDismissedUntil = () => {
    try {
      window.localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_DURATION_MS));
    } catch (error) {
      return false;
    }
    return true;
  };

  const showPromoTab = () => {
    if (!promoTab || mobileQuery.matches) return;
    window.setTimeout(() => {
      if (!promo.classList.contains("is-visible")) {
        promoTab.classList.add("is-visible");
      }
    }, REOPEN_DELAY_MS);
  };

  let hasShown = false;
  let timerId = null;
  const dismissedInitially = readDismissedUntil() > Date.now();

  const showPromo = () => {
    if (hasShown) return;
    if (suppressMobile && mobileQuery.matches) return;
    hasShown = true;
    if (timerId) window.clearTimeout(timerId);
    promo.classList.add("is-visible");
    window.JSMAnalytics.track("signed_copy_promo_impression", promoPayload());
    window.removeEventListener("scroll", onPromoScroll);
  };

  const getScrollDepth = () => {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    if (scrollable <= 0) return 1;
    return window.scrollY / scrollable;
  };

  function onPromoScroll() {
    if (getScrollDepth() >= 0.25) showPromo();
  }

  const closeButton = promo.querySelector("[data-signed-promo-close]");
  if (closeButton) {
    closeButton.addEventListener("click", () => {
      writeDismissedUntil();
      promo.classList.remove("is-visible");
      window.JSMAnalytics.track("signed_copy_promo_dismiss", promoPayload());
      showPromoTab();
    });
  }

  const promoLink = promo.querySelector("[data-signed-promo-link]");
  if (promoLink) {
    promoLink.addEventListener("click", (event) => {
      const href = promoLink.getAttribute("href");
      const opensNewTab = promoLink.target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey;

      if (opensNewTab || !href || href.startsWith("#") || href.startsWith("mailto:")) {
        window.JSMAnalytics.track("signed_copy_promo_click", promoPayload());
        return;
      }

      event.preventDefault();
      window.JSMAnalytics.track("signed_copy_promo_click", promoPayload(), () => {
        window.location.href = href;
      });
    });
  }

  if (promoTab) {
    promoTab.addEventListener("click", () => {
      promoTab.classList.remove("is-visible");
      if (!document.body.contains(promo)) {
        document.body.appendChild(promo);
      }
      promo.classList.add("is-visible");
      window.JSMAnalytics.track("signed_copy_promo_reopen", promoPayload());
      const link = promo.querySelector("[data-signed-promo-link]");
      if (link) link.focus();
    });
  }

  if (dismissedInitially) {
    showPromoTab();
    return;
  }

  timerId = window.setTimeout(showPromo, SHOW_DELAY_MS);
  window.addEventListener("scroll", onPromoScroll, { passive: true });
  onPromoScroll();
});
