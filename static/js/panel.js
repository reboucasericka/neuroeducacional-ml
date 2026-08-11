(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Dropdown acessível (+ Novo registo, etc.)
  document.querySelectorAll("[data-dropdown]").forEach((root) => {
    const trigger = root.querySelector("[data-dropdown-trigger]");
    const menu = root.querySelector("[data-dropdown-menu]");
    if (!trigger || !menu) return;

    const close = () => {
      trigger.setAttribute("aria-expanded", "false");
      menu.hidden = true;
    };
    const open = () => {
      trigger.setAttribute("aria-expanded", "true");
      menu.hidden = false;
      const first = menu.querySelector("[role='menuitem']");
      if (first) first.focus();
    };

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      const expanded = trigger.getAttribute("aria-expanded") === "true";
      if (expanded) close();
      else open();
    });

    menu.querySelectorAll("[role='menuitem']").forEach((item) => {
      item.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          close();
          trigger.focus();
        }
      });
    });

    document.addEventListener("click", (event) => {
      if (!root.contains(event.target)) close();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
  });

  // Tabs do prontuário → select no mobile
  document.querySelectorAll("[data-record-nav]").forEach((nav) => {
    const select = nav.querySelector("[data-record-nav-select]");
    if (!select) return;
    select.addEventListener("change", () => {
      if (select.value) window.location.href = select.value;
    });
  });

  // Confirmação via <dialog> para forms com data-confirm
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.confirmed === "1") return;
      const message = form.getAttribute("data-confirm") || "Confirmar esta ação?";
      const dialog = document.getElementById("global-confirm-dialog");
      if (!dialog || typeof dialog.showModal !== "function") {
        if (!window.confirm(message)) event.preventDefault();
        return;
      }
      event.preventDefault();
      const msgEl = dialog.querySelector("[data-confirm-message]");
      if (msgEl) msgEl.textContent = message;
      dialog.showModal();
      const onClose = () => {
        dialog.removeEventListener("close", onClose);
        if (dialog.returnValue === "confirm") {
          form.dataset.confirmed = "1";
          if (typeof form.requestSubmit === "function") form.requestSubmit();
          else form.submit();
        }
      };
      dialog.addEventListener("close", onClose);
    });
  });

  // Anamnese: foco no primeiro erro + navegação por secção
  const firstError = document.querySelector(".field--error [aria-invalid='true'], .field--error input, .field--error textarea, .field--error select");
  if (firstError) {
    firstError.focus({ preventScroll: reduceMotion });
    if (!reduceMotion) firstError.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  document.querySelectorAll("[data-anamnesis-nav] a").forEach((link) => {
    link.addEventListener("click", (event) => {
      const targetId = link.getAttribute("href");
      if (!targetId || !targetId.startsWith("#")) return;
      const section = document.querySelector(targetId);
      if (!section) return;
      event.preventDefault();
      section.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
      const focusable = section.querySelector("input, textarea, select, button");
      if (focusable) focusable.focus({ preventScroll: true });
      document.querySelectorAll("[data-anamnesis-nav] a").forEach((a) => a.removeAttribute("aria-current"));
      link.setAttribute("aria-current", "true");
    });
  });

  const anamnesisSelect = document.querySelector("[data-anamnesis-select]");
  if (anamnesisSelect) {
    anamnesisSelect.addEventListener("change", () => {
      const section = document.querySelector(anamnesisSelect.value);
      if (section) section.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    });
  }
})();
