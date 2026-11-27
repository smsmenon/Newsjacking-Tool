"""
CLI entry point for the daily "Newsjacking Articles" job. Meant to be invoked by an external
scheduler (Windows Task Scheduler), not by a live Claude session — loads .env itself so it
runs standalone.

Usage: python -m tada_ci.run_newsjacking
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(root: Path) -> None:
    env_path = root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key:
            import os
            os.environ.setdefault(key, value)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _load_dotenv(_ROOT)

    from tada_ci.services.newsjacking import run_newsjacking

    # No explicit window: 72h on Monday (back to Friday's run), 24h Tuesday-Friday.
    result = run_newsjacking(root=_ROOT, to_email="sidelle.menon@tadanow.com")

    print(f"Subject: {result['subject']}")
    print(f"Send result: {result['send_result']}")
    print(f"Website: {result['website_usage_stats']}")
    print(f"LinkedIn: {result['linkedin_summary']}")

    # A dry run (SEND_EMAIL=false) reports success=False because nothing was sent. That is
    # the requested outcome, not a failure — only a genuine send attempt that failed is.
    send = result["send_result"]
    return 0 if (send.get("success") or send.get("skipped")) else 1


if __name__ == "__main__":
    sys.exit(main())
