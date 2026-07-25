"""
Shared helpers used by all fetch_*.py scripts.

Keeps every fetcher honest about:
- writing the exact unified schema
- never crashing the whole pipeline on one bad API call
- de-duplicating by `id` before writing to disk
"""
import json
import os
import sys
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

REQUIRED_FIELDS = [
    "id", "title", "platform", "content_type", "url",
    "published_at", "engagement", "summary", "tags",
]


def now_iso():
    """Current UTC time in ISO-8601 with Z suffix, matching the schema."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_item(item):
    """Raise if an item is missing a required field. Cheap guardrail so a
    malformed record never silently corrupts the JSON file."""
    missing = [f for f in REQUIRED_FIELDS if f not in item]
    if missing:
        raise ValueError(f"Item missing required fields {missing}: {item.get('id', '?')}")


def dedupe_by_id(items):
    seen = set()
    out = []
    for item in items:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        out.append(item)
    return out


def write_json(filename, items):
    """Validate, de-duplicate, and atomically write the items list to
    data/<filename>."""
    for item in items:
        validate_item(item)
    items = dedupe_by_id(items)
    # Sort newest first so the file itself is human-scannable in diffs/PRs.
    items.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    path = os.path.join(DATA_DIR, filename)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)
    print(f"[common] wrote {len(items)} items -> {path}")


def log_error(source, err):
    print(f"[{source}] ERROR: {err}", file=sys.stderr)
