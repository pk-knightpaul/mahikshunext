"""
Runs last, after all fetch_*.py scripts. Reads each data file to determine
whether it fetched successfully (non-empty, or explicitly marked ok) and
writes data/meta.json with a fresh timestamp + per-platform status.

Status logic:
- "ok"      -- the file exists and contains a valid JSON array (even an
               empty one -- that can legitimately mean "no new opportunities
               right now", not a failure).
- "error"   -- the file exists but isn't valid JSON, or isn't a JSON array.
- "missing" -- the file doesn't exist at all (e.g. a fetcher never ran).
"""
import json
import os
from common import DATA_DIR, now_iso

PLATFORMS = ["binance", "coingecko", "dexscreener", "news"]


def check_platform(name, data_dir=None):
    """Pure-ish function: takes an optional data_dir override so it's
    testable against a temp directory without monkeypatching module state."""
    base_dir = data_dir if data_dir is not None else DATA_DIR
    path = os.path.join(base_dir, f"{name}.json")
    if not os.path.exists(path):
        return "missing"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return "error"
        return "ok"
    except (json.JSONDecodeError, OSError):
        return "error"


def build_meta(data_dir=None):
    """Pure-ish function returning the meta dict without writing to disk --
    easy to unit test."""
    status = {p: check_platform(p, data_dir=data_dir) for p in PLATFORMS}
    return {
        "last_updated": now_iso(),
        "platforms_status": status,
    }


def main():
    meta = build_meta()
    path = os.path.join(DATA_DIR, "meta.json")
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)
    print(f"[update_meta] {meta}")


if __name__ == "__main__":
    main()
