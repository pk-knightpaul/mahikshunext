"""
Detects newly-tradable Binance spot symbols by diffing the current
`GET /api/v3/exchangeInfo` symbol list against a snapshot saved from the
previous run, and normalizes any new symbols into the unified schema.

Design note (why not the old announcements approach):
Binance's unofficial `bapi/.../cms/article/...` endpoint is NOT part of the
documented, supported API surface -- Binance's own developer community has
confirmed it returns 403 for automated/non-browser callers and is not meant
for public use. Rather than depend on an undocumented endpoint that actively
blocks scripted access, this script uses `/api/v3/exchangeInfo`, which is
fully public, documented, unauthenticated, and stable
(https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-endpoints).
A new TRADING-status symbol appearing since the last run is a reliable,
sanctioned proxy for "Binance listed something new."

This trades off timeliness (you learn about a listing once it's live for
trading, not from a pre-listing announcement) for reliability (no reliance
on a blocked, unofficial endpoint). If Binance later exposes an official
public announcements API, fetch() below is the only function that needs to
change -- parse_exchange_info() and build_items() are reusable.
"""
import json
import os
import requests
from common import write_json, log_error, now_iso, DATA_DIR

SOURCE = "binance"
EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
SNAPSHOT_PATH = os.path.join(DATA_DIR, ".binance_symbols_snapshot.json")


def parse_exchange_info(payload):
    """Extract the set of currently-TRADING spot symbols from a raw
    exchangeInfo response. Pure function, no I/O -- easy to unit test
    against a fixture."""
    symbols = payload.get("symbols", [])
    return {
        s["symbol"]: s
        for s in symbols
        if isinstance(s, dict) and s.get("status") == "TRADING" and s.get("symbol")
    }


def load_previous_snapshot():
    if not os.path.exists(SNAPSHOT_PATH):
        return {}
    try:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            return {name: True for name in json.load(f)}
    except (json.JSONDecodeError, OSError):
        return {}


def save_snapshot(current_symbols):
    tmp_path = SNAPSHOT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(sorted(current_symbols.keys()), f)
    os.replace(tmp_path, SNAPSHOT_PATH)


def build_items(new_symbols, fetched_at):
    """Turn a dict of {symbol: symbol_info} into unified-schema items.
    Pure function -- easy to unit test."""
    items = []
    for symbol, info in new_symbols.items():
        base = info.get("baseAsset", "")
        quote = info.get("quoteAsset", "")
        items.append({
            "id": f"binance_{symbol}",
            "title": f"Binance lists {base}/{quote} for spot trading",
            "platform": "binance",
            "content_type": "listing",
            "url": f"https://www.binance.com/en/trade/{base}_{quote}",
            "published_at": fetched_at,
            "engagement": 0,
            "summary": f"{base} became newly tradable against {quote} on Binance spot markets.",
            "tags": ["listing", base.lower()] if base else ["listing"],
        })
    return items


def fetch():
    items = []
    try:
        resp = requests.get(EXCHANGE_INFO_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()

        current_symbols = parse_exchange_info(payload)
        previous_symbols = load_previous_snapshot()

        # First run ever (no snapshot yet): don't flag every existing symbol
        # as "new" -- just establish the baseline silently.
        if previous_symbols:
            new_symbol_names = set(current_symbols) - set(previous_symbols)
            new_symbols = {k: current_symbols[k] for k in new_symbol_names}
            items = build_items(new_symbols, now_iso())

        save_snapshot(current_symbols)
    except Exception as e:
        log_error(SOURCE, e)

    write_json("binance.json", items)


if __name__ == "__main__":
    fetch()
