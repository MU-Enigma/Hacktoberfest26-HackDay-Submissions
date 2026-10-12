(() => {
  "use strict";

  const state = {
    view: "landing",
    me: null,
    category: "All",
    intention: "all",
    activities: [],
    detailId: null,
    loading: false,
    reportingId: null,
  };

  const PASTEL = [
    "pastel-pink",
    "pastel-mint",
    "pastel-sky",
    "pastel-butter",
    "pastel-lavender",
    "pastel-orange",
  ];
  const TILTS = ["tilt-a", "tilt-b", "tilt-c"];
  const DECOS = ["✦", "✿", "★", "♡", "✧", "❀"];
  const CAT_DECO = {
    Coffee: "☕",
    Games: "🎲",
    Music: "♪",
    Study: "📚",
    Outdoors: "🌿",
    Creative: "🎨",
    Tech: "💻",
    Food: "🍜",
  };

  const MASCOTS = {
    star: `<svg viewBox="0 0 40 40" width="100%" height="100%"><polygon points="20,3 24.5,14 36.5,15.5 27.5,23.5 30,35.5 20,29 10,35.5 12.5,23.5 3.5,15.5 15.5,14" fill="#FFE38A" stroke="#453A55" stroke-width="2"/><circle cx="16" cy="18" r="1.5" fill="#393149"/><circle cx="24" cy="18" r="1.5" fill="#393149"/><path d="M17 23 Q20 26 23 23" stroke="#393149" stroke-width="1.6" fill="none" stroke-linecap="round"/></svg>`,
    blob: `<svg viewBox="0 0 40 40" width="100%" height="100%"><path d="M10 24 C10 12 30 12 30 24 C30 33 10 33 10 24 Z" fill="#D9CCFF" stroke="#453A55" stroke-width="2"/><circle cx="16" cy="20" r="1.5" fill="#393149"/><circle cx="24" cy="20" r="1.5" fill="#393149"/><path d="M17 24 Q20 27 23 24" stroke="#393149" stroke-width="1.6" fill="none" stroke-linecap="round"/><circle cx="13" cy="22" r="1.5" fill="#FFB7CE"/><circle cx="27" cy="22" r="1.5" fill="#FFB7CE"/></svg>`,
    flower: `<svg viewBox="0 0 40 40" width="100%" height="100%"><circle cx="20" cy="12" r="5.5" fill="#FFB7CE" stroke="#453A55" stroke-width="1.5"/><circle cx="27" cy="17" r="5.5" fill="#FFB7CE" stroke="#453A55" stroke-width="1.5"/><circle cx="25" cy="25" r="5.5" fill="#FFB7CE" stroke="#453A55" stroke-width="1.5"/><circle cx="15" cy="25" r="5.5" fill="#FFB7CE" stroke="#453A55" stroke-width="1.5"/><circle cx="13" cy="17" r="5.5" fill="#FFB7CE" stroke="#453A55" stroke-width="1.5"/><circle cx="20" cy="20" r="5.5" fill="#FFE38A" stroke="#453A55" stroke-width="2"/><circle cx="18" cy="19" r="1" fill="#393149"/><circle cx="22" cy="19" r="1" fill="#393149"/><path d="M18.5 22 Q20 23.5 21.5 22" stroke="#393149" stroke-width="1.2" fill="none"/></svg>`,
    spark: `<svg viewBox="0 0 40 40" width="100%" height="100%"><path d="M20 4 Q20 20 4 20 Q20 20 20 36 Q20 20 36 20 Q20 20 20 4 Z" fill="#C9F2D0" stroke="#453A55" stroke-width="2"/><circle cx="18" cy="18" r="1.2" fill="#393149"/><circle cx="22" cy="18" r="1.2" fill="#393149"/><path d="M18.5 22 Q20 23.5 21.5 22" stroke="#393149" stroke-width="1.2" fill="none" stroke-linecap="round"/></svg>`,
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const els = {
    landing: $("#view-landing"),
    shell: $("#app-shell"),
    navUserArea: $("#nav-user-area"),
    auth: $("#view-auth"),
    loginPane: $("#auth-login-pane"),
    registerPane: $("#auth-register-pane"),
    tabBtnLogin: $("#tab-btn-login"),
    tabBtnRegister: $("#tab-btn-register"),
    loginForm: $("#login-form"),
    registerForm: $("#register-form"),
    discover: $("#view-discover"),
    detail: $("#view-detail"),
    create: $("#view-create"),
    myQuests: $("#view-my-quests"),
    profile: $("#view-profile"),
    grid: $("#activity-grid"),
    status: $("#discover-status"),
    modalRoot: $("#modal-root"),
    modalMessage: $("#modal-message"),
    modalActions: $("#modal-actions"),
    modalDialog: $(".modal-dialog"),
    reportModal: $("#report-modal"),
    reportReason: $("#report-reason"),
    btnSubmitReport: $("#btn-submit-report"),
    toastRoot: $("#toast-root"),
    createForm: $("#create-form"),
    myContent: $("#my-quests-content"),
    profileContent: $("#profile-content"),
  };

  let lastFocus = null;

  async function api(path, options = {}) {
    const isFormData = options.body instanceof FormData;
    const headers = isFormData ? (options.headers || {}) : { "Content-Type": "application/json", ...(options.headers || {}) };
    const opts = {
      headers,
      ...options,
    };
    const res = await fetch(path, opts);
    let data = null;
    const text = await res.text();
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { error: "bad_json", message: text };
    }
    if (!res.ok) {
      const err = new Error(data?.message || data?.error || "request failed");
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function initials(name) {
    return String(name || "?")
      .split(/\s+/)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() || "")
      .join("");
  }

  function renderAvatar(u, sizeClass = "") {
    if (!u) return `<span class="avatar ${sizeClass}">?</span>`;
    if (u.avatar_url) {
      return `<span class="avatar ${sizeClass}"><img src="${escapeHtml(u.avatar_url)}" alt="${escapeHtml(u.display_name)}" /></span>`;
    }
    const mascotKey = u.default_avatar || "star";
    if (MASCOTS[mascotKey]) {
      return `<span class="avatar ${sizeClass}">${MASCOTS[mascotKey]}</span>`;
    }
    return `<span class="avatar ${sizeClass}">${escapeHtml(initials(u.display_name))}</span>`;
  }

  function formatWhen(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  function intentionLabel(type) {
    if (type === "friends") return "Friendship";
    if (type === "dating") return "Dating";
    return "Either / open";
  }

  function cardStyle(id) {
    const pastel = PASTEL[id % PASTEL.length];
    const tilt = TILTS[id % TILTS.length];
    const deco = DECOS[id % DECOS.length];
    return { pastel, tilt, deco };
  }

  function toast(message, variant = "ok") {
    const node = document.createElement("div");
    node.className = `toast ${variant === "error" ? "error" : variant === "warn" ? "warn" : ""}`;
    node.textContent = message;
    els.toastRoot.appendChild(node);
    setTimeout(() => node.remove(), 3400);
  }

  function showModal({ message, primary, secondary, variant = "info" }) {
    return new Promise((resolve) => {
      lastFocus = document.activeElement;
      els.modalMessage.textContent = message;
      els.modalActions.innerHTML = "";
      els.modalRoot.classList.remove("hidden");
      els.modalDialog.classList.toggle("success", variant === "success");
      els.modalDialog.classList.toggle("warn", variant === "warn");
      els.modalDialog.classList.toggle("error", variant === "error");

      const finish = (value) => {
        els.modalRoot.classList.add("hidden");
        if (lastFocus && lastFocus.focus) lastFocus.focus();
        resolve(value);
      };

      if (primary) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-primary";
        btn.textContent = primary.label;
        btn.addEventListener("click", () => finish(primary.value ?? true));
        els.modalActions.appendChild(btn);
        setTimeout(() => btn.focus(), 0);
      }

      if (secondary) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-ghost";
        btn.textContent = secondary.label;
        btn.addEventListener("click", () => finish(secondary.value ?? false));
        els.modalActions.appendChild(btn);
      }

      const onKey = (e) => {
        if (e.key === "Escape") {
          document.removeEventListener("keydown", onKey);
          finish(false);
        }
      };
      document.addEventListener("keydown", onKey);

      const backdrop = $("[data-close-modal]", els.modalRoot);
      const onBackdrop = () => {
        backdrop.removeEventListener("click", onBackdrop);
        document.removeEventListener("keydown", onKey);
        finish(false);
      };
      backdrop.addEventListener("click", onBackdrop, { once: true });
    });
  }

  function updateNavUser() {
    if (!els.navUserArea) return;
    if (state.me) {
      const yearBadge = state.me.study_year_label
        ? `<span class="badge-year">${escapeHtml(state.me.study_year_label)}</span>`
        : "";
      const adminBtn = state.me.role === "admin"
        ? `<a href="/admin" class="btn btn-butter" style="padding:0.35rem 0.75rem; font-size:0.8rem">Admin</a>`
        : "";
      els.navUserArea.innerHTML = `
        <button type="button" class="nav-user-pill" data-nav="profile" title="View your profile">
          ${renderAvatar(state.me, "")}
          <span>${escapeHtml(state.me.display_name)}</span>
          ${yearBadge}
        </button>
        ${adminBtn}
        <button type="button" class="btn btn-ghost" id="btn-logout" style="padding:0.35rem 0.65rem; font-size:0.8rem">Log Out</button>
      `;
      $("#btn-logout")?.addEventListener("click", handleLogout);
    } else {
      els.navUserArea.innerHTML = `
        <button type="button" class="btn btn-primary" data-nav="auth" style="padding:0.35rem 0.8rem; font-size:0.85rem">Log In</button>
        <button type="button" class="btn btn-mint" id="btn-nav-demo" style="padding:0.35rem 0.8rem; font-size:0.85rem">Demo</button>
      `;
      $("#btn-nav-demo")?.addEventListener("click", () => handleDemoLogin());
    }
  }

  function setNavActive(view) {
    $$(".nav-item").forEach((btn) => {
      const target = btn.dataset.nav;
      const active = target === view || (view === "detail" && target === "discover");
      btn.classList.toggle("active", active);
      if (active) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
  }

  function showView(view) {
    state.view = view;
    const inApp = view !== "landing";
    els.landing.classList.toggle("hidden", inApp);
    els.shell.classList.toggle("hidden", !inApp);

    const map = {
      auth: els.auth,
      discover: els.discover,
      detail: els.detail,
      create: els.create,
      "my-quests": els.myQuests,
      profile: els.profile,
    };
    Object.entries(map).forEach(([key, el]) => {
      if (el) el.classList.toggle("hidden", key !== view);
    });
    setNavActive(view);
    updateNavUser();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function navigate(view, opts = {}) {
    if (view === "landing") {
      showView("landing");
      return;
    }
    if (view === "auth") {
      showView("auth");
      return;
    }

    if (!state.me) {
      try {
        state.me = await api("/api/me");
      } catch {
        // Not logged in -> go to auth
        showView("auth");
        return;
      }
    }

    showView(view);

    if (view === "discover") await loadDiscover();
    if (view === "detail" && opts.id) await loadDetail(opts.id);
    if (view === "my-quests") await loadMyQuests();
    if (view === "profile") await loadProfile();
    if (view === "create") prepareCreateForm();
  }

  function renderStatus(html) {
    els.status.innerHTML = html || "";
  }

  function loadingBubble(text = "asking the campus pigeons for directions...") {
    return `
      <div class="dialogue-panel">
        <div aria-hidden="true" style="font-size:1.6rem">🐦</div>
        <div class="bubble"><p>${escapeHtml(text)}</p></div>
      </div>`;
  }

  function emptyBubble(message, actionLabel, actionNav) {
    return `
      <div class="dialogue-panel">
        <div aria-hidden="true" style="font-size:1.6rem">✦</div>
        <div class="bubble">
          <p>${escapeHtml(message)}</p>
          <button type="button" class="btn btn-primary" data-nav="${actionNav}">${escapeHtml(actionLabel)}</button>
        </div>
      </div>`;
  }

  function renderQuestCard(a, { showRec = true } = {}) {
    const { pastel, tilt, deco } = cardStyle(a.id);
    const tags = (a.interest_tags || [])
      .slice(0, 4)
      .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
      .join("");
    const rec =
      showRec && a.recommendation?.explanation
        ? `<p class="rec-note">${escapeHtml(a.recommendation.explanation)}</p>`
        : "";
    const isFull = a.is_full && !a.joined;
    const isRestricted = a.invite_policy && a.invite_policy !== "everyone";
    const guestBadge = isRestricted
      ? `<span class="badge-eligibility restricted">🔒 ${escapeHtml(a.invite_label || "Guest list")}</span>`
      : `<span class="badge-eligibility">👥 Everyone</span>`;

    const isIneligible = a.eligible === false && !a.joined;
    let joinLabel = "join quest";
    let joinDisabled = false;

    if (a.joined) {
      joinLabel = "joined ✓";
      joinDisabled = true;
    } else if (isIneligible) {
      joinLabel = "restricted 🔒";
      joinDisabled = true;
    } else if (isFull) {
      joinLabel = "packed";
      joinDisabled = true;
    }

    const hostYear = a.host?.study_year_label
      ? `<span class="badge-year" style="font-size:0.7rem; padding:0.05rem 0.4rem">${escapeHtml(a.host.study_year_label)}</span>`
      : "";

    return `
      <article class="quest-card ${pastel} ${tilt}" data-id="${a.id}">
        <span class="deco" aria-hidden="true">${CAT_DECO[a.category] || deco}</span>
        <div class="quest-meta">
          <span class="badge">${escapeHtml(a.category)}</span>
          <span class="badge badge-${escapeHtml(a.connection_type)}">${escapeHtml(intentionLabel(a.connection_type))}</span>
          ${guestBadge}
        </div>
        <h3>${escapeHtml(a.title)}</h3>
        <p class="desc">${escapeHtml(a.description)}</p>
        <div class="quest-facts">
          <span>🗓 ${escapeHtml(formatWhen(a.starts_at))}</span>
          <span>📍 ${escapeHtml(a.venue)}</span>
          <span style="display:flex; align-items:center; gap:0.35rem">
            ${renderAvatar(a.host, "")} host: <strong>${escapeHtml(a.host?.display_name || "someone")}</strong> ${hostYear}
          </span>
          <span>👥 ${a.participant_count}/${a.capacity} adventurers</span>
        </div>
        <div class="tag-row">${tags}</div>
        ${rec}
        <div class="card-actions">
          <button type="button" class="btn btn-ghost" data-open-detail="${a.id}">details</button>
          <button type="button" class="btn btn-primary" data-join="${a.id}" ${joinDisabled ? "disabled" : ""}>${joinLabel}</button>
        </div>
      </article>`;
  }

  function renderCreateCard() {
    return `
      <button type="button" class="quest-card create-card" data-nav="create" aria-label="Create a quest">
        <span class="deco" aria-hidden="true">＋</span>
        <h3>create a quest</h3>
        <p class="desc">got a silly plan? the campus noticeboard hungers.</p>
      </button>`;
  }

  async function loadDiscover() {
    renderStatus(loadingBubble());
    els.grid.innerHTML = "";
    try {
      const params = new URLSearchParams();
      if (state.category && state.category !== "All") {
        params.set("category", state.category);
      }
      if (state.intention && state.intention !== "all") {
        params.set("intention", state.intention);
      }
      const data = await api(`/api/activities?${params.toString()}`);
      state.activities = data.activities || [];

      if (!state.activities.length) {
        renderStatus(
          emptyBubble(
            "well, this is awkward. even the pigeons are busy rn.",
            "make the first quest ✿",
            "create"
          )
        );
        els.grid.innerHTML = renderCreateCard();
        return;
      }

      renderStatus("");
      els.grid.innerHTML =
        renderCreateCard() +
        state.activities.map((a) => renderQuestCard(a)).join("");
    } catch (e) {
      renderStatus(`
        <div class="dialogue-panel error">
          <div aria-hidden="true">☁</div>
          <div class="bubble">
            <p>well. that wasn't supposed to happen. your quest is temporarily haunted.</p>
            <button type="button" class="btn btn-primary" id="retry-discover">retry →</button>
          </div>
        </div>`);
      $("#retry-discover")?.addEventListener("click", () => loadDiscover());
    }
  }

  async function loadDetail(id) {
    state.detailId = id;
    els.detail.innerHTML = loadingBubble();
    try {
      const a = await api(`/api/activities/${id}`);
      const tags = (a.interest_tags || [])
        .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
        .join("");

      const attendees = (a.participants || [])
        .map((p) => {
          const badge = p.badge_label || p.study_year_label;
          const yr = badge ? `<span class="badge-year" style="font-size:0.65rem; padding:0.05rem 0.35rem">${escapeHtml(badge)}</span>` : "";
          const pInterests = (p.interests || []).slice(0, 3).map(i => `<span class="tag" style="font-size:0.7rem; padding:0.1rem 0.4rem">#${escapeHtml(i)}</span>`).join(" ");
          const bioHtml = p.bio ? `<p style="font-size:0.78rem; line-height:1.3; color:var(--ink); margin:0.35rem 0">${escapeHtml(p.bio)}</p>` : "";
          const firstName = escapeHtml(p.first_name || p.display_name);

          return `
            <div class="attendee-chip-wrap" tabindex="0">
              <a href="/user/${p.id}" class="attendee-chip" title="Click to view full student profile">
                ${renderAvatar(p, "")}
                <span>${firstName}</span>
                ${yr}
              </a>
              <div class="attendee-card-popover" role="tooltip">
                <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.35rem">
                  ${renderAvatar(p, "")}
                  <div>
                    <strong style="font-size:0.88rem; display:block">${escapeHtml(p.display_name)}</strong>
                    ${yr}
                  </div>
                </div>
                ${bioHtml}
                ${pInterests ? `<div style="display:flex; flex-wrap:wrap; gap:0.25rem; margin-top:0.35rem">${pInterests}</div>` : ""}
                <div style="margin-top:0.5rem; text-align:right">
                  <a href="/user/${p.id}" style="font-size:0.75rem; font-weight:700; color:var(--ink); text-decoration:underline">view profile ✿</a>
                </div>
              </div>
            </div>`;
        })
        .join("");

      const ice = a.icebreaker?.prompt || "say hi and ask what brought them here.";
      const isRestricted = a.invite_policy && a.invite_policy !== "everyone";
      const guestBadge = isRestricted
        ? `<span class="badge-eligibility restricted">🔒 ${escapeHtml(a.invite_label || "Guest list restricted")}</span>`
        : `<span class="badge-eligibility">👥 Everyone welcome</span>`;

      let joinBtn = "";
      if (a.joined) {
        joinBtn = `<button type="button" class="btn btn-danger" data-leave="${a.id}">leave quest</button>`;
      } else if (a.eligible === false) {
        joinBtn = `<button type="button" class="btn" disabled>restricted guest list 🔒</button>`;
      } else if (a.is_full) {
        joinBtn = `<button type="button" class="btn" disabled>quest is full</button>`;
      } else {
        joinBtn = `<button type="button" class="btn btn-primary" data-join="${a.id}">join this quest ✿</button>`;
      }

      const rec = a.recommendation?.explanation
        ? `<p class="rec-note" style="margin:0.5rem 0">${escapeHtml(a.recommendation.explanation)}</p>`
        : "";

      const ineligibleNote = a.eligible === false
        ? `<div class="dialogue-panel warn" style="margin:0.75rem 0">
             <div aria-hidden="true">🔒</div>
             <div class="bubble"><p><strong>Guest list note:</strong> ${escapeHtml(a.eligibility_message || "This quest has guest list restrictions.")}</p></div>
           </div>`
        : "";

      const hostYearBadge = a.host?.study_year_label
        ? `<span class="badge-year">${escapeHtml(a.host.study_year_label)}</span>`
        : "";

      els.detail.innerHTML = `
        <button type="button" class="btn btn-ghost" data-nav="discover" style="margin-bottom:0.8rem">← back to discover</button>
        <article class="detail-card ${cardStyle(a.id).pastel}">
          <div class="quest-meta">
            <span class="badge">${escapeHtml(a.category)}</span>
            <span class="badge badge-${escapeHtml(a.connection_type)}">${escapeHtml(intentionLabel(a.connection_type))}</span>
            ${guestBadge}
          </div>
          <h1>${escapeHtml(a.title)}</h1>
          <p style="font-size:1.05rem; line-height:1.45">${escapeHtml(a.description)}</p>

          <div class="quest-facts" style="margin:1rem 0">
            <span>🗓 ${escapeHtml(formatWhen(a.starts_at))}${a.ends_at ? ` → ${escapeHtml(formatWhen(a.ends_at))}` : ""}</span>
            <span>📍 ${escapeHtml(a.venue)}</span>
            <span style="display:flex; align-items:center; gap:0.4rem">
              ${renderAvatar(a.host, "")} hosted by <strong>${escapeHtml(a.host?.display_name || "someone")}</strong> ${hostYearBadge}
            </span>
            <span>👥 ${a.participant_count}/${a.capacity} spots filled · ${a.spots_left} spots left</span>
          </div>

          <div class="tag-row" style="margin-top:0.6rem">${tags}</div>
          ${rec}

          <div class="icebreaker" role="note">
            <strong>shared-interest icebreaker:</strong> "${escapeHtml(ice)}"
          </div>

          ${ineligibleNote}

          <h3>who's coming (${a.participant_count}/${a.capacity})</h3>
          <div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin:0.75rem 0">${attendees || "<span class='muted'>nobody yet — brave first?</span>"}</div>

          <div class="safety-notice">
            <p>🛡️ <strong>Prototype note:</strong> Basic eligibility logic is active. Real-user dating features would require additional age verification, affirmative consent gates, and active community moderation safeguards before campus deployment.</p>
          </div>

          <div class="card-actions" style="margin-top:1.25rem; display:flex; justify-content:space-between; align-items:center">
            <div>${joinBtn}</div>
            <button type="button" class="btn btn-ghost" style="color:var(--muted-ink); font-size:0.85rem" data-report-act="${a.id}">report quest</button>
          </div>
        </article>`;
    } catch {
      els.detail.innerHTML = `
        <div class="dialogue-panel error">
          <div class="bubble">
            <p>this quest seems to have dematerialized.</p>
            <button type="button" class="btn btn-primary" data-nav="discover">back to discover</button>
          </div>
        </div>`;
    }
  }

  async function joinActivity(id) {
    try {
      const data = await api(`/api/activities/${id}/join`, { method: "POST" });
      await showModal({
        message: "IT'S OFFICIAL!! you've joined the quest 🎉 go forth and acquire new lore.",
        primary: { label: "let's go →", value: true },
        variant: "success",
      });
      toast("quest joined 🎉");
      if (state.view === "detail") await loadDetail(id);
      else if (state.view === "discover") await loadDiscover();
      else if (state.view === "my-quests") await loadMyQuests();
      return data;
    } catch (e) {
      const reason = e.data?.error;
      if (reason === "full") {
        await showModal({
          message:
            e.data?.message ||
            "nooo, this quest is packed. the plot demands another adventure.",
          primary: { label: "find another ✿", value: true },
          variant: "warn",
        });
      } else if (reason === "ineligible") {
        await showModal({
          message: e.data?.message || "you're not on this quest's guest list.",
          primary: { label: "understood", value: true },
          variant: "warn",
        });
      } else if (reason === "already_joined") {
        toast("you're already in!", "warn");
      } else {
        toast(e.data?.message || "join failed", "error");
      }
      if (state.view === "discover") await loadDiscover();
      if (state.view === "detail") await loadDetail(id);
    }
  }

  async function leaveActivity(id) {
    const ok = await showModal({
      message: "backing out of this adventure?",
      primary: { label: "leave quest", value: true },
      secondary: { label: "stay for the plot", value: false },
      variant: "warn",
    });
    if (!ok) return;
    try {
      await api(`/api/activities/${id}/join`, { method: "DELETE" });
      toast("left the quest");
      if (state.view === "detail") await loadDetail(id);
      else if (state.view === "my-quests") await loadMyQuests();
      else await loadDiscover();
    } catch (e) {
      toast(e.data?.message || "couldn't leave", "error");
    }
  }

  function prepareCreateForm() {
    const dateInput = $("#f-date");
    if (dateInput && !dateInput.value) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      dateInput.value = tomorrow.toISOString().slice(0, 10);
    }
    const inviteSelect = $("#f-invite");
    const customWrap = $("#custom-genders-wrap");
    if (inviteSelect && customWrap) {
      customWrap.classList.toggle("hidden", inviteSelect.value !== "custom");
    }
    clearFormErrors();
  }

  function clearFormErrors() {
    $$(".field-error").forEach((el) => {
      el.hidden = true;
      el.textContent = "";
    });
  }

  function showFormErrors(fields) {
    clearFormErrors();
    Object.entries(fields || {}).forEach(([key, msg]) => {
      const el = $(`.field-error[data-for="${key}"]`);
      if (el) {
        el.textContent = msg;
        el.hidden = false;
      }
    });
  }

  async function submitCreate(e) {
    e.preventDefault();
    clearFormErrors();
    const fd = new FormData(els.createForm);
    const tags = String(fd.get("tags") || "")
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const invitePolicy = fd.get("invite_policy") || "everyone";
    const customGenders = $$('input[name="invite_gender"]:checked').map(cb => cb.value);

    const payload = {
      title: fd.get("title"),
      description: fd.get("description"),
      category: fd.get("category"),
      connection_type: fd.get("connection_type"),
      invite_policy: invitePolicy,
      invite_genders: invitePolicy === "custom" ? customGenders : [],
      date: fd.get("date"),
      start_time: fd.get("start_time"),
      end_time: fd.get("end_time") || "",
      venue: fd.get("venue"),
      capacity: Number(fd.get("capacity")),
      interest_tags: tags,
    };

    // Client validation
    const local = {};
    if (!payload.title?.trim()) {
      local.title = "tiny plot twist: we need a title before this quest can exist.";
    }
    if (!payload.date || !payload.start_time) {
      local.starts_at = "date and start time are required.";
    }
    if (invitePolicy === "custom" && !customGenders.length) {
      local.invite_policy = "custom guest list needs at least one gender selected.";
    }
    if (Object.keys(local).length) {
      showFormErrors(local);
      return;
    }

    try {
      const activity = await api("/api/activities", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      els.createForm.reset();
      await showModal({
        message: "YOUR QUEST HAS ENTERED THE WORLD. may the vibes be immaculate.",
        primary: { label: "show me →", value: true },
        variant: "success",
      });
      navigate("detail", { id: activity.id });
    } catch (err) {
      if (err.data?.fields) {
        showFormErrors(err.data.fields);
        const first = Object.values(err.data.fields)[0];
        toast(first, "warn");
      } else {
        toast(err.message || "could not create quest", "error");
      }
    }
  }

  async function loadMyQuests() {
    els.myContent.innerHTML = loadingBubble();
    try {
      const data = await api("/api/my-quests");
      const section = (title, items, emptyMsg) => {
        if (!items.length) {
          return `
            <section class="quest-section">
              <h2>${escapeHtml(title)}</h2>
              <div class="dialogue-panel">
                <div class="bubble"><p>${escapeHtml(emptyMsg)}</p></div>
              </div>
            </section>`;
        }
        return `
          <section class="quest-section">
            <h2>${escapeHtml(title)}</h2>
            <div class="quest-list">
              ${items
                .map((a) => {
                  const leave =
                    a.joined && !a.is_host
                      ? `<button type="button" class="btn btn-danger" data-leave="${a.id}">leave</button>`
                      : "";
                  return `
                    <article class="quest-card ${cardStyle(a.id).pastel}">
                      <div class="quest-meta">
                        <span class="badge">${escapeHtml(a.category)}</span>
                        ${a.is_host ? '<span class="badge" style="background:var(--butter)">hosted by you</span>' : ""}
                        <span class="badge badge-${escapeHtml(a.connection_type)}">${escapeHtml(intentionLabel(a.connection_type))}</span>
                      </div>
                      <h3>${escapeHtml(a.title)}</h3>
                      <div class="quest-facts">
                        <span>🗓 ${escapeHtml(formatWhen(a.starts_at))}</span>
                        <span>📍 ${escapeHtml(a.venue)}</span>
                        <span>👥 ${a.participant_count}/${a.capacity} spots</span>
                      </div>
                      <div class="card-actions">
                        <button type="button" class="btn btn-ghost" data-open-detail="${a.id}">details</button>
                        ${leave}
                      </div>
                    </article>`;
                })
                .join("")}
            </div>
          </section>`;
      };

      const emptyAll =
        !data.coming_up.length && !data.hosted.length && !data.past.length;
      if (emptyAll) {
        els.myContent.innerHTML = emptyBubble(
          "your quest log is blank — the campus awaits.",
          "discover quests ✿",
          "discover"
        );
        return;
      }

      els.myContent.innerHTML =
        section("Coming up", data.coming_up, "nothing on the horizon yet.") +
        section("Hosted by me", data.hosted, "you haven't hosted a quest yet.") +
        section(
          "Past adventures",
          data.past,
          "no past adventures yet — go make some lore."
        );
    } catch {
      els.myContent.innerHTML = `
        <div class="dialogue-panel error">
          <div class="bubble">
            <p>couldn't load your quest log. haunted, probably.</p>
            <button type="button" class="btn btn-primary" id="retry-my">retry →</button>
          </div>
        </div>`;
      $("#retry-my")?.addEventListener("click", () => loadMyQuests());
    }
  }

  async function loadProfile() {
    els.profileContent.innerHTML = loadingBubble();
    try {
      state.me = await api("/api/me");
      const me = state.me;
      const interests = (me.interests || [])
        .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
        .join("");

      const badgeText = me.badge_label || me.study_year_label;
      const yearInfo = badgeText
        ? `<span class="badge-year" style="font-size:0.9rem; padding:0.25rem 0.75rem">${escapeHtml(badgeText)}</span>`
        : `<span class="badge" style="background:#eee">Student</span>`;

      const avatarChoices = Object.keys(MASCOTS)
        .map(
          (k) => `
            <button type="button" class="avatar-choice ${me.default_avatar === k && !me.avatar_url ? 'active' : ''}" data-pick-avatar="${k}" title="Choose ${k}">
              ${MASCOTS[k]}
            </button>`
        )
        .join("");

      const removeAvatarBtn = me.avatar_url
        ? `<button type="button" class="btn btn-ghost" id="btn-remove-avatar" style="font-size:0.82rem">remove photo</button>`
        : "";

      const cats = ["Coffee", "Games", "Music", "Study", "Outdoors", "Creative", "Tech", "Food"];
      const prefCats = me.preferred_categories || [];
      const catCheckboxes = cats.map(c => `
        <label class="category-choice ${prefCats.includes(c) ? 'selected' : ''}">
          <input type="checkbox" name="pref_cat" value="${c}" ${prefCats.includes(c) ? 'checked' : ''} />
          ${CAT_DECO[c] || '✦'} ${c}
        </label>
      `).join("");

      els.profileContent.innerHTML = `
        <div class="paper-card profile-card">
          <div style="display:flex; flex-wrap:wrap; align-items:center; gap:1.25rem">
            <div style="position:relative">
              ${renderAvatar(me, "avatar-large")}
            </div>
            <div style="flex:1; min-width:200px">
              <div style="display:flex; flex-wrap:wrap; align-items:center; gap:0.5rem">
                <h2 style="margin:0">${escapeHtml(me.display_name)}</h2>
                ${yearInfo}
              </div>
              <p style="margin:0.25rem 0 0; color:var(--muted-ink); font-size:0.9rem">${escapeHtml(me.email || '')}</p>
              <div style="margin-top:0.4rem">
                <a href="/user/${me.id}" class="btn btn-ghost" style="padding:0.25rem 0.6rem; font-size:0.8rem">view public profile page →</a>
              </div>
            </div>
          </div>

          <!-- Avatar management -->
          <div style="background:rgba(255,255,255,0.7); border:2px dashed var(--border); border-radius:18px; padding:1rem">
            <h3 style="font-size:1rem; margin-bottom:0.4rem">profile picture & mascots</h3>
            <p class="helper">Upload a photo (JPEG, PNG, WebP up to 5MB) or choose an illustrated mascot:</p>
            <div style="display:flex; flex-wrap:wrap; align-items:center; gap:0.75rem; margin-top:0.6rem">
              <input type="file" id="input-avatar-file" accept=".jpg,.jpeg,.png,.webp" style="display:none" />
              <button type="button" class="btn btn-mint" id="btn-upload-avatar" style="font-size:0.85rem">upload photo 📷</button>
              ${removeAvatarBtn}
            </div>
            <div style="margin-top:0.8rem">
              <span class="helper" style="display:block; margin-bottom:0.3rem">or pick a default mascot:</span>
              <div class="avatar-picker">${avatarChoices}</div>
            </div>
          </div>

          <div class="stats-row">
            <div class="stat"><strong>${me.joined_count}</strong>joined</div>
            <div class="stat"><strong>${me.hosted_count}</strong>hosted</div>
            <div class="stat"><strong>${escapeHtml(intentionLabel(me.connection_preference))}</strong>vibe</div>
          </div>

          <div>
            <h3>interests</h3>
            <div class="tag-row">${interests || '<span class="muted">no interests listed yet</span>'}</div>
          </div>

          <!-- Edit Profile Form -->
          <form id="profile-form" class="profile-form">
            <h3 style="font-size:1.15rem; margin-top:0.5rem">edit preferences</h3>
            <div class="field">
              <label for="p-name">display name</label>
              <input id="p-name" name="display_name" value="${escapeHtml(me.display_name)}" maxlength="40" required />
            </div>
            <div class="field">
              <label for="p-bio">bio</label>
              <textarea id="p-bio" name="bio" rows="2" maxlength="280">${escapeHtml(me.bio || '')}</textarea>
            </div>
            <div class="field">
              <label for="p-vis">profile visibility on quests</label>
              <select id="p-vis" name="profile_visibility">
                <option value="public" ${me.profile_visibility === "public" ? "selected" : ""}>Public (Full name, bio, and interests shown)</option>
                <option value="first_name_only" ${me.profile_visibility === "first_name_only" ? "selected" : ""}>First Name Only (Privacy-first badge)</option>
                <option value="minimal" ${me.profile_visibility === "minimal" ? "selected" : ""}>Minimal (Avatar & first name only)</option>
              </select>
              <p class="helper">Controls how your details appear to other students on quests and attendee hover tooltips.</p>
            </div>
            <div class="field-row" style="grid-template-columns:1fr 1fr">
              <div class="field">
                <label for="p-gender">gender <span class="optional">(optional)</span></label>
                <select id="p-gender" name="gender">
                  <option value="prefer_not_to_say" ${me.gender === "prefer_not_to_say" ? "selected" : ""}>Prefer not to say</option>
                  <option value="woman" ${me.gender === "woman" ? "selected" : ""}>Woman</option>
                  <option value="man" ${me.gender === "man" ? "selected" : ""}>Man</option>
                  <option value="non_binary" ${me.gender === "non_binary" ? "selected" : ""}>Non-binary</option>
                  <option value="self_describe" ${me.gender === "self_describe" ? "selected" : ""}>Self-describe...</option>
                </select>
                <p class="helper">Used only for quest guest list eligibility checks. Never public.</p>
              </div>
              <div class="field">
                <label for="p-pref">preferred connection vibe</label>
                <select id="p-pref" name="connection_preference">
                  <option value="either" ${me.connection_preference === "either" ? "selected" : ""}>Either / open</option>
                  <option value="friends" ${me.connection_preference === "friends" ? "selected" : ""}>Friendship</option>
                  <option value="dating" ${me.connection_preference === "dating" ? "selected" : ""}>Dating</option>
                </select>
              </div>
            </div>

            <div class="field ${me.gender === 'self_describe' ? '' : 'hidden'}" id="p-gender-self-wrap">
              <label for="p-gender-self">self-described gender</label>
              <input id="p-gender-self" name="gender_self_describe" value="${escapeHtml(me.gender_self_describe || '')}" />
            </div>

            <div class="field">
              <label>favorite categories (used for recommendations)</label>
              <div class="category-picker">${catCheckboxes}</div>
            </div>

            <div class="field">
              <label for="p-interests">interests (comma separated)</label>
              <input id="p-interests" name="interests" value="${escapeHtml((me.interests || []).join(", "))}" />
            </div>
            <button type="submit" class="btn btn-primary" style="margin-top:0.5rem">save profile ✿</button>
          </form>
        </div>`;

      // Profile events
      $("#profile-form")?.addEventListener("submit", saveProfile);

      $("#p-gender")?.addEventListener("change", (e) => {
        $("#p-gender-self-wrap")?.classList.toggle("hidden", e.target.value !== "self_describe");
      });

      $$(".category-choice").forEach((label) => {
        label.addEventListener("click", () => {
          const cb = $("input", label);
          label.classList.toggle("selected", cb.checked);
        });
      });

      $$("[data-pick-avatar]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const mascot = btn.dataset.pickAvatar;
          try {
            state.me = await api("/api/me", {
              method: "PATCH",
              body: JSON.stringify({ default_avatar: mascot, clear_avatar: true }),
            });
            toast("mascot updated ✿");
            updateNavUser();
            await loadProfile();
          } catch (e) {
            toast(e.message, "error");
          }
        });
      });

      $("#btn-upload-avatar")?.addEventListener("click", () => {
        $("#input-avatar-file")?.click();
      });

      $("#input-avatar-file")?.addEventListener("change", async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) {
          toast("file is too large (max 5 MB)", "error");
          return;
        }
        const formData = new FormData();
        formData.append("avatar", file);
        try {
          toast("uploading picture...");
          state.me = await api("/api/me/avatar", {
            method: "POST",
            body: formData,
          });
          toast("photo uploaded successfully ✦");
          updateNavUser();
          await loadProfile();
        } catch (err) {
          toast(err.data?.error || err.message || "upload failed", "error");
        }
      });

      $("#btn-remove-avatar")?.addEventListener("click", async () => {
        try {
          state.me = await api("/api/me/avatar", { method: "DELETE" });
          toast("photo removed");
          updateNavUser();
          await loadProfile();
        } catch (err) {
          toast(err.message, "error");
        }
      });
    } catch {
      els.profileContent.innerHTML = `<div class="dialogue-panel error"><div class="bubble"><p>profile went on a side quest of its own.</p></div></div>`;
    }
  }

  async function saveProfile(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const selectedCats = $$('input[name="pref_cat"]:checked').map(cb => cb.value);
    const payload = {
      display_name: fd.get("display_name"),
      bio: fd.get("bio"),
      gender: fd.get("gender"),
      gender_self_describe: fd.get("gender_self_describe") || "",
      connection_preference: fd.get("connection_preference"),
      profile_visibility: fd.get("profile_visibility") || "public",
      preferred_categories: selectedCats,
      interests: String(fd.get("interests") || "")
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };
    try {
      state.me = await api("/api/me", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      toast("profile saved ✿");
      updateNavUser();
      await loadProfile();
    } catch (err) {
      toast(err.data?.error || "couldn't save", "error");
    }
  }

  // Auth operations
  async function handleDemoLogin(email = null) {
    try {
      const body = email ? JSON.stringify({ email }) : "{}";
      const data = await api("/api/auth/demo", {
        method: "POST",
        body,
      });
      state.me = data.user;
      toast(`welcome, ${state.me.display_name}! (demo student mode)`);
      updateNavUser();
      navigate("discover");
    } catch (err) {
      toast(err.data?.error || "demo login failed", "error");
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const email = fd.get("email");
    const password = fd.get("password");
    $("#login-general-error").hidden = true;
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      state.me = data.user;
      toast(`welcome back, ${state.me.display_name}! ✿`);
      updateNavUser();
      navigate("discover");
    } catch (err) {
      $("#login-general-error").textContent = err.data?.error || err.message || "login failed";
      $("#login-general-error").hidden = false;
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const interests = String(fd.get("interests") || "")
      .split(",")
      .map(t => t.trim())
      .filter(Boolean);

    const payload = {
      email: fd.get("email"),
      password: fd.get("password"),
      display_name: fd.get("display_name"),
      gender: fd.get("gender"),
      gender_self_describe: fd.get("gender_self_describe") || "",
      connection_preference: fd.get("connection_preference"),
      profile_visibility: fd.get("profile_visibility") || "public",
      interests,
    };

    $$("[data-reg-error]").forEach(el => { el.hidden = true; el.textContent = ""; });
    $("#register-general-error").hidden = true;

    try {
      const data = await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.me = data.user;
      toast(`welcome to SideQuest, ${state.me.display_name}! ✿`);
      const userBadge = data.study_year?.badge_label || data.study_year?.study_year_label || "First Year";
      await showModal({
        message: `welcome aboard! email verification is simulated in this demo. your student badge is ${userBadge} ✿`,
        primary: { label: "start exploring ✦", value: true },
        variant: "success",
      });
      updateNavUser();
      navigate("discover");
    } catch (err) {
      if (err.data?.fields) {
        Object.entries(err.data.fields).forEach(([k, msg]) => {
          const el = $(`[data-reg-error="${k}"]`);
          if (el) {
            el.textContent = msg;
            el.hidden = false;
          }
        });
      } else {
        $("#register-general-error").textContent = err.data?.error || err.message || "registration failed";
        $("#register-general-error").hidden = false;
      }
    }
  }

  async function handleLogout() {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch (_) {}
    state.me = null;
    toast("logged out! see you on the next quest ✿");
    updateNavUser();
    navigate("landing");
  }

  // Report handling
  function openReportModal(activityId) {
    state.reportingId = activityId;
    els.reportReason.value = "";
    els.reportModal.classList.remove("hidden");
  }

  function closeReportModal() {
    state.reportingId = null;
    els.reportModal.classList.add("hidden");
  }

  async function submitReport() {
    const reason = els.reportReason.value.trim();
    if (!reason || reason.length < 5) {
      toast("please write a bit more detail (min 5 characters)", "warn");
      return;
    }
    try {
      await api(`/api/activities/${state.reportingId}/report`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      closeReportModal();
      toast("thank you. campus moderators have been notified.", "ok");
    } catch (err) {
      toast(err.data?.error || "report submission failed", "error");
    }
  }

  function bindGlobal() {
    document.body.addEventListener("click", (e) => {
      const nav = e.target.closest("[data-nav]");
      if (nav) {
        e.preventDefault();
        navigate(nav.dataset.nav);
        return;
      }
      const demoBtn = e.target.closest("[data-demo-email]");
      if (demoBtn) {
        e.preventDefault();
        handleDemoLogin(demoBtn.dataset.demoEmail);
        return;
      }
      const open = e.target.closest("[data-open-detail]");
      if (open) {
        navigate("detail", { id: Number(open.dataset.openDetail) });
        return;
      }
      const join = e.target.closest("[data-join]");
      if (join) {
        joinActivity(Number(join.dataset.join));
        return;
      }
      const leave = e.target.closest("[data-leave]");
      if (leave) {
        leaveActivity(Number(leave.dataset.leave));
        return;
      }
      const reportBtn = e.target.closest("[data-report-act]");
      if (reportBtn) {
        openReportModal(Number(reportBtn.dataset.reportAct));
        return;
      }
    });

    // Auth tab switching
    els.tabBtnLogin?.addEventListener("click", () => {
      els.tabBtnLogin.classList.add("active");
      els.tabBtnRegister.classList.remove("active");
      els.loginPane.classList.remove("hidden");
      els.registerPane.classList.add("hidden");
    });
    els.tabBtnRegister?.addEventListener("click", () => {
      els.tabBtnRegister.classList.add("active");
      els.tabBtnLogin.classList.remove("active");
      els.registerPane.classList.remove("hidden");
      els.loginPane.classList.add("hidden");
    });

    $("#r-gender")?.addEventListener("change", (e) => {
      $("#r-gender-self-wrap")?.classList.toggle("hidden", e.target.value !== "self_describe");
    });

    $("#f-invite")?.addEventListener("change", (e) => {
      $("#custom-genders-wrap")?.classList.toggle("hidden", e.target.value !== "custom");
    });

    els.loginForm?.addEventListener("submit", handleLogin);
    els.registerForm?.addEventListener("submit", handleRegister);

    $("#btn-demo-login")?.addEventListener("click", () => handleDemoLogin());
    $("#btn-what-is")?.addEventListener("click", () => {
      $("#what-is")?.scrollIntoView({ behavior: "smooth" });
    });

    $$("[data-category]").forEach((chip) => {
      chip.addEventListener("click", () => {
        state.category = chip.dataset.category;
        $$("[data-category]").forEach((c) => c.classList.toggle("active", c === chip));
        loadDiscover();
      });
    });

    $$("[data-intention]").forEach((chip) => {
      chip.addEventListener("click", () => {
        state.intention = chip.dataset.intention;
        $$("[data-intention]").forEach((c) => c.classList.toggle("active", c === chip));
        loadDiscover();
      });
    });

    els.createForm?.addEventListener("submit", submitCreate);

    // Report modal triggers
    $$("[data-close-report]").forEach((el) => {
      el.addEventListener("click", closeReportModal);
    });
    els.btnSubmitReport?.addEventListener("click", submitReport);
  }

  async function boot() {
    bindGlobal();
    // Check if user is already logged in
    try {
      state.me = await api("/api/me");
      updateNavUser();
      // If query param ?next=admin, redirect to admin
      const params = new URLSearchParams(window.location.search);
      if (params.get("next") === "admin" && state.me?.role === "admin") {
        window.location.href = "/admin";
        return;
      }
    } catch {
      state.me = null;
      updateNavUser();
    }
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
