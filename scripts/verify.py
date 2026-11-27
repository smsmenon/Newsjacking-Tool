from __future__ import annotations

from pathlib import Path

from tada_ci.pipeline import build_digest, load_articles


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    digest = build_digest(load_articles(root / "examples" / "sample_articles.json"))
    assert digest.top_signals, "expected at least one surfaced signal"
    assert all(item.signal.score.final_score >= 7 for item in digest.top_signals)
    assert all(item.content_opportunity.review_status == "draft" for item in digest.top_signals)
    print(f"Verified {len(digest.top_signals)} surfaced draft signals.")


if __name__ == "__main__":
    main()
