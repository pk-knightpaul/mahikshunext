// storage.js — thin wrappers around localStorage / sessionStorage.
// localStorage: persistent, non-sensitive preferences (theme).
// sessionStorage: BYOK API key — cleared when the tab closes, never persisted.

export const localStore = {
  get(key, fallback = null) {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // localStorage may be unavailable (private browsing, quota) — fail silently.
    }
  },
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch {
      /* no-op */
    }
  },
};

export const sessionStore = {
  get(key, fallback = null) {
    try {
      const raw = sessionStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* no-op */
    }
  },
  remove(key) {
    try {
      sessionStorage.removeItem(key);
    } catch {
      /* no-op */
    }
  },
};
