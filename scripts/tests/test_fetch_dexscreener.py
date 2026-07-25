"""
Unit tests for scripts/fetch_dexscreener.py build_items(), against a
fixture matching DexScreener's documented /token-boosts/latest/v1 response
shape (a top-level JSON array, not wrapped in a "data" key).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_dexscreener import build_items

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "dexscreener_boosts.json")


def load_fixture():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def test_build_items_skips_entries_without_token_address():
    payload = load_fixture()
    items = build_items(payload, "2026-07-25T10:00:00Z")
    # The fixture has 3 entries; the third has an empty tokenAddress.
    assert len(items) == 2


def test_build_items_produces_unified_schema():
    payload = load_fixture()
    items = build_items(payload, "2026-07-25T10:00:00Z")
    item = items[0]

    assert item["platform"] == "dexscreener"
    assert item["content_type"] == "trending"
    assert item["id"].startswith("dexscreener_solana_")
    assert "solana" in item["tags"]
    assert item["published_at"] == "2026-07-25T10:00:00Z"


def test_build_items_uses_total_amount_for_engagement():
    payload = load_fixture()
    items = build_items(payload, "2026-07-25T10:00:00Z")
    item = items[0]
    assert item["engagement"] == 1500  # totalAmount, not amount


def test_build_items_falls_back_to_generic_summary_without_description():
    payload = load_fixture()
    items = build_items(payload, "2026-07-25T10:00:00Z")
    item = next(i for i in items if "base" in i["id"])
    assert item["summary"] == "Trending/boosted token pair on DexScreener."


def test_build_items_handles_top_level_dict_gracefully():
    # If DexScreener ever wraps the array (contrary to current docs), we
    # should degrade to an empty list rather than crash.
    assert build_items({"data": []}, "2026-07-25T10:00:00Z") == []


def test_build_items_empty_list():
    assert build_items([], "2026-07-25T10:00:00Z") == []
