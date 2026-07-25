"""
Unit tests for scripts/fetch_coingecko.py build_items(), against a fixture
matching CoinGecko's documented /search/trending response shape.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_coingecko import build_items

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "coingecko_trending.json")


def load_fixture():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def test_build_items_skips_entries_without_name():
    payload = load_fixture()
    items = build_items(payload, "2026-07-25T10:00:00Z")
    # The fixture has 3 coins; one has an empty name and should be skipped.
    assert len(items) == 2
    ids = {i["id"] for i in items}
    assert "coingecko_no-name-coin" not in ids


def test_build_items_produces_unified_schema():
    payload = load_fixture()
    items = build_items(payload, "2026-07-25T10:00:00Z")
    item = next(i for i in items if i["id"] == "coingecko_pepe2")

    assert item["platform"] == "coingecko"
    assert item["content_type"] == "trending"
    assert item["url"] == "https://www.coingecko.com/en/coins/pepe2"
    assert "pepe2" in item["tags"]
    assert item["published_at"] == "2026-07-25T10:00:00Z"


def test_build_items_engagement_derived_from_score():
    payload = load_fixture()
    items = build_items(payload, "2026-07-25T10:00:00Z")
    item = next(i for i in items if i["id"] == "coingecko_pepe2")
    # score=0 (top trending) -> engagement = 10 - 0 = 10
    assert item["engagement"] == 10


def test_build_items_handles_null_market_cap_rank():
    payload = load_fixture()
    items = build_items(payload, "2026-07-25T10:00:00Z")
    item = next(i for i in items if i["id"] == "coingecko_some-dog-coin")
    assert "ranked" not in item["summary"]  # rank omitted when null


def test_build_items_empty_coins_list():
    assert build_items({"coins": []}, "2026-07-25T10:00:00Z") == []


def test_build_items_missing_coins_key():
    assert build_items({}, "2026-07-25T10:00:00Z") == []
