(function () {
  const ATTRIBUTION_KEY = "jsm_campaign_attribution";
  const ATTRIBUTION_FIELDS = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
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

    ATTRIBUTION_FIELDS.forEach((field) => {
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

  const buildPayload = (extra) => ({
    page_path: window.location.pathname,
    landing_page: attribution.landing_page || window.location.pathname,
    utm_source: attribution.utm_source || "",
    utm_medium: attribution.utm_medium || "",
    utm_campaign: attribution.utm_campaign || "",
    utm_term: attribution.utm_term || "",
    utm_content: attribution.utm_content || "",
    gclid: attribution.gclid || "",
    ...extra,
  });

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
      value: element.dataset.value || undefined,
      currency: element.dataset.currency || undefined,
      transaction_id: element.dataset.transactionId || undefined,
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
          ATTRIBUTION_FIELDS.forEach((field) => {
            if (campaign[field]) url.searchParams.set(field, campaign[field]);
          });
          href = url.pathname + url.search + url.hash;
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
