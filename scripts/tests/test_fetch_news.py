"""
Unit tests for scripts/fetch_news.py build_items(), against a fixture of
feedparser-entry-like dicts.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_news import build_items, make_id, struct_time_to_iso

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "news_entries.json")


def load_fixture():
    """Loads the JSON fixture and converts any `published_parsed` list back
    into a real time.struct_time, matching what feedparser actually
    produces (JSON itself has no struct_time representation, so the raw
    fixture stores it as a plain list)."""
    with open(FIXTURE_PATH) as f:
        entries = json.load(f)
    for entry in entries:
        if isinstance(entry.get("published_parsed"), list):
            entry["published_parsed"] = time.struct_time(tuple(entry["published_parsed"]))
    return entries


def test_build_items_skips_entries_without_title_or_link():
    entries = load_fixture()
    items = build_items(entries, "CoinDesk")
    # 4 fixture entries; 2 are missing title or link and should be skipped.
    assert len(items) == 2


def test_build_items_produces_unified_schema():
    entries = load_fixture()
    items = build_items(entries, "CoinDesk")
    item = items[0]

    assert item["platform"] == "news"
    assert item["content_type"] == "article"
    assert item["id"] == make_id(item["url"])
    assert "coindesk" in item["tags"]


def test_build_items_deterministic_id_from_url():
    entries = load_fixture()
    items = build_items(entries, "CoinDesk")
    # Same URL should always produce the same id (important for de-dup
    # across runs).
    assert items[0]["id"] == make_id("https://example.com/news/altcoin-etf")


def test_build_items_summary_truncated_to_280_chars():
    entries = [{
        "title": "Long article",
        "link": "https://example.com/long",
        "summary": "x" * 500,
    }]
    items = build_items(entries, "Decrypt")
    assert len(items[0]["summary"]) == 280


def test_build_items_falls_back_when_published_parsed_missing():
    entries = load_fixture()
    items = build_items(entries, "Decrypt")
    # Second fixture entry has published_parsed: null -> should still get
    # a valid ISO timestamp via now_iso() fallback, not crash.
    whale_item = next(i for i in items if "whale" in i["title"].lower())
    assert whale_item["published_at"].endswith("Z")


def test_struct_time_to_iso_handles_none():
    result = struct_time_to_iso(None)
    assert result.endswith("Z")


def test_struct_time_to_iso_converts_valid_struct_time():
    st = time.struct_time((2026, 7, 24, 18, 0, 0, 4, 205, 0))
    result = struct_time_to_iso(st)
    assert result.startswith("2026-07-24")


def test_struct_time_to_iso_degrades_gracefully_on_malformed_input():
    # A plain list/tuple that isn't a real time.struct_time should not
    # crash the pipeline -- it should fall back to "now" rather than
    # propagate an exception up through build_items().
    result = struct_time_to_iso([2026, 7, 24, 18, 0, 0, 4, 205, 0])
    assert result.endswith("Z")


def test_build_items_empty_entries():
    assert build_items([], "CoinDesk") == []
