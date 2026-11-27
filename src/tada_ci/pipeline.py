from __future__ import annotations

import argparse
import json
from pathlib import Path

from .content_strategy import build_content
from .models import Article, DailyDigest, DigestItem, Signal
from .scoring import article_to_signal
from .tada_perspective import build_perspective

# Two surfaced signals are treated as the same topic (and only the higher-scored one is kept)
# when they share a signal type and their keyword sets overlap at or above this ratio.
TOPIC_OVERLAP_THRESHOLD = 0.5


def load_articles(path: Path) -> list[Article]:
    data = json.loads(path.read_text())
    return [Article(**item) for item in data]


def _topic_signature(signal: Signal) -> frozenset[str]:
    return frozenset(signal.keywords) or frozenset({signal.signal_type})


def _is_duplicate_topic(signal: Signal, already_selected: list[Signal]) -> bool:
    signature = _topic_signature(signal)
    for other in already_selected:
        if signal.signal_type != other.signal_type:
            continue
        other_signature = _topic_signature(other)
        union = signature | other_signature
        if not union:
            continue
        overlap = len(signature & other_signature) / len(union)
        if overlap >= TOPIC_OVERLAP_THRESHOLD:
            return True
    return False


def _select_signals(articles: list[Article]) -> list[Signal]:
    surfaced = [s for s in (article_to_signal(a) for a in articles) if s.surfaced]
    surfaced.sort(key=lambda s: s.score.final_score, reverse=True)

    deduped: list[Signal] = []
    for signal in surfaced:
        if _is_duplicate_topic(signal, deduped):
            continue
        deduped.append(signal)
    return deduped


def build_digest(articles: list[Article]) -> DailyDigest:
    items: list[DigestItem] = []
    for signal in _select_signals(articles):
        perspective = build_perspective(signal)
        content = build_content(signal, perspective)
        items.append(
            DigestItem(
                signal=signal,
                business_impact=perspective.potential_impact,
                tada_perspective=perspective,
                suggested_action=perspective.do,
                content_opportunity=content,
            )
        )
    return DailyDigest.create(items)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TADA daily intelligence pipeline.")
    parser.add_argument("--input", required=True, help="Path to article JSON input.")
    parser.add_argument("--output", required=True, help="Path to digest JSON output.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    digest = build_digest(load_articles(input_path))
    output_path.write_text(json.dumps(digest.to_dict(), indent=2))
    print(f"Wrote {len(digest.top_signals)} surfaced signals to {output_path}")


if __name__ == "__main__":
    main()

