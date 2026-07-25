"""
Unit tests for scripts/common.py.

Run with: python -m pytest scripts/tests/ -v
(from the repo root, after `pip install pytest -r scripts/requirements.txt`)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from common import validate_item, dedupe_by_id, write_json, REQUIRED_FIELDS

VALID_ITEM = {
    "id": "test_1",
    "title": "Test title",
    "platform": "news",
    "content_type": "article",
    "url": "https://example.com",
    "published_at": "2026-07-25T10:00:00Z",
    "engagement": 0,
    "summary": "A test summary.",
    "tags": ["test"],
}


def test_validate_item_accepts_valid_item():
    validate_item(VALID_ITEM)  # should not raise


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_validate_item_rejects_missing_field(missing_field):
    item = {k: v for k, v in VALID_ITEM.items() if k != missing_field}
    with pytest.raises(ValueError):
        validate_item(item)


def test_dedupe_by_id_removes_duplicates():
    items = [
        {**VALID_ITEM, "id": "a"},
        {**VALID_ITEM, "id": "b"},
        {**VALID_ITEM, "id": "a"},  # duplicate
    ]
    result = dedupe_by_id(items)
    assert len(result) == 2
    assert {i["id"] for i in result} == {"a", "b"}


def test_dedupe_by_id_keeps_first_occurrence():
    items = [
        {**VALID_ITEM, "id": "a", "title": "first"},
        {**VALID_ITEM, "id": "a", "title": "second"},
    ]
    result = dedupe_by_id(items)
    assert len(result) == 1
    assert result[0]["title"] == "first"


def test_dedupe_by_id_empty_list():
    assert dedupe_by_id([]) == []


def test_write_json_sorts_newest_first(tmp_path, monkeypatch):
    import common
    monkeypatch.setattr(common, "DATA_DIR", str(tmp_path))

    items = [
        {**VALID_ITEM, "id": "old", "published_at": "2026-01-01T00:00:00Z"},
        {**VALID_ITEM, "id": "new", "published_at": "2026-07-01T00:00:00Z"},
    ]
    write_json("test_output.json", items)

    with open(tmp_path / "test_output.json") as f:
        result = json.load(f)
    assert [i["id"] for i in result] == ["new", "old"]


def test_write_json_raises_on_invalid_item(tmp_path, monkeypatch):
    import common
    monkeypatch.setattr(common, "DATA_DIR", str(tmp_path))

    bad_item = {k: v for k, v in VALID_ITEM.items() if k != "url"}
    with pytest.raises(ValueError):
        write_json("test_output.json", [bad_item])


def test_write_json_writes_valid_json_for_empty_list(tmp_path, monkeypatch):
    import common
    monkeypatch.setattr(common, "DATA_DIR", str(tmp_path))

    write_json("empty.json", [])
    with open(tmp_path / "empty.json") as f:
        result = json.load(f)
    assert result == []
