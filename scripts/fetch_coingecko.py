"""
Fetches currently-trending coins from CoinGecko's free public API
(/search/trending). No API key required for this endpoint.
"""
import requests
from common import write_json, log_error, now_iso

SOURCE = "coingecko"
TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"


def build_items(payload, fetched_at):
    """Turn a raw /search/trending response into unified-schema items.
    Pure function, no I/O -- easy to unit test against a fixture."""
    items = []
    coins = payload.get("coins", [])

    for entry in coins:
        c = entry.get("item", {})
        coin_id = c.get("id")
        name = c.get("name")
        symbol = c.get("symbol", "")
        rank = c.get("market_cap_rank")
        score = c.get("score", 0)  # 0-indexed trending rank
        if not coin_id or not name:
            continue

        title = f"{name} ({symbol.upper()}) is trending on CoinGecko"
        summary = (
            f"{name} is currently trending on CoinGecko"
            + (f", ranked #{rank} by market cap" if rank else "")
            + f". Trending position #{score + 1}."
        )
        items.append({
            "id": f"coingecko_{coin_id}",
            "title": title,
            "platform": "coingecko",
            "content_type": "trending",
            "url": f"https://www.coingecko.com/en/coins/{coin_id}",
            "published_at": fetched_at,
            "engagement": (10 - score) if isinstance(score, int) else 0,
            "summary": summary,
            "tags": ["trending", symbol.lower()] if symbol else ["trending"],
        })
    return items


def fetch():
    items = []
    try:
        resp = requests.get(TRENDING_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        items = build_items(payload, now_iso())
    except Exception as e:
        log_error(SOURCE, e)

    write_json("coingecko.json", items)


if __name__ == "__main__":
    fetch()
