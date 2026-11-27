from __future__ import annotations
import logging
import re

log = logging.getLogger(__name__)

_STOP = {
    "the", "a", "an", "in", "on", "at", "for", "of", "to", "and",
    "or", "is", "are", "was", "were", "has", "have", "it", "its",
    "be", "been", "by", "from", "with", "as", "this", "that",
}


def _stem(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _words(title: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", title.lower())
    return {_stem(t) for t in tokens if t not in _STOP and len(t) > 2}


def _similarity(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    shared = wa & wb
    return len(shared) / max(len(wa), len(wb))


def _same_event(a: dict, b: dict) -> bool:
    """
    LLM same-event check — title word-overlap alone misses this constantly, because two
    outlets covering the identical news event routinely share almost no vocabulary
    ("Trade Talks Break Down... Tariffs Take Effect" vs "Trump's 50% tariff... in effect
    as talks stall" scored 0.2 word-similarity despite being the same story). Only called
    for pairs that already share 2+ matched_themes, so this stays cheap — a handful of
    calls on a ~10-item candidate list, not O(n^2) over everything.
    """
    try:
        from .contrarian_pipeline import _claude
    except Exception:
        return False

    def snippet(x: dict) -> str:
        title = x.get("title", x.get("headline", ""))
        content = (x.get("content") or "")[:300]
        return f"{title} — {content}"

    prompt = f"""Are these two articles reporting on the SAME underlying news event (not just the same
general topic)? Different outlets often use very different wording for identical news.

ARTICLE A: {snippet(a)}

ARTICLE B: {snippet(b)}

Respond with ONLY: SAME_EVENT: [true/false]"""
    try:
        raw = _claude(prompt, max_tokens=20)
        return "true" in raw.lower()
    except Exception as exc:
        log.debug("_same_event check failed: %s", exc)
        return False


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    # Pass 1: URL dedup
    seen_urls: set[str] = set()
    url_deduped: list[dict] = []
    for a in articles:
        url = a.get("url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        url_deduped.append(a)

    # Pass 2: title similarity OR (shared themes + LLM same-event confirmation)
    kept: list[dict] = []
    for candidate in url_deduped:
        title = candidate.get("title", candidate.get("headline", ""))
        score = candidate.get("relevance_score", 0.0)
        tier = candidate.get("trust_tier", 3)
        c_themes = set(candidate.get("matched_themes", []) or [])

        duplicate = False
        for i, existing in enumerate(kept):
            etitle = existing.get("title", existing.get("headline", ""))
            e_themes = set(existing.get("matched_themes", []) or [])

            is_dup = _similarity(title, etitle) >= 0.6
            if not is_dup and len(c_themes & e_themes) >= 2:
                is_dup = _same_event(candidate, existing)

            if is_dup:
                escore = existing.get("relevance_score", 0.0)
                etier = existing.get("trust_tier", 3)
                # Duplicates used to be dropped outright, which threw away the fact that a
                # story got broad pickup — and left whichever outlet happened to score
                # highest as the only link, so a trade-press version could stand in for a
                # story the WSJ also ran. Keep the losing coverage alongside the winner.
                if tier < etier or (tier == etier and score > escore):
                    candidate["coverage"] = existing.get("coverage", []) + [_coverage_of(existing)]
                    kept[i] = candidate
                else:
                    existing.setdefault("coverage", []).append(_coverage_of(candidate))
                duplicate = True
                break

        if not duplicate:
            kept.append(candidate)

    kept.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
    return kept


def _coverage_of(article: dict) -> dict:
    """The minimum needed to link an outlet's version of a story in the digest."""
    return {
        "source": article.get("source", ""),
        "url": article.get("url", ""),
        "title": article.get("title", article.get("headline", "")),
    }
