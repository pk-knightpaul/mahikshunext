"""
Unit tests for scripts/fetch_binance.py.

These test the pure functions (parse_exchange_info, build_items) and the
snapshot persistence helpers (load_previous_snapshot, save_snapshot)
against a realistic fixture of Binance's documented /api/v3/exchangeInfo
response shape, without making any network calls.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fetch_binance
from fetch_binance import parse_exchange_info, build_items, load_previous_snapshot, save_snapshot

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "binance_exchange_info.json")


def load_fixture():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def test_parse_exchange_info_only_includes_trading_symbols():
    payload = load_fixture()
    result = parse_exchange_info(payload)

    assert "BTCUSDT" in result
    assert "ETHUSDT" in result
    assert "NEWCOINUSDT" in result
    assert "HALTEDUSDT" not in result  # status is HALT, not TRADING


def test_parse_exchange_info_returns_symbol_info():
    payload = load_fixture()
    result = parse_exchange_info(payload)
    assert result["BTCUSDT"]["baseAsset"] == "BTC"
    assert result["BTCUSDT"]["quoteAsset"] == "USDT"


def test_parse_exchange_info_handles_missing_symbols_key():
    assert parse_exchange_info({}) == {}


def test_parse_exchange_info_skips_malformed_entries():
    payload = {"symbols": [{"status": "TRADING"}, "not-a-dict", None]}
    result = parse_exchange_info(payload)
    assert result == {}  # missing "symbol" key means it's skipped


def test_build_items_produces_unified_schema():
    new_symbols = {
        "NEWCOINUSDT": {"symbol": "NEWCOINUSDT", "baseAsset": "NEWCOIN", "quoteAsset": "USDT"}
    }
    items = build_items(new_symbols, "2026-07-25T10:00:00Z")

    assert len(items) == 1
    item = items[0]
    assert item["id"] == "binance_NEWCOINUSDT"
    assert item["platform"] == "binance"
    assert item["content_type"] == "listing"
    assert "NEWCOIN" in item["title"]
    assert item["published_at"] == "2026-07-25T10:00:00Z"
    assert "newcoin" in item["tags"]


def test_build_items_empty_dict_produces_no_items():
    assert build_items({}, "2026-07-25T10:00:00Z") == []


def test_diff_detects_only_new_symbols():
    """Simulates the core fetch() logic: previous snapshot vs current."""
    previous = {"BTCUSDT": True, "ETHUSDT": True}
    payload = load_fixture()
    current = parse_exchange_info(payload)

    new_symbol_names = set(current) - set(previous)
    # HALTEDUSDT is excluded because it's not TRADING; NEWCOINUSDT is new.
    assert new_symbol_names == {"NEWCOINUSDT"}


# ---------- Snapshot persistence ----------

def test_load_previous_snapshot_missing_file_returns_empty_dict(tmp_path, monkeypatch):
    snapshot_path = tmp_path / ".binance_symbols_snapshot.json"
    monkeypatch.setattr(fetch_binance, "SNAPSHOT_PATH", str(snapshot_path))
    assert load_previous_snapshot() == {}


def test_load_previous_snapshot_empty_array_returns_empty_dict(tmp_path, monkeypatch):
    # Mirrors the repo's seeded data/.binance_symbols_snapshot.json ([]) --
    # an empty baseline should behave identically to "no snapshot yet",
    # so the very first real run doesn't flag every existing symbol as new.
    snapshot_path = tmp_path / ".binance_symbols_snapshot.json"
    snapshot_path.write_text("[]")
    monkeypatch.setattr(fetch_binance, "SNAPSHOT_PATH", str(snapshot_path))
    assert load_previous_snapshot() == {}


def test_load_previous_snapshot_reads_existing_symbols(tmp_path, monkeypatch):
    snapshot_path = tmp_path / ".binance_symbols_snapshot.json"
    snapshot_path.write_text(json.dumps(["BTCUSDT", "ETHUSDT"]))
    monkeypatch.setattr(fetch_binance, "SNAPSHOT_PATH", str(snapshot_path))
    result = load_previous_snapshot()
    assert set(result.keys()) == {"BTCUSDT", "ETHUSDT"}


def test_load_previous_snapshot_corrupt_file_returns_empty_dict(tmp_path, monkeypatch):
    snapshot_path = tmp_path / ".binance_symbols_snapshot.json"
    snapshot_path.write_text("not valid json{{{")
    monkeypatch.setattr(fetch_binance, "SNAPSHOT_PATH", str(snapshot_path))
    assert load_previous_snapshot() == {}


def test_save_snapshot_writes_sorted_symbol_list(tmp_path, monkeypatch):
    snapshot_path = tmp_path / ".binance_symbols_snapshot.json"
    monkeypatch.setattr(fetch_binance, "SNAPSHOT_PATH", str(snapshot_path))

    save_snapshot({"ETHUSDT": {}, "BTCUSDT": {}})

    with open(snapshot_path) as f:
        result = json.load(f)
    assert result == ["BTCUSDT", "ETHUSDT"]  # sorted


def test_save_snapshot_roundtrips_with_load(tmp_path, monkeypatch):
    snapshot_path = tmp_path / ".binance_symbols_snapshot.json"
    monkeypatch.setattr(fetch_binance, "SNAPSHOT_PATH", str(snapshot_path))

    save_snapshot({"BTCUSDT": {}, "NEWCOINUSDT": {}})
    reloaded = load_previous_snapshot()
    assert set(reloaded.keys()) == {"BTCUSDT", "NEWCOINUSDT"}
