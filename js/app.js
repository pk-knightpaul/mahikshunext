// app.js — core UI logic: fetch data, filter/sort client-side, render cards.

import { localStore } from "./storage.js";

const DATA_FILES = ["binance.json", "coingecko.json", "dexscreener.json", "news.json"];
const THEME_KEY = "mahikshu_theme";

const PLATFORM_LABELS = {
  binance: "Binance",
  coingecko: "CoinGecko",
  dexscreener: "DexScreener",
  news: "News",
};

let allItems = [];

// ---------- Data loading ----------

async function loadAllData() {
  const results = await Promise.all(
    DATA_FILES.map(async (file) => {
      try {
        const resp = await fetch(`data/${file}?_=${Date.now()}`, { cache: "no-store" });
        if (!resp.ok) throw new Error(`${file}: HTTP ${resp.status}`);
        const json = await resp.json();
        return Array.isArray(json) ? json : [];
      } catch (err) {
        console.error(`[mahikshu] failed to load ${file}:`, err);
        return [];
      }
    })
  );
  return results.flat();
}

async function loadMeta() {
  try {
    const resp = await fetch(`data/meta.json?_=${Date.now()}`, { cache: "no-store" });
    if (!resp.ok) throw new Error(`meta.json: HTTP ${resp.status}`);
    return await resp.json();
  } catch (err) {
    console.error("[mahikshu] failed to load meta.json:", err);
    return null;
  }
}

// ---------- Filtering & sorting ----------

function withinTimeRange(item, range) {
  const now = Date.now();
  const published = new Date(item.published_at).getTime();
  if (Number.isNaN(published)) return true; // don't hide malformed dates, just pass through
  const diffMs = now - published;
  const HOUR = 3600 * 1000;

  switch (range) {
    case "now":
      return diffMs <= HOUR;
    case "today": {
      const d1 = new Date(published);
      const d2 = new Date(now);
      return d1.toDateString() === d2.toDateString();
    }
    case "24h":
      return diffMs <= 24 * HOUR;
    case "week":
      return diffMs <= 7 * 24 * HOUR;
    case "month":
      return diffMs <= 30 * 24 * HOUR;
    case "all":
    default:
      return true;
  }
}

function applyFiltersAndSort() {
  const platform = document.getElementById("filter-platform").value;
  const timeRange = document.getElementById("filter-time").value;
  const sortBy = document.getElementById("filter-sort").value;

  let filtered = allItems.filter((item) => {
    const platformOk = platform === "all" || item.platform === platform;
    const timeOk = withinTimeRange(item, timeRange);
    return platformOk && timeOk;
  });

  filtered.sort((a, b) => {
    if (sortBy === "engagement") {
      return (b.engagement || 0) - (a.engagement || 0);
    }
    // newest first
    return new Date(b.published_at) - new Date(a.published_at);
  });

  renderCards(filtered);
  updateOpportunityCount(filtered.length);
}

// ---------- Rendering ----------

function timeAgo(isoString) {
  const then = new Date(isoString).getTime();
  if (Number.isNaN(then)) return "";
  const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));

  if (diffSec < 60) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  const diffMonth = Math.floor(diffDay / 30);
  return `${diffMonth}mo ago`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function cardTemplate(item) {
  const platformLabel = PLATFORM_LABELS[item.platform] || item.platform;
  const badgeClass = `badge-${item.platform}`;

  return `
    <article class="card" data-id="${escapeHtml(item.id)}">
      <div class="card-top-row">
        <span class="badge ${badgeClass}">${escapeHtml(platformLabel)}</span>
        <span class="time-ago">${timeAgo(item.published_at)}</span>
      </div>
      <span class="content-type-tag">${escapeHtml(item.content_type)}</span>
      <h3 class="card-title">${escapeHtml(item.title)}</h3>
      <p class="card-summary">${escapeHtml(item.summary)}</p>
      <div class="card-footer">
        <a class="card-link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">
          View source ↗
        </a>
      </div>
    </article>
  `;
}

function renderCards(items) {
  const grid = document.getElementById("cards-grid");
  const emptyState = document.getElementById("empty-state");

  if (items.length === 0) {
    grid.innerHTML = "";
    emptyState.hidden = false;
    return;
  }

  emptyState.hidden = true;
  grid.innerHTML = items.map(cardTemplate).join("");
}

function updateOpportunityCount(count) {
  const el = document.getElementById("opportunity-count");
  el.textContent = `${count} opportunit${count === 1 ? "y" : "ies"} found`;
}

function updateLastUpdated(meta) {
  const el = document.getElementById("last-updated");
  if (!meta || !meta.last_updated) {
    el.textContent = "Last updated: —";
    return;
  }
  const date = new Date(meta.last_updated);
  const formatted = date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  el.textContent = `Last updated: ${formatted}`;
}

// ---------- Dark mode ----------

function initTheme() {
  const saved = localStore.get(THEME_KEY, null);
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved || (prefersDark ? "dark" : "light");
  applyTheme(theme);

  document.getElementById("dark-mode-toggle").addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    localStore.set(THEME_KEY, next);
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const icon = document.getElementById("theme-icon");
  if (icon) icon.textContent = theme === "dark" ? "☀️" : "🌙";
}

// ---------- Init ----------

async function init() {
  initTheme();

  const [items, meta] = await Promise.all([loadAllData(), loadMeta()]);
  allItems = items;

  updateLastUpdated(meta);
  applyFiltersAndSort();

  ["filter-platform", "filter-time", "filter-sort"].forEach((id) => {
    document.getElementById(id).addEventListener("change", applyFiltersAndSort);
  });
}

document.addEventListener("DOMContentLoaded", init);
