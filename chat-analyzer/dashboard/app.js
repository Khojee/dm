/* App shell: decryption, unlock flow, rendering, filters, palette. */
"use strict";

window.APP_STATE = { stats: null, senders: [], senderOn: {}, year: "all" };

/* ═══════════ crypto ═══════════ */

const b64ToBytes = (b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));

async function decryptPayload(passphrase) {
  const p = window.__ENCRYPTED_PAYLOAD__;
  const salt = b64ToBytes(p.salt), iv = b64ToBytes(p.iv), ct = b64ToBytes(p.ciphertext);
  const keyMaterial = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: parseInt(p.iterations, 10), hash: "SHA-256" },
    keyMaterial, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  const plainGz = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ct);
  const ds = new DecompressionStream("gzip");
  const stream = new Blob([plainGz]).stream().pipeThrough(ds);
  const json = await new Response(stream).text();
  return JSON.parse(json);
}

/* ═══════════ unlock flow ═══════════ */

const $ = (sel) => document.querySelector(sel);

document.getElementById("unlock-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#passphrase"), card = $("#lock-card"), err = $("#lock-error");
  const label = $("#unlock-label");
  label.textContent = "Decrypting…";
  try {
    const stats = await decryptPayload(input.value);
    label.textContent = "Unlocked ✓";
    sessionStorageSafe("dm_pass", input.value);
    launchDashboard(stats);
  } catch (_) {
    label.textContent = "Unlock";
    err.classList.remove("opacity-0");
    input.classList.add("input-error");
    card.classList.remove("shake"); void card.offsetWidth; card.classList.add("shake");
    input.select();
    setTimeout(() => { err.classList.add("opacity-0"); input.classList.remove("input-error"); }, 2200);
  }
});

function sessionStorageSafe(k, v) { try { sessionStorage.setItem(k, v); } catch (_) {} }

// Auto-unlock within the same tab session
(async () => {
  try {
    const saved = sessionStorage.getItem("dm_pass");
    if (saved) launchDashboard(await decryptPayload(saved));
  } catch (_) {}
})();

function lock() {
  try { sessionStorage.removeItem("dm_pass"); } catch (_) {}
  location.reload();
}

/* ═══════════ dashboard boot ═══════════ */

function launchDashboard(stats) {
  const S = window.APP_STATE;
  S.stats = stats;
  S.senders = [stats.meta.me, stats.meta.friend];
  S.senders.forEach((n) => (S.senderOn[n] = true));

  const lockEl = $("#lockscreen"), dash = $("#dashboard");
  lockEl.style.transition = "opacity .6s, transform .6s";
  lockEl.style.opacity = "0"; lockEl.style.transform = "scale(1.04)";
  setTimeout(() => {
    lockEl.remove();
    dash.classList.remove("hidden");
    requestAnimationFrame(() => dash.classList.remove("opacity-0"));
    renderAll(stats);
  }, 550);
}

/* ═══════════ rendering ═══════════ */

function fmt(n) { return n.toLocaleString("en-US"); }

function renderAll(S) {
  renderHero(S);
  renderFilters(S);
  renderTimeline(S);
  renderInsights(S);
  renderStreakCards(S);
  renderDynamicsCards(S);
  renderSignatureWords(S);
  renderAwards(S);
  renderWrapped(S);
  renderMonthly(S);
  setupReveals();
  setupLazyCharts();
  setupPalette(S);
  setupShortcuts();
}

function renderHero(S) {
  const a = S.activity;
  $("#hero-names").textContent = `${S.meta.me} & ${S.meta.friend}`;
  $("#hero-sub").textContent =
    `${fmt(a.total_messages)} messages · ${a.first_date} → ${a.last_date} · ` +
    `${Object.keys(a.by_platform).length} platforms · ${a.active_days} active days`;

  const cards = [
    { label: "Messages", value: a.total_messages, icon: "💬" },
    { label: "Words written", value: S.words.total_words, icon: "✍️" },
    { label: "Emojis used", value: S.emoji.total_emojis, icon: "😂" },
    { label: "Media shared", value: S.media.total_media, icon: "📸" },
  ];
  $("#hero-stats").innerHTML = cards.map((c) => `
    <div class="stat-card text-center">
      <div class="text-2xl mb-1">${c.icon}</div>
      <div class="count-up text-3xl sm:text-4xl font-extrabold text-white tabular-nums" data-target="${c.value}">0</div>
      <div class="mt-1 text-xs uppercase tracking-wider text-zinc-500">${c.label}</div>
    </div>`).join("");
}

function renderFilters(S) {
  const years = [...new Set(S.activity.daily.map((p) => p[0].slice(0, 4)))];
  const bar = $("#filter-bar");
  let html = `<span class="text-xs text-zinc-500 mr-1">Filter:</span>`;
  html += `<button class="chip active" data-year="all">All time</button>`;
  years.forEach((y) => (html += `<button class="chip" data-year="${y}">${y}</button>`));
  html += `<span class="mx-2 text-zinc-700">|</span>`;
  S.meta && [S.meta.me, S.meta.friend].forEach((n) => {
    html += `<button class="chip active" data-sender="${n}">${n}</button>`;
  });
  bar.innerHTML = html;

  bar.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip"); if (!btn) return;
    const st = window.APP_STATE;
    if (btn.dataset.year) {
      bar.querySelectorAll("[data-year]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      st.year = btn.dataset.year;
    } else if (btn.dataset.sender) {
      const name = btn.dataset.sender;
      const on = !st.senderOn[name];
      // never allow zero senders
      if (!on && Object.values(st.senderOn).filter(Boolean).length === 1) return;
      st.senderOn[name] = on;
      btn.classList.toggle("active", on);
    }
    rerenderCharts();
  });
}

function renderTimeline(S) {
  const el = $("#timeline-list");
  el.innerHTML = `<div class="tl-line"></div>` + S.timeline.map((e) => `
    <div class="tl-item reveal">
      <div class="tl-dot">${e.icon}</div>
      <div class="text-xs font-medium text-brand-400 mb-0.5">${e.date}</div>
      <div class="font-semibold text-white">${e.title}</div>
      <div class="text-sm text-zinc-400 mt-0.5">${escapeHtml(e.detail)}</div>
    </div>`).join("");
}

function renderInsights(S) {
  $("#insights-grid").innerHTML = S.insights.map((i) => `
    <div class="card reveal">
      <div class="flex items-start gap-3">
        <div class="text-2xl">${i.icon}</div>
        <div>
          <div class="font-semibold text-white text-sm">${escapeHtml(i.title)}</div>
          <p class="mt-1 text-sm text-zinc-400 leading-relaxed">${escapeHtml(i.text)}</p>
        </div>
      </div>
    </div>`).join("");
}

function renderStreakCards(S) {
  const a = S.activity;
  const inact = a.inactive_periods[0];
  const cards = [
    { icon: "🔥", title: "Longest streak", big: `${a.longest_streak_days} days`,
      sub: a.longest_streak_range ? `${a.longest_streak_range[0]} → ${a.longest_streak_range[1]}` : "" },
    { icon: "🏔️", title: "Biggest day", big: `${fmt(a.busiest_day.count)} msgs`, sub: a.busiest_day.date },
    { icon: "🌵", title: "Longest quiet spell", big: inact ? `${inact.days} days` : "0 days",
      sub: inact ? `${inact.from} → ${inact.to}` : "never went quiet" },
  ];
  $("#streak-cards").innerHTML = cards.map((c) => `
    <div class="card reveal text-center">
      <div class="text-2xl">${c.icon}</div>
      <div class="mt-2 text-2xl font-extrabold text-white">${c.big}</div>
      <div class="text-xs uppercase tracking-wider text-zinc-500 mt-1">${c.title}</div>
      <div class="text-xs text-zinc-600 mt-1">${c.sub}</div>
    </div>`).join("");
}

function renderDynamicsCards(S) {
  const c = S.conversation;
  const items = [];
  Object.entries(c.response).forEach(([name, r]) => {
    items.push({ icon: "⏱️", title: `${name}'s median reply`, big: r.median_h, sub: `${r.count} replies measured` });
  });
  if (c.fastest_reply) items.push({ icon: "⚡", title: "Fastest reply ever", big: c.fastest_reply.human, sub: `by ${c.fastest_reply.sender}` });
  if (c.longest_silence) items.push({ icon: "🕊️", title: "Longest silence", big: c.longest_silence.human, sub: `broken by ${c.longest_silence.broken_by}` });
  $("#dynamics-cards").innerHTML = items.slice(0, 4).map((i) => `
    <div class="card reveal text-center">
      <div class="text-2xl">${i.icon}</div>
      <div class="mt-2 text-2xl font-extrabold text-white">${i.big}</div>
      <div class="text-xs uppercase tracking-wider text-zinc-500 mt-1">${i.title}</div>
      <div class="text-xs text-zinc-600 mt-1">${i.sub}</div>
    </div>`).join("");
}

function renderSignatureWords(S) {
  const tfidf = S.words.tfidf_by_sender || {};
  $("#signature-words").innerHTML = Object.entries(tfidf).map(([name, words]) => `
    <div class="card reveal">
      <h3 class="card-title">${name}'s signature vocabulary</h3>
      <div class="flex flex-wrap gap-2">
        ${words.map(([w]) => `<span class="chip" style="cursor:default">${escapeHtml(w)}</span>`).join("")}
      </div>
      <p class="mt-3 text-xs text-zinc-600">Words distinctively used by ${name} (TF-IDF).</p>
    </div>`).join("");
}

function renderAwards(S) {
  $("#awards-grid").innerHTML = S.awards.map((a, i) => `
    <div class="award reveal" style="transition-delay:${(i % 6) * 60}ms">
      <div class="text-3xl">${a.icon}</div>
      <div class="mt-3 text-lg font-bold text-white">${escapeHtml(a.title)}</div>
      <div class="mt-1 text-sm font-semibold bg-gradient-to-r from-brand-300 to-fuchsia-300 bg-clip-text text-transparent">${escapeHtml(a.winner)}</div>
      <div class="mt-2 text-xs text-zinc-500">${escapeHtml(a.evidence)}</div>
    </div>`).join("");
}

function renderWrapped(S) {
  $("#wrapped-cards").innerHTML = S.recap.map((r) => {
    const senders = Object.entries(r.by_sender).map(([n, c]) => `${n}: ${fmt(c)}`).join(" · ");
    const plats = Object.entries(r.platforms).map(([p, c]) => `${p} ${c}`).join(" · ");
    return `
    <div class="wrapped reveal">
      <div class="text-sm font-semibold uppercase tracking-[0.2em] text-brand-300">${r.year} Wrapped</div>
      <div class="mt-4 flex items-end gap-3">
        <span class="count-up text-6xl font-black text-white tabular-nums" data-target="${r.messages}">0</span>
        <span class="pb-2 text-zinc-400 text-sm">messages</span>
      </div>
      <div class="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div><div class="text-zinc-500 text-xs">Words</div><div class="text-white font-semibold">${fmt(r.words)}</div></div>
        <div><div class="text-zinc-500 text-xs">Active days</div><div class="text-white font-semibold">${r.active_days}</div></div>
        <div><div class="text-zinc-500 text-xs">Top emoji</div><div class="text-2xl">${r.top_emojis.join(" ")}</div></div>
        <div><div class="text-zinc-500 text-xs">Favourite hour</div><div class="text-white font-semibold">${r.favorite_hour}:00</div></div>
        <div><div class="text-zinc-500 text-xs">Biggest day</div><div class="text-white font-semibold">${r.busiest_day.date} (${r.busiest_day.count})</div></div>
        <div><div class="text-zinc-500 text-xs">Media</div><div class="text-white font-semibold">${fmt(r.media_sent)}</div></div>
      </div>
      <div class="mt-5 text-xs text-zinc-500">${senders}</div>
      <div class="mt-1 text-xs text-zinc-600">${plats}</div>
    </div>`;
  }).join("");
}

function renderMonthly(S) {
  $("#monthly-cards").innerHTML = S.monthly_summaries.map((m) => `
    <div class="card reveal">
      <div class="flex items-center justify-between">
        <div class="font-bold text-white">${m.label}</div>
        <div class="text-xl">${m.top_emoji || ""}</div>
      </div>
      <div class="mt-3 grid grid-cols-3 gap-2 text-center">
        <div><div class="text-lg font-bold text-white tabular-nums">${fmt(m.messages)}</div><div class="text-[10px] uppercase tracking-wider text-zinc-500">msgs</div></div>
        <div><div class="text-lg font-bold text-white tabular-nums">${fmt(m.words)}</div><div class="text-[10px] uppercase tracking-wider text-zinc-500">words</div></div>
        <div><div class="text-lg font-bold text-white tabular-nums">${m.active_days}</div><div class="text-[10px] uppercase tracking-wider text-zinc-500">days</div></div>
      </div>
      <div class="mt-3 text-xs text-zinc-600">${Object.entries(m.by_sender).map(([n, c]) => `${n} ${c}`).join(" · ")}${m.media ? ` · ${m.media} media` : ""}</div>
    </div>`).join("");
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ═══════════ animations ═══════════ */

function setupReveals() {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) {
        en.target.classList.add("visible");
        en.target.querySelectorAll(".count-up:not(.done)").forEach(animateCount);
        if (en.target.classList.contains("count-up") && !en.target.classList.contains("done")) animateCount(en.target);
        obs.unobserve(en.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((el) => obs.observe(el));
  // hero counters (hero is visible immediately)
  document.querySelectorAll("#hero-stats .count-up").forEach(animateCount);
}

function animateCount(el) {
  if (el.classList.contains("done")) return;
  el.classList.add("done");
  const target = parseInt(el.dataset.target, 10) || 0;
  const dur = 1400, t0 = performance.now();
  const step = (t) => {
    const p = Math.min((t - t0) / dur, 1);
    const eased = 1 - Math.pow(1 - p, 4);
    el.textContent = fmt(Math.round(target * eased));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* ═══════════ charts (lazy) ═══════════ */

const renderedCharts = new Set();

function renderChart(el) {
  const kind = el.dataset.chart;
  const spec = window.CHARTS[kind]?.(window.APP_STATE.stats);
  if (!spec) { el.closest(".card")?.remove(); return; }
  Plotly.react(el, spec.data, spec.layout, window.PLOTLY_CONFIG);
  el.style.opacity = "0";
  el.style.transition = "opacity .8s ease";
  requestAnimationFrame(() => (el.style.opacity = "1"));
  if (spec.animateGrow) animateCumulative(el, spec);
  renderedCharts.add(el);
}

function animateCumulative(el, spec) {
  // Progressive draw of the cumulative line (time-based, guaranteed to finish).
  // Copy the arrays first: Plotly.restyle mutates the trace in place.
  const full = { x: [...spec.data[0].x], y: [...spec.data[0].y] };
  const n = full.x.length;
  if (n < 10) return;
  const dur = 1600, t0 = performance.now();
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    Plotly.restyle(el, { x: [full.x], y: [full.y] }, [0]);
  };
  const tick = (t) => {
    if (done) return;
    const p = Math.min((t - t0) / dur, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    const i = Math.max(2, Math.round(n * eased));
    if (p >= 1) return finish();
    Plotly.restyle(el, { x: [full.x.slice(0, i)], y: [full.y.slice(0, i)] }, [0]);
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  setTimeout(finish, dur + 400); // safety net if rAF is throttled
}

function setupLazyCharts() {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) { renderChart(en.target); obs.unobserve(en.target); }
    });
  }, { rootMargin: "220px" });
  document.querySelectorAll(".chart").forEach((el) => obs.observe(el));
}

function rerenderCharts() {
  renderedCharts.forEach((el) => {
    if (!document.body.contains(el)) return;
    const spec = window.CHARTS[el.dataset.chart]?.(window.APP_STATE.stats);
    if (spec) Plotly.react(el, spec.data, spec.layout, window.PLOTLY_CONFIG);
  });
}

/* ═══════════ command palette & shortcuts ═══════════ */

function setupPalette(S) {
  const palette = $("#palette"), input = $("#palette-input"), results = $("#palette-results");

  const entries = [
    { icon: "📖", label: "The Story So Far", action: () => go("#story") },
    { icon: "🔎", label: "What the Data Says", action: () => go("#insights-section") },
    { icon: "📈", label: "Activity", action: () => go("#activity") },
    { icon: "⚡", label: "Conversation Dynamics", action: () => go("#dynamics") },
    { icon: "🗣️", label: "Language & Emoji", action: () => go("#language") },
    { icon: "🏆", label: "The Awards", action: () => go("#awards") },
    { icon: "🎁", label: "Wrapped", action: () => go("#wrapped") },
    { icon: "🔒", label: "Lock dashboard", action: lock },
  ];
  // searchable facts
  S.awards.forEach((a) => entries.push({
    icon: a.icon, label: `${a.title} — ${a.winner} (${a.evidence})`, action: () => go("#awards"),
  }));
  S.timeline.forEach((e) => entries.push({
    icon: e.icon, label: `${e.title} — ${e.date}`, action: () => go("#story"),
  }));
  S.insights.forEach((i) => entries.push({ icon: i.icon, label: i.title + " — " + i.text, action: () => go("#insights-section") }));

  let filtered = entries, sel = 0;

  function go(hash) { closePalette(); document.querySelector(hash)?.scrollIntoView({ behavior: "smooth" }); }

  function draw() {
    results.innerHTML = filtered.slice(0, 12).map((e, i) => `
      <button class="palette-item ${i === sel ? "selected" : ""}" data-i="${i}">
        <span>${e.icon}</span><span class="truncate">${escapeHtml(e.label)}</span>
      </button>`).join("") ||
      `<div class="px-4 py-6 text-center text-sm text-zinc-500">No results</div>`;
  }

  function openPalette() { palette.classList.remove("hidden"); palette.classList.add("flex"); input.value = ""; filtered = entries; sel = 0; draw(); setTimeout(() => input.focus(), 30); }
  function closePalette() { palette.classList.add("hidden"); palette.classList.remove("flex"); }

  window.__openPalette = openPalette;
  window.__closePalette = closePalette;

  $("#palette-btn").addEventListener("click", openPalette);
  palette.addEventListener("click", (e) => { if (e.target === palette) closePalette(); });
  results.addEventListener("click", (e) => {
    const b = e.target.closest(".palette-item"); if (b) filtered[+b.dataset.i]?.action();
  });
  input.addEventListener("input", () => {
    const q = input.value.toLowerCase();
    filtered = entries.filter((e) => e.label.toLowerCase().includes(q));
    sel = 0; draw();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { sel = Math.min(sel + 1, Math.min(filtered.length, 12) - 1); draw(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); draw(); e.preventDefault(); }
    else if (e.key === "Enter") { filtered[sel]?.action(); }
    else if (e.key === "Escape") { closePalette(); }
  });
}

function setupShortcuts() {
  document.addEventListener("keydown", (e) => {
    const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault(); window.__openPalette?.();
    } else if (!typing && e.key === "/") {
      e.preventDefault(); window.__openPalette?.();
    } else if (!typing && e.key.toLowerCase() === "l") {
      lock();
    } else if (e.key === "Escape") {
      window.__closePalette?.();
    }
  });
}
