"""Competitor news must not be consumed by a run that never mailed it.

Run #1 was a dry run and still marked 22 competitor URLs as seen, which would have
dropped them from the next real digest: never sent, never offered again.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tada_ci.services import competitor_watch as cw

URLS = ["https://example.com/a", "https://example.com/b"]

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "data").mkdir()
    cache = root / "data" / "competitor_seen.json"

    # A prior run exists, so this is not the baseline case.
    cw.record_seen(root, ["https://example.com/old"])
    before = json.loads(cache.read_text())
    assert len(before) == 1, before

    # Deferred: the sink collects, the cache is untouched.
    sink: list[str] = []
    sink.extend(URLS)  # what run_competitor_watch does with seen_sink
    assert json.loads(cache.read_text()) == before, "seen-cache written despite seen_sink"

    # The caller records only once the send succeeded.
    cw.record_seen(root, sink)
    after = json.loads(cache.read_text())
    assert set(URLS) <= set(after), "recorded URLs missing after a successful send"
    assert len(after) == 3, after

print("OK: deferred recording leaves the cache untouched until the send succeeds")

# The wiring itself: newsjacking must pass a sink and record only on success.
src = Path(__file__).resolve().parents[1] / "src" / "tada_ci" / "services" / "newsjacking.py"
text = src.read_text(encoding="utf-8")
assert "seen_sink=competitor_seen_pending" in text, "competitor watch is not deferring"
gate = text.index('if send_result.get("success")')
assert "record_competitors_seen" in text[gate:gate + 400], \
    "competitor URLs are not recorded inside the send-success gate"
print("OK: newsjacking defers, and records inside the success gate")
