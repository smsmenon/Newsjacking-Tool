from tada_ci.models import Article
from tada_ci.pipeline import build_digest


def test_digest_surfaces_relevant_signal():
    articles = [
        Article(
            title="Tariff Risk Forces Supplier Planning Changes",
            source="Supply Chain Dive",
            category="Supply Chain",
            url="https://example.com/test",
            publication_date="2026-06-15T00:00:00Z",
            full_text=(
                "Tariff risk, supplier disruption, inventory cost, planning response, "
                "decision intelligence, and action workflows are changing supply chain strategy."
            ),
        )
    ]
    digest = build_digest(articles)
    assert len(digest.top_signals) == 1
    assert digest.top_signals[0].signal.score.final_score >= 7
    assert digest.top_signals[0].content_opportunity.review_status == "draft"
