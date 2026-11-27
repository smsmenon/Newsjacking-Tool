from __future__ import annotations

from .models import Perspective, Signal
from .scoring import pick_theme

# Each entry maps a claim the source article is implicitly making to TADA's contrarian,
# capability-grounded counter-position. We do not restate the article's claim approvingly --
# "traditional_response" names the claim, "tada_response" argues against it with something concrete.
# Templates take a {theme} placeholder (a concrete supply-chain term from the signal) so two
# different articles landing in the same claim bucket don't render identical text.
CLAIM_LIBRARY: dict[str, dict[str, tuple[str, ...] | str]] = {
    "visibility_only": {
        "terms": ("visibility", "dashboard", "monitor", "system of record", "real-time data", "track"),
        "traditional_response": (
            "The framing here is that better visibility -- more dashboards, more tracking -- is the "
            "fix for {theme}."
        ),
        "tada_response": (
            "Seeing the {theme} signal in a dashboard is step one, not the finish line. You don't need "
            "better visibility, you need to move fast and respond in minutes, not days. That's the gap "
            "between seeing the problem and solving it."
        ),
    },
    "pre_planned_scenarios": {
        "terms": ("scenario", "playbook", "contingency plan", "pre-built", "pre-defined", "if-then"),
        "traditional_response": (
            "The assumption is that a pre-built playbook or scenario library already covers {theme}."
        ),
        "tada_response": (
            "Pre-planned scenarios assume you know what breaks. What if the next {theme} disruption isn't "
            "on your list? You need solutions that can handle unknowns in real time and enable faster "
            "decisions."
        ),
    },
    "quarterly_planning": {
        "terms": ("quarterly", "annual planning", "planning cycle", "static plan", "forecast cycle"),
        "traditional_response": (
            "The response being proposed is a tighter forecast or a faster planning cycle for {theme}."
        ),
        "tada_response": (
            "Disruption is the new normal. When {theme} shifts, quarterly planning is your enemy. The "
            "plan needs to change the moment the constraint does, not at the next review meeting."
        ),
    },
    "probabilistic_orchestration": {
        "terms": ("probabilistic", "recommendation engine", "predictive model", "consolidat", "pre-built workflow"),
        "traditional_response": (
            "The pitch is consolidating platforms and layering probabilistic recommendations or "
            "pre-built workflows on top of {theme}."
        ),
        "tada_response": (
            "Most of that is automating probabilistic recommendations on the same planning stack. When "
            "{theme} hits a real constraint, those recommendations fail. You need orchestration grounded "
            "in deterministic logic that computes what's actually possible right now."
        ),
    },
    "ai_needs_to_be_smarter": {
        "terms": ("smarter ai", "more intelligent", "next-gen ai", "advanced model", "better algorithm"),
        "traditional_response": (
            "The argument is that a smarter or more advanced model is what closes the gap on {theme}."
        ),
        "tada_response": (
            "You can't make AI \"smart enough\" for {theme}. You have to make your operating logic "
            "executable -- systems that make calls fast, explain their reasoning, and never guess. "
            "That's what a team can actually act on."
        ),
    },
}

DEFAULT_TRADITIONAL_RESPONSE = (
    "The article treats reporting the {theme} disruption -- and knowing it happened -- as the resolution."
)
DEFAULT_TADA_RESPONSE = (
    "Knowing about {theme} isn't the same as acting on it. The gap that costs manufacturers money sits "
    "between detecting a signal and executing a response -- and that's a decision-speed problem, not an "
    "information problem."
)


def _match_claim(signal: Signal) -> dict[str, str] | None:
    text = f"{signal.headline} {signal.summary} {signal.evidence}".lower()
    for claim in CLAIM_LIBRARY.values():
        if any(term in text for term in claim["terms"]):
            return claim
    return None


def build_perspective(signal: Signal) -> Perspective:
    primary_risk = signal.risks[0] if signal.risks else "slower response to disruption"
    primary_opportunity = (
        signal.opportunities[0] if signal.opportunities else "faster decision execution"
    )
    theme = pick_theme(signal)

    claim = _match_claim(signal)
    traditional_template = claim["traditional_response"] if claim else DEFAULT_TRADITIONAL_RESPONSE
    tada_template = claim["tada_response"] if claim else DEFAULT_TADA_RESPONSE
    traditional_response = traditional_template.format(theme=theme)
    tada_response = tada_template.format(theme=theme)

    return Perspective(
        what_happened=f"{signal.source} reported a {signal.signal_type.lower()} signal: {signal.headline}.",
        why_it_matters=(
            f"{traditional_response} For a $1B+ manufacturer, that's the wrong place to stop -- it doesn't "
            "close the gap between seeing a constraint and acting on it."
        ),
        potential_impact=(
            f"Left unaddressed, this shows up as {primary_risk.lower()}, higher operating cost, and "
            "slower protection of service levels."
        ),
        traditional_response=traditional_response,
        tada_response=tada_response,
        detect=f"Track indicators related to {', '.join(signal.keywords[:4]) or signal.signal_type.lower()}.",
        decide="Compute the response options that are actually executable under current cost, inventory, service, and supplier constraints.",
        do=(
            f"Trigger a response focused on {primary_opportunity.lower()}, executed in minutes rather "
            "than routed through another planning cycle."
        ),
    )

