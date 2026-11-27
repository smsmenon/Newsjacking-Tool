"""
TADA Intelligence Platform — Content Strategy Agent
====================================================
Takes surfaced signals + TADA perspectives and generates a full content
strategy with complete traceability back to source signals:

  - 5 LinkedIn post ideas per signal (different angles/hooks)
  - Thought leadership article outline (title, angle, outline, keywords)
  - Newsletter topic suggestions
  - Sales talking points (per signal, per persona)
  - Webinar / podcast topic ideas

All content ideas include:
  - signal_id: full traceability to the originating signal
  - target_audience: which TADA team benefits (marketing/sales/cs/product/leadership)
  - format, hook, CTA, urgency level

Model recommendation: claude-3-5-sonnet
Temperature: 0.7  (more creative output needed)
Langfuse trace name: "content_strategy"
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from agents.state import (
    AgentState,
    ContentIdea,
    DetectedSignal,
    TADAPerspective,
)

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

_langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

_llm = ChatAnthropic(
    model=os.getenv("CONTENT_STRATEGY_MODEL", "claude-3-5-sonnet-20241022"),
    temperature=0.7,
    max_tokens=4096,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

CONTENT_STRATEGY_SYSTEM_PROMPT = """You are the Content Strategist for TADA, a supply chain intelligence platform.

Your job is to transform intelligence signals into compelling, actionable content ideas that TADA can produce to demonstrate thought leadership, generate leads, and enable sales.

## TADA's Content Pillars
1. Supply Chain Intelligence — early signal detection, real-time monitoring
2. Decision Acceleration — moving from data to decision faster than competitors
3. Detect → Decide → Do — TADA's proprietary framework for operational agility
4. Executive Intelligence — curated, synthesis-ready intelligence for leadership
5. Competitive Positioning — why TADA vs. legacy ERP/SCM tools

## Audience Profiles
- **LinkedIn audience**: Supply chain professionals, procurement leaders, operations executives, logistics VPs
- **Newsletter audience**: CSCO, VP Operations, Chief Procurement Officer — time-poor, need synthesis
- **Sales content**: Account Executives, SDRs talking to VP+ in manufacturing, retail, pharma, CPG
- **Webinar audience**: Practitioners + influencers interested in supply chain innovation
- **Thought leadership**: Industry analysts, consultants, target buyers researching solutions

## Content Tone
- Authoritative but conversational (not academic)
- Data-led whenever possible (statistics, case studies, specific numbers)
- Solutions-oriented — always connect to what TADA enables
- Urgency without alarmism — "act now" not "panic"

## LinkedIn Post Angles (use all 5 varieties)
1. Contrarian: "Everyone is doing X wrong. Here's why..."
2. Data-led: "New data shows X. What it means for supply chain leaders..."
3. Story: "A CSCO I spoke with said... [hook] [insight] [CTA]"
4. Framework: "3 things supply chain leaders need to know about X..."
5. Hot-take: "Hot take: X is not a supply chain problem. It's a [intelligence/decision] problem."

Return ONLY valid JSON.
"""

CONTENT_STRATEGY_USER_TEMPLATE = """Generate a complete content strategy for the following signal.

## Signal
Signal ID: {signal_id}
Headline: {headline}
Type: {signal_type}
Summary: {summary}
Keywords: {keywords}
Entities: {entities}
Score: {score}
Momentum: {momentum}

## TADA Perspective
What Happened: {what_happened}
Why It Matters: {why_it_matters}
TADA Response: {tada_response}
Detect: {detect}
Decide: {decide}
Do: {do}
Expected Outcome: {expected_outcome}
Urgency: {urgency}

Return JSON with this exact schema:
{{
  "linkedin_posts": [
    {{
      "angle": "contrarian|data_led|story|framework|hot_take",
      "hook": "string — first line of the post (≤150 chars), must stop the scroll",
      "body_outline": "string — 3-4 bullet points or sentences for the body",
      "cta": "string — clear call to action",
      "hashtags": ["3-5 relevant hashtags"],
      "estimated_reach": "niche|moderate|broad",
      "urgency": "evergreen|timely|breaking"
    }}
  ],
  "thought_leadership_article": {{
    "title": "string — compelling article title (≤80 chars)",
    "subtitle": "string — explanatory subtitle",
    "angle": "string — unique perspective/thesis of the article",
    "target_publication": "string — e.g. Supply Chain Dive, Forbes, LinkedIn Newsletter",
    "outline": [
      "string — section heading or key point"
    ],
    "key_stat": "string — most compelling data point to anchor the article",
    "word_count": 1200,
    "keywords_seo": ["5 SEO keywords"],
    "urgency": "evergreen|timely|breaking"
  }},
  "newsletter_topic": {{
    "subject_line": "string — email subject line (≤60 chars)",
    "preview_text": "string — email preview text (≤90 chars)",
    "angle": "string — editorial angle for the newsletter section",
    "key_insight": "string — the single most important insight to share",
    "recommended_section": "string — where in a newsletter this fits (e.g. Lead Story, Signal Spotlight, Quick Takes)"
  }},
  "sales_talking_points": [
    {{
      "persona": "string — target persona (e.g. CSCO, VP Procurement, CEO)",
      "talking_point": "string — the key message in 1-2 sentences",
      "discovery_question": "string — question to open a conversation about this topic",
      "objection_bridge": "string — how to use this signal to overcome a common objection",
      "urgency_trigger": "string — why they need to act now"
    }}
  ],
  "webinar_podcast_idea": {{
    "title": "string — session title",
    "format": "webinar|podcast|panel|roundtable",
    "premise": "string — 2-3 sentence description of the session",
    "target_speaker": "string — ideal guest type or TADA expert",
    "audience": "string — who would attend",
    "key_questions": ["3-5 discussion questions"]
  }}
}}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_perspective(signal_id: str, perspectives: List[TADAPerspective]) -> Optional[TADAPerspective]:
    for p in perspectives:
        if p["signal_id"] == signal_id:
            return p
    return None


def _parse_linkedin_posts(raw_posts: List[Dict], signal_id: str) -> List[ContentIdea]:
    ideas: List[ContentIdea] = []
    for post in raw_posts[:5]:
        ideas.append(ContentIdea(
            idea_id=f"li_{uuid.uuid4().hex[:8]}",
            format="linkedin_post",
            title=post.get("hook", "")[:100],
            hook=post.get("hook", ""),
            outline=post.get("body_outline", "").split("\n") if isinstance(post.get("body_outline"), str) else [],
            key_message=post.get("body_outline", ""),
            cta=post.get("cta", ""),
            signal_id=signal_id,
            target_audience="marketing",
            estimated_reach=post.get("estimated_reach", "moderate"),
            urgency=post.get("urgency", "timely"),
        ))
    return ideas


def _parse_article(raw_article: Dict, signal_id: str) -> ContentIdea:
    return ContentIdea(
        idea_id=f"art_{uuid.uuid4().hex[:8]}",
        format="article",
        title=raw_article.get("title", ""),
        hook=raw_article.get("subtitle", ""),
        outline=raw_article.get("outline", []),
        key_message=raw_article.get("angle", ""),
        cta=f"Read in {raw_article.get('target_publication', 'your newsletter')}",
        signal_id=signal_id,
        target_audience="marketing",
        estimated_reach=raw_article.get("estimated_reach", "moderate"),
        urgency=raw_article.get("urgency", "evergreen"),
    )


def _parse_newsletter(raw_nl: Dict, signal_id: str) -> ContentIdea:
    return ContentIdea(
        idea_id=f"nl_{uuid.uuid4().hex[:8]}",
        format="newsletter",
        title=raw_nl.get("subject_line", ""),
        hook=raw_nl.get("preview_text", ""),
        outline=[raw_nl.get("key_insight", "")],
        key_message=raw_nl.get("angle", ""),
        cta="Subscribe to TADA Intelligence Digest",
        signal_id=signal_id,
        target_audience="leadership",
        estimated_reach="moderate",
        urgency="timely",
    )


def _parse_sales_ideas(raw_sales: List[Dict], signal_id: str) -> List[ContentIdea]:
    ideas: List[ContentIdea] = []
    for sp in raw_sales[:3]:
        ideas.append(ContentIdea(
            idea_id=f"sales_{uuid.uuid4().hex[:8]}",
            format="sales_deck_slide",
            title=f"[{sp.get('persona', 'Executive')}] {sp.get('talking_point', '')[:80]}",
            hook=sp.get("discovery_question", ""),
            outline=[sp.get("talking_point", ""), sp.get("objection_bridge", ""), sp.get("urgency_trigger", "")],
            key_message=sp.get("talking_point", ""),
            cta=sp.get("urgency_trigger", ""),
            signal_id=signal_id,
            target_audience="sales",
            estimated_reach="niche",
            urgency="timely",
        ))
    return ideas


def _parse_webinar(raw_wb: Dict, signal_id: str) -> ContentIdea:
    return ContentIdea(
        idea_id=f"wb_{uuid.uuid4().hex[:8]}",
        format="webinar",
        title=raw_wb.get("title", ""),
        hook=raw_wb.get("premise", ""),
        outline=raw_wb.get("key_questions", []),
        key_message=raw_wb.get("premise", ""),
        cta="Register for the live session",
        signal_id=signal_id,
        target_audience="marketing",
        estimated_reach="moderate",
        urgency="timely",
    )


# ---------------------------------------------------------------------------
# Main node function
# ---------------------------------------------------------------------------

def content_strategy_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Content Strategy

    Reads:   state["surfaced_signals"], state["tada_perspectives"]
    Writes:  state["content_ideas"], state["content_calendar_suggestions"]

    For each surfaced signal with a TADA perspective:
    1. Generates 5 LinkedIn posts (different angles)
    2. Generates 1 thought leadership article outline
    3. Generates 1 newsletter topic
    4. Generates 3 sales talking points (different personas)
    5. Generates 1 webinar/podcast topic idea

    All ideas are tagged with signal_id for traceability.
    """
    node_name = "content_strategy"
    start_time = time.time()

    trace = _langfuse.trace(
        name=node_name,
        id=f"{state['run_id']}-{node_name}",
        metadata={"run_mode": state["run_mode"]},
    )
    langfuse_handler = CallbackHandler(trace_id=trace.id)

    try:
        surfaced: List[DetectedSignal] = state.get("surfaced_signals", [])
        perspectives: List[TADAPerspective] = state.get("tada_perspectives", [])

        if not surfaced:
            return {
                **state,
                "content_ideas": [],
                "content_calendar_suggestions": [],
                "node_timings": {**state.get("node_timings", {}), node_name: time.time() - start_time},
            }

        all_ideas: List[ContentIdea] = []

        # Only generate content for top 10 signals (resource constraint)
        top_signals = surfaced[:10]

        for signal in top_signals:
            perspective = _get_perspective(signal["signal_id"], perspectives)
            if not perspective:
                continue

            span = trace.span(name=f"content_{signal['signal_id']}", input={"headline": signal["headline"]})
            try:
                user_msg = CONTENT_STRATEGY_USER_TEMPLATE.format(
                    signal_id=signal["signal_id"],
                    headline=signal["headline"],
                    signal_type=signal["signal_type"],
                    summary=signal["summary"],
                    keywords=", ".join(signal["keywords"]),
                    entities=", ".join(signal["entities"]),
                    score=signal["score"]["final_score"],
                    momentum=signal["momentum"],
                    what_happened=perspective["what_happened"],
                    why_it_matters=perspective["why_it_matters"],
                    tada_response=perspective["tada_response"],
                    detect=perspective["detect"],
                    decide=perspective["decide"],
                    do=perspective["do"],
                    expected_outcome=perspective["expected_business_outcome"],
                    urgency=perspective["urgency"],
                )

                response = _llm.invoke(
                    [
                        SystemMessage(content=CONTENT_STRATEGY_SYSTEM_PROMPT),
                        HumanMessage(content=user_msg),
                    ],
                    config={"callbacks": [langfuse_handler]},
                )

                raw_text = response.content.strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]

                parsed = json.loads(raw_text)
                signal_id = signal["signal_id"]

                # Parse all content types
                all_ideas.extend(_parse_linkedin_posts(parsed.get("linkedin_posts", []), signal_id))
                if article := parsed.get("thought_leadership_article"):
                    all_ideas.append(_parse_article(article, signal_id))
                if newsletter := parsed.get("newsletter_topic"):
                    all_ideas.append(_parse_newsletter(newsletter, signal_id))
                all_ideas.extend(_parse_sales_ideas(parsed.get("sales_talking_points", []), signal_id))
                if webinar := parsed.get("webinar_podcast_idea"):
                    all_ideas.append(_parse_webinar(webinar, signal_id))

                span.end(output={"ideas_generated": len(all_ideas)})

            except Exception as e:
                state.setdefault("errors", []).append(
                    {"node": node_name, "error": f"{signal['signal_id']}: {e}", "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                span.end(level="ERROR", status_message=str(e))

        # Build calendar suggestions (group by urgency and format)
        calendar_suggestions = _build_calendar_suggestions(all_ideas)

        trace.update(output={"total_ideas": len(all_ideas), "signals_processed": len(top_signals)})

        elapsed = time.time() - start_time
        return {
            **state,
            "content_ideas": all_ideas,
            "content_calendar_suggestions": calendar_suggestions,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }

    except Exception as e:
        elapsed = time.time() - start_time
        errors = state.get("errors", [])
        errors.append({"node": node_name, "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
        trace.event(name="node_error", level="ERROR", message=str(e))
        return {
            **state,
            "content_ideas": state.get("content_ideas", []),
            "content_calendar_suggestions": state.get("content_calendar_suggestions", []),
            "errors": errors,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }


def _build_calendar_suggestions(ideas: List[ContentIdea]) -> List[Dict[str, Any]]:
    """Generate a prioritised content calendar from all ideas."""
    # Group breaking/immediate ideas first
    breaking = [i for i in ideas if i["urgency"] == "breaking"]
    timely = [i for i in ideas if i["urgency"] == "timely"]
    evergreen = [i for i in ideas if i["urgency"] == "evergreen"]

    calendar = []
    day_offset = 0
    for idea in (breaking + timely + evergreen)[:30]:
        calendar.append({
            "day_offset": day_offset,
            "format": idea["format"],
            "title": idea["title"],
            "idea_id": idea["idea_id"],
            "signal_id": idea["signal_id"],
            "target_audience": idea["target_audience"],
            "urgency": idea["urgency"],
        })
        # LinkedIn: can post daily; articles/webinars: space out
        if idea["format"] == "linkedin_post":
            day_offset += 1
        elif idea["format"] in ("article", "webinar", "newsletter"):
            day_offset += 3
        else:
            day_offset += 2

    return calendar
