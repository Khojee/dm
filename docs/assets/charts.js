/* Chart builders. Each returns {data, layout, config} for Plotly.
   All charts respect the global filter state (year + senders). */
"use strict";

const PALETTE = {
  A: "#a78bfa", // first sender (violet)
  B: "#fb7185", // second sender (rose)
  accent: "#e879f9",
  grid: "rgba(255,255,255,0.06)",
  text: "#9d9db1",
};

function senderColor(name) {
  const s = window.APP_STATE;
  return name === s.senders[0] ? PALETTE.A : PALETTE.B;
}

function baseLayout(extra = {}) {
  return Object.assign({
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: PALETTE.text, size: 12 },
    margin: { l: 46, r: 16, t: 10, b: 40 },
    xaxis: { gridcolor: PALETTE.grid, zeroline: false, linecolor: "rgba(255,255,255,0.1)" },
    yaxis: { gridcolor: PALETTE.grid, zeroline: false },
    hoverlabel: {
      bgcolor: "#1b1b2c", bordercolor: "rgba(167,139,250,.4)",
      font: { family: "Inter, sans-serif", color: "#fff", size: 12 },
    },
    showlegend: false,
    dragmode: false,
  }, extra);
}

const PLOTLY_CONFIG = { displayModeBar: false, responsive: true };

/* ── filter helpers ─────────────────────────────────────────── */
function inYear(dateStr) {
  const y = window.APP_STATE.year;
  return y === "all" || dateStr.startsWith(y);
}
function activeSenders() {
  const s = window.APP_STATE;
  return s.senders.filter((n) => s.senderOn[n]);
}

/* ── charts ─────────────────────────────────────────────────── */
const CHARTS = {

  daily(S) {
    const traces = activeSenders().map((name) => {
      const pairs = (S.activity.per_sender_daily[name] || []).filter((p) => inYear(p[0]));
      return {
        x: pairs.map((p) => p[0]), y: pairs.map((p) => p[1]),
        type: "scatter", mode: "lines", name,
        line: { width: 2, color: senderColor(name), shape: "spline", smoothing: 0.6 },
        fill: "tozeroy",
        fillcolor: senderColor(name).replace(")", "") + "22",
        stackgroup: "one",
        hovertemplate: `<b>${name}</b> · %{x}<br>%{y} messages<extra></extra>`,
      };
    });
    return { data: traces, layout: baseLayout({ showlegend: true, legend: { orientation: "h", y: 1.12 } }) };
  },

  cumulative(S) {
    const pairs = S.activity.cumulative.filter((p) => inYear(p[0]));
    const base = pairs.length && window.APP_STATE.year !== "all" ? 0 : 0;
    return {
      data: [{
        x: pairs.map((p) => p[0]), y: pairs.map((p) => p[1] - base),
        type: "scatter", mode: "lines", line: { width: 3, color: PALETTE.accent, shape: "spline" },
        fill: "tozeroy", fillcolor: "rgba(232,121,249,0.09)",
        hovertemplate: "%{x}<br><b>%{y}</b> messages so far<extra></extra>",
      }],
      layout: baseLayout(),
      animateGrow: true,
    };
  },

  monthly(S) {
    const traces = activeSenders().map((name) => {
      const pairs = (S.activity.monthly_by_sender[name] || []).filter((p) => inYear(p[0]));
      return {
        x: pairs.map((p) => p[0]), y: pairs.map((p) => p[1]),
        type: "bar", name, marker: { color: senderColor(name), cornerradius: 6 },
        hovertemplate: `<b>${name}</b> · %{x}<br>%{y} messages<extra></extra>`,
      };
    });
    return { data: traces, layout: baseLayout({ barmode: "group", showlegend: true, legend: { orientation: "h", y: 1.12 }, bargap: 0.25 }) };
  },

  calendar(S) {
    const daily = S.activity.daily.filter((p) => inYear(p[0]));
    if (!daily.length) return null;
    const first = new Date(daily[0][0] + "T00:00:00");
    const weeks = {}; const weekStarts = [];
    const z = [[], [], [], [], [], [], []];
    const start = new Date(first);
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7)); // back to Monday
    const byDate = Object.fromEntries(daily);
    const last = new Date(daily[daily.length - 1][0] + "T00:00:00");
    const custom = [[], [], [], [], [], [], []];
    for (let d = new Date(start); d <= last; d.setDate(d.getDate() + 7)) {
      weekStarts.push(d.toISOString().slice(0, 10));
      for (let wd = 0; wd < 7; wd++) {
        const day = new Date(d); day.setDate(day.getDate() + wd);
        const key = day.toISOString().slice(0, 10);
        z[wd].push(byDate[key] ?? null);
        custom[wd].push(key);
      }
    }
    return {
      data: [{
        z, x: weekStarts, y: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        customdata: custom,
        type: "heatmap", colorscale: [[0, "#131320"], [0.25, "#3b2a70"], [0.6, "#7c3aed"], [1, "#e879f9"]],
        xgap: 3, ygap: 3, showscale: false, hoverongaps: false,
        hovertemplate: "%{customdata}<br><b>%{z}</b> messages<extra></extra>",
      }],
      layout: baseLayout({ yaxis: { autorange: "reversed", gridcolor: "rgba(0,0,0,0)" }, xaxis: { gridcolor: "rgba(0,0,0,0)" } }),
    };
  },

  heatmap(S) {
    return {
      data: [{
        z: S.activity.hour_weekday_heatmap,
        x: [...Array(24).keys()].map((h) => `${h}:00`),
        y: S.activity.weekday_labels,
        type: "heatmap",
        colorscale: [[0, "#131320"], [0.3, "#312e81"], [0.65, "#7c3aed"], [1, "#f0abfc"]],
        xgap: 2, ygap: 2, showscale: false,
        hovertemplate: "%{y} %{x}<br><b>%{z}</b> messages<extra></extra>",
      }],
      layout: baseLayout({ yaxis: { autorange: "reversed", gridcolor: "rgba(0,0,0,0)" }, xaxis: { gridcolor: "rgba(0,0,0,0)", tickvals: [0, 4, 8, 12, 16, 20].map((h) => `${h}:00`) } }),
    };
  },

  clock(S) {
    const theta = [...Array(24).keys()].map((h) => h * 15);
    const traces = activeSenders().map((name) => ({
      r: S.activity.hourly_by_sender[name] || [],
      theta, type: "barpolar", name,
      marker: { color: senderColor(name), opacity: 0.75 },
      hovertemplate: `<b>${name}</b> · %{theta}°/15 h<br>%{r} messages<extra></extra>`,
    }));
    return {
      data: traces,
      layout: baseLayout({
        showlegend: true, legend: { orientation: "h", y: 1.15 },
        polar: {
          bgcolor: "rgba(0,0,0,0)",
          angularaxis: {
            tickvals: [0, 90, 180, 270], ticktext: ["00:00", "06:00", "12:00", "18:00"],
            direction: "clockwise", gridcolor: PALETTE.grid, linecolor: PALETTE.grid,
          },
          radialaxis: { gridcolor: PALETTE.grid, showticklabels: false, linecolor: "rgba(0,0,0,0)" },
        },
        margin: { l: 40, r: 40, t: 30, b: 30 },
      }),
    };
  },

  replydist(S) {
    const d = S.conversation.reply_dist;
    const traces = activeSenders().map((name) => ({
      x: d.labels, y: d.by_sender[name] || [],
      type: "bar", name, marker: { color: senderColor(name), cornerradius: 6 },
      hovertemplate: `<b>${name}</b><br>%{y} replies within %{x}<extra></extra>`,
    }));
    return { data: traces, layout: baseLayout({ barmode: "group", showlegend: true, legend: { orientation: "h", y: 1.12 } }) };
  },

  starters(S) {
    const c = S.conversation;
    const names = window.APP_STATE.senders;
    return {
      data: [
        { x: names.map((n) => c.conversation_starters[n] || 0), y: names, name: "Started",
          type: "bar", orientation: "h", marker: { color: PALETTE.A, cornerradius: 6 },
          hovertemplate: "<b>%{y}</b> started %{x} conversations<extra></extra>" },
        { x: names.map((n) => c.conversation_enders[n] || 0), y: names, name: "Had the last word",
          type: "bar", orientation: "h", marker: { color: PALETTE.accent, cornerradius: 6 },
          hovertemplate: "<b>%{y}</b> ended %{x} conversations<extra></extra>" },
      ],
      layout: baseLayout({ barmode: "group", showlegend: true, legend: { orientation: "h", y: 1.15 }, margin: { l: 90, r: 16, t: 10, b: 40 } }),
    };
  },

  radar(S) {
    const names = window.APP_STATE.senders;
    const axes = ["Volume", "Essay energy", "Emoji love", "Media", "Night owl", "Ignition", "Reply speed"];
    const get = (n) => {
      const total = S.activity.by_sender[n] || 0;
      const other = names.filter((x) => x !== n)[0];
      const totalOther = S.activity.by_sender[other] || 1;
      const words = S.words.avg_message_length_words[n] || 0;
      const wordsO = S.words.avg_message_length_words[other] || 1;
      const emoji = S.emoji.emoji_count_by_sender[n] || 0;
      const emojiO = S.emoji.emoji_count_by_sender[other] || 1;
      const media = S.media.by_sender[n] || 0;
      const mediaO = S.media.by_sender[other] || 1;
      const night = S.activity.night_owl_score[n] || 0;
      const nightO = S.activity.night_owl_score[other] || 1;
      const start = S.conversation.conversation_starters[n] || 0;
      const startO = S.conversation.conversation_starters[other] || 1;
      const spd = S.conversation.response[n] ? 1 / S.conversation.response[n].median_s : 0;
      const spdO = S.conversation.response[other] ? 1 / S.conversation.response[other].median_s : 1e-9;
      const rel = (a, b) => (a + b) > 0 ? a / Math.max(a, b) : 0;
      return [rel(total, totalOther), rel(words, wordsO), rel(emoji, emojiO), rel(media, mediaO),
              rel(night, nightO), rel(start, startO), rel(spd, spdO)].map((v) => Math.round(v * 100));
    };
    const traces = activeSenders().map((name) => ({
      type: "scatterpolar", r: [...get(name), get(name)[0]], theta: [...axes, axes[0]],
      fill: "toself", name, line: { color: senderColor(name), width: 2 },
      fillcolor: senderColor(name) + "26",
      hovertemplate: `<b>${name}</b> · %{theta}: %{r}/100<extra></extra>`,
    }));
    return {
      data: traces,
      layout: baseLayout({
        showlegend: true, legend: { orientation: "h", y: 1.12 },
        polar: {
          bgcolor: "rgba(0,0,0,0)",
          radialaxis: { range: [0, 100], gridcolor: PALETTE.grid, showticklabels: false, linecolor: "rgba(0,0,0,0)" },
          angularaxis: { gridcolor: PALETTE.grid, linecolor: PALETTE.grid },
        },
        margin: { l: 60, r: 60, t: 40, b: 40 },
      }),
    };
  },

  emoji(S) {
    const top = S.emoji.top.slice(0, 12).reverse();
    return {
      data: [{
        x: top.map((t) => t[1]), y: top.map((t) => t[0]),
        type: "bar", orientation: "h",
        marker: {
          color: top.map((_, i) => `rgba(${139 + i * 6},${92 + i * 8},246,0.85)`),
          cornerradius: 8,
        },
        hovertemplate: "%{y} used <b>%{x}</b> times<extra></extra>",
      }],
      layout: baseLayout({ yaxis: { tickfont: { size: 18 }, gridcolor: "rgba(0,0,0,0)" }, margin: { l: 48, r: 16, t: 6, b: 40 } }),
    };
  },

  emojiEvo(S) {
    const evo = S.emoji.evolution;
    const colors = ["#a78bfa", "#fb7185", "#e879f9", "#38bdf8", "#4ade80", "#fbbf24"];
    const traces = Object.entries(evo).map(([em, pairs], i) => ({
      x: pairs.map((p) => p[0]), y: pairs.map((p) => p[1]),
      type: "scatter", mode: "lines+markers", name: em,
      line: { width: 2, color: colors[i % colors.length], shape: "spline" },
      marker: { size: 6 },
      hovertemplate: `${em} · %{x}: <b>%{y}</b><extra></extra>`,
    }));
    return { data: traces, layout: baseLayout({ showlegend: true, legend: { orientation: "h", y: 1.15, font: { size: 15 } } }) };
  },

  words(S) {
    const top = S.words.top_words.slice(0, 14).reverse();
    return {
      data: [{
        x: top.map((t) => t[1]), y: top.map((t) => t[0]),
        type: "bar", orientation: "h",
        marker: { color: "rgba(167,139,250,0.8)", cornerradius: 8 },
        hovertemplate: "“%{y}” — <b>%{x}</b> times<extra></extra>",
      }],
      layout: baseLayout({ margin: { l: 90, r: 16, t: 6, b: 40 }, yaxis: { gridcolor: "rgba(0,0,0,0)" } }),
    };
  },

  bigrams(S) {
    const items = [...S.words.top_bigrams.slice(0, 8), ...S.words.top_trigrams.slice(0, 4)];
    if (!items.length) return null;
    return {
      data: [{
        type: "treemap",
        labels: items.map((t) => t[0]),
        parents: items.map(() => ""),
        values: items.map((t) => t[1]),
        marker: {
          colors: items.map((t) => t[1]),
          colorscale: [[0, "#241f3f"], [0.6, "#6d28d9"], [1, "#d946ef"]],
          cornerradius: 8, line: { color: "#0b0b12", width: 2 },
        },
        textfont: { family: "Inter, sans-serif", color: "#fff", size: 13 },
        hovertemplate: "“%{label}”<br><b>%{value}</b> times<extra></extra>",
      }],
      layout: baseLayout({ margin: { l: 4, r: 4, t: 4, b: 4 } }),
    };
  },

  sentiment(S) {
    const pairs = S.sentiment.weekly.filter((p) => inYear(p[0]));
    return {
      data: [{
        x: pairs.map((p) => p[0]), y: pairs.map((p) => p[1]),
        type: "scatter", mode: "lines+markers",
        line: { width: 2.5, color: "#4ade80", shape: "spline" },
        marker: { size: 6, color: pairs.map((p) => (p[1] >= 0 ? "#4ade80" : "#fb7185")) },
        fill: "tozeroy", fillcolor: "rgba(74,222,128,0.07)",
        hovertemplate: "week of %{x}<br>mood <b>%{y:.2f}</b> (−1…+1)<extra></extra>",
      }],
      layout: baseLayout({ yaxis: { range: [-1.05, 1.05], zeroline: true, zerolinecolor: "rgba(255,255,255,0.15)" } }),
    };
  },

  media(S) {
    const bts = S.media.by_type_sender;
    const labels = [], parents = [], values = [];
    const types = Object.keys(S.media.by_type);
    const pretty = { photo: "📷 Photos", video: "🎬 Videos", voice: "🎙️ Voice", sticker: "🩵 Stickers",
                     gif: "GIFs", file: "📎 Files", share: "🔗 Shares", reel: "🎞️ Reels",
                     thread_share: "🧵 Threads posts", video_note: "📹 Video notes" };
    types.forEach((t) => {
      labels.push(pretty[t] || t); parents.push(""); values.push(0);
    });
    Object.entries(bts).forEach(([key, v]) => {
      const [t, s] = key.split("|");
      labels.push(`${s} (${pretty[t] || t})`); parents.push(pretty[t] || t); values.push(v);
    });
    if (!labels.length) return null;
    return {
      data: [{
        type: "sunburst", labels, parents, values,
        branchvalues: "remainder",
        marker: { colorscale: [[0, "#312e81"], [0.5, "#7c3aed"], [1, "#e879f9"]], line: { color: "#0b0b12", width: 2 } },
        textfont: { family: "Inter, sans-serif", color: "#fff", size: 12 },
        hovertemplate: "%{label}<br><b>%{value}</b> items<extra></extra>",
      }],
      layout: baseLayout({ margin: { l: 4, r: 4, t: 4, b: 4 } }),
    };
  },
};

window.CHARTS = CHARTS;
window.PLOTLY_CONFIG = PLOTLY_CONFIG;
window.PALETTE = PALETTE;
