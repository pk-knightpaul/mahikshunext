"""
Unit tests for scripts/update_meta.py.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from update_meta import check_platform, build_meta, PLATFORMS


def test_check_platform_missing_file(tmp_path):
    result = check_platform("binance", data_dir=str(tmp_path))
    assert result == "missing"


def test_check_platform_valid_empty_array(tmp_path):
    (tmp_path / "binance.json").write_text("[]")
    result = check_platform("binance", data_dir=str(tmp_path))
    assert result == "ok"


def test_check_platform_valid_populated_array(tmp_path):
    (tmp_path / "binance.json").write_text(json.dumps([{"id": "x"}]))
    result = check_platform("binance", data_dir=str(tmp_path))
    assert result == "ok"


def test_check_platform_corrupt_json_is_error(tmp_path):
    (tmp_path / "binance.json").write_text("not valid json{{{")
    result = check_platform("binance", data_dir=str(tmp_path))
    assert result == "error"


def test_check_platform_non_array_json_is_error(tmp_path):
    # A valid JSON object (not array) should be flagged as an error --
    # every fetcher is expected to write a list, per the unified schema.
    (tmp_path / "binance.json").write_text(json.dumps({"unexpected": "shape"}))
    result = check_platform("binance", data_dir=str(tmp_path))
    assert result == "error"


def test_build_meta_includes_all_platforms(tmp_path):
    for p in PLATFORMS:
        (tmp_path / f"{p}.json").write_text("[]")
    meta = build_meta(data_dir=str(tmp_path))

    assert set(meta["platforms_status"].keys()) == set(PLATFORMS)
    assert all(v == "ok" for v in meta["platforms_status"].values())


def test_build_meta_mixed_statuses(tmp_path):
    (tmp_path / "binance.json").write_text("[]")
    (tmp_path / "coingecko.json").write_text("not json{{{")
    # dexscreener.json and news.json intentionally absent
    meta = build_meta(data_dir=str(tmp_path))

    assert meta["platforms_status"]["binance"] == "ok"
    assert meta["platforms_status"]["coingecko"] == "error"
    assert meta["platforms_status"]["dexscreener"] == "missing"
    assert meta["platforms_status"]["news"] == "missing"


def test_build_meta_has_last_updated_timestamp(tmp_path):
    meta = build_meta(data_dir=str(tmp_path))
    assert meta["last_updated"].endswith("Z")
