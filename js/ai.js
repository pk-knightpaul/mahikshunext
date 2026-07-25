// ai.js — "Bring Your Own Key" AI integration (Phase 2).
//
// The API key never touches any Mahikshu server (there isn't one — this is
// a static site). It's stored only in sessionStorage and sent directly,
// client-side, to the provider's own API. Clearing the key or closing the
// tab removes it completely.

import { sessionStore } from "./storage.js";

const KEY_STORAGE_KEY = "mahikshu_ai_key";
const PROVIDER_STORAGE_KEY = "mahikshu_ai_provider";

const PROVIDER_ENDPOINTS = {
  anthropic: "https://api.anthropic.com/v1/messages",
  openai: "https://api.openai.com/v1/chat/completions",
};

function getDialog() {
  return document.getElementById("ai-setup-dialog");
}

function initAiSetup() {
  const openBtn = document.getElementById("ai-setup-btn");
  const dialog = getDialog();
  const form = document.getElementById("ai-setup-form");
  const keyInput = document.getElementById("ai-api-key");
  const providerSelect = document.getElementById("ai-provider");
  const clearBtn = document.getElementById("ai-clear-btn");

  if (!openBtn || !dialog || !form) return;

  // Pre-fill from session (so re-opening the dialog mid-session shows saved state).
  const savedProvider = sessionStore.get(PROVIDER_STORAGE_KEY, "anthropic");
  const savedKey = sessionStore.get(KEY_STORAGE_KEY, "");
  providerSelect.value = savedProvider;
  keyInput.value = savedKey || "";

  openBtn.addEventListener("click", () => {
    dialog.showModal();
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const key = keyInput.value.trim();
    const provider = providerSelect.value;
    if (key) {
      sessionStore.set(KEY_STORAGE_KEY, key);
      sessionStore.set(PROVIDER_STORAGE_KEY, provider);
    }
    dialog.close();
  });

  clearBtn.addEventListener("click", () => {
    sessionStore.remove(KEY_STORAGE_KEY);
    keyInput.value = "";
  });

  // Close on backdrop click.
  dialog.addEventListener("click", (e) => {
    const rect = dialog.getBoundingClientRect();
    const inDialog =
      e.clientX >= rect.left && e.clientX <= rect.right &&
      e.clientY >= rect.top && e.clientY <= rect.bottom;
    if (!inDialog) dialog.close();
  });
}

/**
 * Returns { provider, key } if the user has configured BYOK, otherwise null.
 * Other modules (e.g. a future "summarize" card action) can import this
 * to check whether AI features are available before showing AI-only UI.
 */
export function getAiCredentials() {
  const key = sessionStore.get(KEY_STORAGE_KEY, "");
  const provider = sessionStore.get(PROVIDER_STORAGE_KEY, "anthropic");
  if (!key) return null;
  return { provider, key };
}

/**
 * Sends a single-turn prompt to the configured provider directly from the
 * browser. Throws if no key is configured or the request fails.
 */
export async function askAi(prompt) {
  const creds = getAiCredentials();
  if (!creds) {
    throw new Error("No AI key configured. Click 'AI Setup' to add one.");
  }

  if (creds.provider === "anthropic") {
    const resp = await fetch(PROVIDER_ENDPOINTS.anthropic, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": creds.key,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 1000,
        messages: [{ role: "user", content: prompt }],
      }),
    });
    if (!resp.ok) throw new Error(`Anthropic API error: ${resp.status}`);
    const data = await resp.json();
    return (data.content || [])
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("\n");
  }

  if (creds.provider === "openai") {
    const resp = await fetch(PROVIDER_ENDPOINTS.openai, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${creds.key}`,
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [{ role: "user", content: prompt }],
      }),
    });
    if (!resp.ok) throw new Error(`OpenAI API error: ${resp.status}`);
    const data = await resp.json();
    return data.choices?.[0]?.message?.content || "";
  }

  throw new Error(`Unknown provider: ${creds.provider}`);
}

document.addEventListener("DOMContentLoaded", initAiSetup);
