"""
Fetches trending token pairs from DexScreener's public, documented
`/token-boosts/latest/v1` endpoint. DexScreener doesn't expose a single
"trending list" endpoint publicly, so boosted (promoted) tokens are used as
a reasonable public proxy for "content-worthy" DEX activity. No API key
required.

Per DexScreener's docs (https://docs.dexscreener.com/api/reference), this
endpoint returns a JSON array directly at the top level -- not wrapped in a
"data" key -- with fields: url, chainId, tokenAddress, amount, totalAmount,
and optional icon/header/description/links.
"""
import requests
from common import write_json, log_error, now_iso

SOURCE = "dexscreener"
BOOSTS_URL = "https://api.dexscreener.com/token-boosts/latest/v1"


def build_items(payload, fetched_at):
    """Turn a raw token-boosts/latest/v1 response into unified-schema items.
    Pure function, no I/O -- easy to unit test against a fixture."""
    items = []
    entries = payload if isinstance(payload, list) else []

    for e in entries:
        token_address = e.get("tokenAddress")
        chain_id = e.get("chainId", "")
        url = e.get("url") or (
            f"https://dexscreener.com/{chain_id}/{token_address}" if token_address else None
        )
        description = e.get("description") or ""
        if not token_address or not url:
            continue

        title = f"Boosted token on {chain_id.upper()}: {token_address[:8]}..."
        amount = e.get("totalAmount", e.get("amount", 0))
        items.append({
            "id": f"dexscreener_{chain_id}_{token_address}",
            "title": title,
            "platform": "dexscreener",
            "content_type": "trending",
            "url": url,
            "published_at": fetched_at,
            "engagement": int(amount) if isinstance(amount, (int, float)) else 0,
            "summary": description[:280] if description else "Trending/boosted token pair on DexScreener.",
            "tags": ["dex", chain_id.lower()] if chain_id else ["dex"],
        })
    return items


def fetch():
    items = []
    try:
        resp = requests.get(BOOSTS_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        items = build_items(payload, now_iso())
    except Exception as e:
        log_error(SOURCE, e)

    write_json("dexscreener.json", items)


if __name__ == "__main__":
    fetch()
