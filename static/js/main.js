"use strict";

/*
 * Progressive enhancement only: every page works without this file.
 * Text coming from the server (JSON) is always inserted with textContent.
 */
(function () {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function getCookie(name) {
    const prefix = name + "=";
    for (const part of document.cookie.split(";")) {
      const item = part.trim();
      if (item.startsWith(prefix)) return decodeURIComponent(item.slice(prefix.length));
    }
    return "";
  }

  /* ---- 4. Toasts: auto-dismiss after 4s + close button ----------------- */
  const TOAST_MS = 4000;

  function dismissToast(toast) {
    if (!toast.isConnected) return;
    if (reducedMotion()) {
      toast.remove();
      return;
    }
    toast.classList.add("is-leaving");
    setTimeout(() => toast.remove(), 300);
  }

  function setupToast(toast) {
    const close = el("button", "message__close", "✕");
    close.type = "button";
    close.setAttribute("aria-label", "Mesajı kapat");
    close.addEventListener("click", () => dismissToast(toast));
    toast.append(close);
    setTimeout(() => dismissToast(toast), TOAST_MS);
  }

  function showToast(text, kind) {
    let container = $("#toasts");
    if (!container) {
      container = el("div", "toasts");
      container.id = "toasts";
      container.setAttribute("role", "status");
      document.body.insertBefore(container, $("main") || null);
    }
    const toast = el("div", "message message--" + (kind || "info"), text);
    container.append(toast);
    setupToast(toast);
  }

  function initToasts() {
    $$("#toasts .message").forEach(setupToast);
  }

  /* ---- 3. Result bar animation ----------------------------------------- */
  function animateBars(root) {
    if (reducedMotion()) return;
    const fills = $$(".result__fill[data-percent]", root);
    fills.forEach((fill) => {
      fill.style.width = "0%";
    });
    // Force a reflow so the 0% width is applied before animating to the target.
    void document.body.offsetWidth;
    requestAnimationFrame(() => {
      fills.forEach((fill) => {
        fill.style.width = fill.dataset.percent + "%";
      });
    });
  }

  /* ---- 2. Voting with fetch -------------------------------------------- */
  function buildResults(data) {
    const wrap = el("div", "results");
    wrap.dataset.total = String(Number(data.total_votes) || 0);
    wrap.tabIndex = -1;
    if (!data.total_votes) wrap.append(el("p", "results__empty", "Henüz oy yok"));

    const list = el("ul", "options");
    for (const r of data.results) {
      const percent = Number(r.percent) || 0;
      const item = el("li", "result option--" + ((Number(r.order) || 0) + 1));

      const head = el("div", "result__head");
      head.append(el("span", "result__text", r.text));
      const badges = el("span", "result__badges");
      if (r.is_mine) badges.append(el("span", "badge badge--mine", "Senin seçimin ✓"));
      if (r.is_leading) badges.append(el("span", "badge badge--lead", "👑 Önde"));
      head.append(badges);

      const bar = el("div", "result__bar");
      bar.setAttribute("role", "img");
      bar.setAttribute("aria-label", r.text + ": %" + percent);
      const fill = el("div", "result__fill");
      fill.dataset.percent = String(percent);
      fill.style.width = percent + "%";
      bar.append(fill);

      const numbers = el("div", "result__numbers");
      numbers.append(el("strong", null, "%" + percent), document.createTextNode(" · " + r.votes + " oy"));

      item.append(head, bar, numbers);
      list.append(item);
    }
    wrap.append(list, el("p", "results__total", "Toplam " + data.total_votes + " oy"));
    return wrap;
  }

  function initVoteForm() {
    const form = $("form.vote-form");
    if (!form || !window.fetch || !window.FormData) return;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = $("button[type=submit]", form);
      if (button && button.disabled) return;
      if (button) button.disabled = true;

      try {
        const token = getCookie("csrftoken") || ($("input[name=csrfmiddlewaretoken]", form) || {}).value || "";
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          credentials: "same-origin",
          headers: { Accept: "application/json", "X-CSRFToken": token },
        });
        if (!(response.headers.get("content-type") || "").includes("application/json")) {
          throw new Error("unexpected response");
        }
        const data = await response.json();
        if (response.status === 429) {
          // Rate limited: tell the user and let them retry later, no form fallback.
          showToast(data.message, "error");
          if (button) button.disabled = false;
          return;
        }
        if (!data.ok) throw new Error("rejected");

        const results = buildResults(data);
        // The author already has a results block above the form: swap it, drop the form.
        const existing = $(".results");
        if (existing) {
          existing.replaceWith(results);
          form.remove();
          const title = $(".vote-title");
          if (title) title.remove();
        } else {
          form.replaceWith(results);
        }
        animateBars(results);
        results.focus({ preventScroll: true });
        showToast(data.message, "success");
      } catch (error) {
        // Network problem or a rejected vote: fall back to the normal form post,
        // which shows the server's message after a redirect.
        HTMLFormElement.prototype.submit.call(form);
      }
    });
  }

  /* ---- 1. Poll create form: add/remove options -------------------------- */
  function initPollForm() {
    const fields = $$("[data-option-field]");
    if (fields.length < 3) return;

    const MIN = 2;
    const inputs = fields.map((field) => $("input", field));
    let shown = MIN;
    fields.forEach((field, index) => {
      if (inputs[index].value.trim() || $(".field__error", field)) shown = Math.max(shown, index + 1);
    });

    const addButton = el("button", "btn btn--ghost btn--small option-add", "+ Seçenek ekle");
    addButton.type = "button";
    fields[fields.length - 1].after(addButton);

    const removeButtons = fields.map((field, index) => {
      const button = el("button", "field__remove", "✕");
      button.type = "button";
      button.setAttribute("aria-label", "Seçenek " + (index + 1) + " kaldır");
      button.addEventListener("click", () => removeOption(index));
      $(".field", field).append(button);
      return button;
    });

    function render() {
      fields.forEach((field, index) => {
        field.hidden = index >= shown;
      });
      addButton.hidden = shown >= fields.length;
      removeButtons.forEach((button) => {
        button.hidden = shown <= MIN;
      });
    }

    function removeOption(index) {
      if (shown <= MIN) return;
      // Shift later values up so the filled options stay contiguous from option 1.
      for (let i = index; i < shown - 1; i++) inputs[i].value = inputs[i + 1].value;
      inputs[shown - 1].value = "";
      shown -= 1;
      render();
      inputs[Math.min(index, shown - 1)].focus();
    }

    addButton.addEventListener("click", () => {
      if (shown >= fields.length) return;
      shown += 1;
      render();
      inputs[shown - 1].focus();
    });

    render();
  }

  /* ---- 5. Copy link ----------------------------------------------------- */
  function initCopyLink() {
    const button = $("[data-copy-url]");
    if (!button || !navigator.clipboard || !navigator.clipboard.writeText) return;
    button.hidden = false;
    const original = button.textContent;
    let timer = null;
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copyUrl);
        button.textContent = "Kopyalandı! ✓";
        clearTimeout(timer);
        timer = setTimeout(() => {
          button.textContent = original;
        }, 2000);
      } catch (error) {
        /* Clipboard blocked: leave the button as it is. */
      }
    });
  }

  /* ---- Countdown to the poll's closing time --------------------------- */
  function formatRemaining(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const days = Math.floor(total / 86400);
    const hours = Math.floor((total % 86400) / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;
    if (days > 0) return days + " gün " + hours + " sa";
    if (hours > 0) return hours + " sa " + minutes + " dk";
    if (minutes > 0) return minutes + " dk " + String(seconds).padStart(2, "0") + " sn";
    return seconds + " sn";
  }

  function initCountdown() {
    const box = $(".countdown[data-closes-at]");
    const target = box && $("[data-countdown]", box);
    if (!box || !target) return;
    const closesAt = Date.parse(box.dataset.closesAt);
    if (Number.isNaN(closesAt)) return;

    const timer = setInterval(() => {
      const left = closesAt - Date.now();
      if (left <= 0) {
        clearInterval(timer);
        target.textContent = "0 sn";
        // The server decides what a finished poll looks like: reload to show results.
        setTimeout(() => window.location.reload(), 1200);
        return;
      }
      target.textContent = formatRemaining(left);
    }, 1000);
    target.textContent = formatRemaining(closesAt - Date.now());
  }

  /* ---- 6. Mobile menu --------------------------------------------------- */
  function initMenu() {
    const toggle = $(".navbar__toggle");
    const nav = $("#nav-links");
    if (!toggle || !nav) return;

    function setOpen(open) {
      toggle.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("is-open", open);
    }

    toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        setOpen(false);
        toggle.focus();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initToasts();
    initMenu();
    initPollForm();
    initVoteForm();
    initCopyLink();
    initCountdown();
    animateBars(document);
  });
})();
