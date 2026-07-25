"""
Fetches recent crypto news headlines from a handful of public RSS feeds
using `feedparser`. No API key required.
"""
import hashlib
from datetime import datetime, timezone
from time import mktime
from common import write_json, log_error, now_iso

SOURCE = "news"

FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
]

MAX_PER_FEED = 15


def struct_time_to_iso(st):
    if not st:
        return now_iso()
    try:
        dt = datetime.fromtimestamp(mktime(st), tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return now_iso()


def make_id(url):
    return "news_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def build_items(entries, source_name):
    """Turn a list of feedparser entries into unified-schema items.
    Pure function, no I/O -- easy to unit test against a fixture. Does not
    import feedparser, so it's testable without that dependency installed."""
    items = []
    for entry in entries[:MAX_PER_FEED]:
        link = entry.get("link")
        title = entry.get("title", "").strip()
        if not link or not title:
            continue
        summary = entry.get("summary", "") or entry.get("description", "")
        # Strip any embedded HTML tags for a clean plain-text summary.
        summary_clean = " ".join(summary.replace("<", " <").split())
        published = struct_time_to_iso(entry.get("published_parsed") or entry.get("updated_parsed"))

        items.append({
            "id": make_id(link),
            "title": title,
            "platform": "news",
            "content_type": "article",
            "url": link,
            "published_at": published,
            "engagement": 0,
            "summary": summary_clean[:280],
            "tags": ["news", source_name.lower()],
        })
    return items


def fetch():
    import feedparser  # imported lazily: only fetch() needs it, so the
    # pure parsing functions above stay testable without the dependency
    # installed (useful in restricted/offline environments).

    items = []
    for source_name, feed_url in FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.bozo and not parsed.entries:
                raise RuntimeError(f"Failed to parse feed: {parsed.bozo_exception}")
            items.extend(build_items(parsed.entries, source_name))
        except Exception as e:
            log_error(f"{SOURCE}:{source_name}", e)
            continue

    write_json("news.json", items)


if __name__ == "__main__":
    fetch()
