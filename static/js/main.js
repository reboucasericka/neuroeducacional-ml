(() => {
  const header = document.querySelector(".site-header");
  const toggle = document.querySelector(".nav-toggle");
  const mobileNav = document.querySelector(".nav-mobile");
  const yearEl = document.getElementById("year");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }

  const onScroll = () => {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 12);
  };

  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  const closeMobile = () => {
    if (!toggle || !mobileNav) return;
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Abrir menu");
    mobileNav.classList.remove("is-open");
  };

  const openMobile = () => {
    if (!toggle || !mobileNav) return;
    toggle.setAttribute("aria-expanded", "true");
    toggle.setAttribute("aria-label", "Fechar menu");
    mobileNav.classList.add("is-open");
  };

  if (toggle && mobileNav) {
    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      if (expanded) closeMobile();
      else openMobile();
    });

    mobileNav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", closeMobile);
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMobile();
  });

  if (!reduceMotion && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );

    document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
  } else {
    document.querySelectorAll(".reveal").forEach((el) => el.classList.add("is-visible"));
  }
})();
