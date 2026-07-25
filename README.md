# Mahikshu

**Swiftly survey the crypto earth.**

Mahikshu is a free, zero-cost dashboard for crypto content writers (SEO/GEO
writers, researchers, community managers) to spot content opportunities —
new exchange listings, trending coins, DEX activity, and breaking news — in
one place, updated hourly.

There is no backend, no database, and no user accounts. The entire site is
static HTML/CSS/JS, and the "database" is a handful of JSON files refreshed
every hour by a scheduled GitHub Action.

---

## How it works

```
GitHub Actions (hourly cron)
        │
        ▼
Python scripts (scripts/fetch_*.py)
   fetch public APIs → normalize → data/*.json
        │
        ▼
git commit + push (via git-auto-commit-action)
        │
        ▼
Static hosting (GitHub Pages / Cloudflare Pages)
        │
        ▼
Browser: js/app.js fetches data/*.json, filters/sorts
         client-side, renders cards
```

**Data sources:**
| Source | What it fetches | Auth required |
|---|---|---|
| Binance | Newly-tradable spot symbols (proxy for new listings — see note below) | No |
| CoinGecko | Currently trending coins | No |
| DexScreener | Boosted/trending token pairs | No |
| RSS (CoinDesk, Cointelegraph, Decrypt) | Recent news headlines | No |

Every fetcher writes to its own file in `data/` using the **same unified
schema** (see `scripts/common.py` → `REQUIRED_FIELDS`), so the frontend
never needs to know which source an item came from beyond its `platform`
field. If any single source's API is down or rate-limited, that script logs
the error and writes an empty list — it never breaks the other three
sources or crashes the whole pipeline.

### A note on the Binance source

Binance does not expose an official, documented, public API for listing
announcements. Its `bapi/.../cms/article/...` endpoint (used internally by
binance.com) is unofficial, undocumented, and actively rejects automated
callers with a 403.

Instead, `fetch_binance.py` uses Binance's officially documented, public
`GET /api/v3/exchangeInfo` endpoint and **diffs the set of currently-TRADING
spot symbols against a snapshot saved from the previous hourly run**
(`data/.binance_symbols_snapshot.json`, committed to the repo so it persists
across runs). A symbol that's tradable now but wasn't in the last snapshot
is treated as a new listing.

Trade-offs versus an announcements feed:
- **Less timely** — you learn about a listing once it's live for trading,
  not from a pre-listing announcement.
- **More reliable** — no dependency on an endpoint that's known to block
  scripted access.

On the very first run ever (no snapshot exists yet), the script establishes
a baseline silently rather than flagging every existing Binance symbol as
"new." You'll start seeing real listing detections starting from the second
run onward.

---

## Running the data pipeline locally

Requirements: Python 3.11+

```bash
cd scripts
pip install -r requirements.txt

python fetch_binance.py
python fetch_coingecko.py
python fetch_dexscreener.py
python fetch_news.py
python update_meta.py   # run last — reads the files above to set status
```

Each script writes/overwrites its file in `../data/`. Check `data/meta.json`
afterward — `platforms_status` should show `"ok"` for each source that
returned valid JSON (an empty list still counts as `"ok"`; it just means no
new items right now). A `"missing"` status means that fetcher's output file
doesn't exist (it never ran); `"error"` means it ran but produced invalid
JSON.

## Running the test suite

Each `fetch_*.py` script separates its pure parsing/normalization logic
(`build_items()`, or `parse_exchange_info()` for Binance) from its
network-calling `fetch()` function. The test suite in `scripts/tests/`
exercises the pure functions against realistic fixtures of each API's
documented response shape — no network access required.

**With pytest (recommended, requires internet to install):**
```bash
pip install pytest -r scripts/requirements.txt
python -m pytest scripts/tests/ -v
```

**Without pytest (dependency-free fallback):**
```bash
python scripts/tests/run_tests_no_deps.py
```
This runs the same test files using a small stdlib-only shim of the pytest
APIs the tests use (`pytest.raises`, `pytest.mark.parametrize`, `tmp_path`,
`monkeypatch`). Prefer real pytest when you have network access — this
fallback exists for offline/restricted environments.

The suite currently covers:
- `common.py` — schema validation, de-duplication, atomic JSON writes
- `fetch_binance.py` — exchangeInfo parsing, TRADING-status filtering,
  snapshot load/save/diff logic
- `fetch_coingecko.py` — trending-response parsing, missing-field handling
- `fetch_dexscreener.py` — token-boosts parsing, malformed-entry handling
- `fetch_news.py` — RSS-entry normalization, timestamp conversion,
  graceful degradation on malformed `published_parsed` values
- `update_meta.py` — per-platform status logic (ok / error / missing)

## Running the frontend locally

No build step. Serve the repo root with any static file server, e.g.:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

(Opening `index.html` directly via `file://` won't work — the browser
blocks `fetch()` of local JSON files under that protocol. You need an actual
HTTP server, even a trivial one.)

## AI Setup (BYOK)

The "AI Setup" button in the header lets you paste your own Anthropic or
OpenAI API key. It's stored only in `sessionStorage` — never sent to any
Mahikshu server (there isn't one), and cleared automatically when you close
the tab. Requests go straight from your browser to the provider's API.

---

## Deploying

### GitHub Pages
1. Push this repo to GitHub.
2. Repo Settings → Pages → set source to the `main` branch, root folder.
3. Repo Settings → Actions → General → under "Workflow permissions," select
   **"Read and write permissions"** (required so the hourly workflow can
   commit updated data back to the repo).
4. The `update-data.yml` workflow will run automatically every hour. You can
   also trigger it manually from the Actions tab (`workflow_dispatch`).

### Cloudflare Pages
1. Connect the repo in the Cloudflare Pages dashboard.
2. Build command: *(none)* — leave blank.
3. Build output directory: `/` (repo root).
4. Cloudflare Pages auto-deploys on every push, including the hourly commits
   from GitHub Actions, so data stays fresh without any extra Cloudflare-side
   configuration.

Both options are free at this project's scale.

---

## Project structure

```
/
├── .github/workflows/update-data.yml   # hourly cron: fetch → commit → push
├── .gitignore
├── LICENSE                             # MIT
├── data/                               # generated JSON, committed to repo
│   ├── binance.json
│   ├── coingecko.json
│   ├── dexscreener.json
│   ├── news.json
│   ├── meta.json                       # last_updated + per-source status
│   └── .binance_symbols_snapshot.json  # previous-run symbol set (for diffing)
├── scripts/                            # Python fetchers
│   ├── common.py                       # shared validate/dedupe/write helpers
│   ├── fetch_binance.py
│   ├── fetch_coingecko.py
│   ├── fetch_dexscreener.py
│   ├── fetch_news.py
│   ├── update_meta.py
│   ├── requirements.txt
│   └── tests/                          # unit tests + fixtures
│       ├── fixtures/
│       ├── test_common.py
│       ├── test_fetch_binance.py
│       ├── test_fetch_coingecko.py
│       ├── test_fetch_dexscreener.py
│       ├── test_fetch_news.py
│       ├── test_update_meta.py
│       └── run_tests_no_deps.py        # pytest-free fallback runner
├── css/styles.css
├── js/
│   ├── app.js                          # fetch, filter, sort, render
│   ├── ai.js                           # BYOK AI integration
│   └── storage.js                      # localStorage/sessionStorage helpers
├── assets/logo.svg
└── index.html
```

## Unified data schema

Every item in every `data/*.json` file (except `meta.json`) follows this
shape:

```json
{
  "id": "binance_NEWCOINUSDT",
  "title": "Binance lists NEWCOIN/USDT for spot trading",
  "platform": "binance",
  "content_type": "listing",
  "url": "https://www.binance.com/en/trade/NEWCOIN_USDT",
  "published_at": "2026-07-25T10:00:00Z",
  "engagement": 0,
  "summary": "NEWCOIN became newly tradable against USDT on Binance spot markets.",
  "tags": ["listing", "newcoin"]
}
```

`scripts/common.py::write_json()` validates every item against this schema
before writing, so a malformed record from a flaky API can't silently
corrupt a data file.
