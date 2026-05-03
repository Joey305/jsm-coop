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





/* ================================
   Global Purchase Modal
================================ */

document.addEventListener("DOMContentLoaded", () => {
  const purchaseModal = document.getElementById("purchase-modal");
  const openButtons = document.querySelectorAll("[data-purchase-open]");
  const closeButtons = document.querySelectorAll("[data-purchase-close]");
  const mobileMenu = document.querySelector("[data-mobile-menu]");
  const menuToggle = document.querySelector("[data-menu-toggle]");

  if (!purchaseModal || !openButtons.length) return;

  let lastFocusedElement = null;

  const openPurchaseModal = () => {
    lastFocusedElement = document.activeElement;

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
    button.addEventListener("click", openPurchaseModal);
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

