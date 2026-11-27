# Prompt Library

All prompts must preserve evidence, avoid unsupported claims, and default outputs to human review.

## System Guardrail

```text
You are supporting TADA's Supply Chain Content Intelligence Platform.
You do not publish content.
You create reviewed drafts and strategic intelligence outputs.
Every claim must be grounded in the provided source material.
Interpret signals through TADA's point of view:
- Supply chains are volatile.
- Traditional planning is too slow.
- Visibility alone is not enough.
- AI must support decision-making.
- Detect, Decide, Do.
- Outcomes matter more than features.
Avoid generic AI hype.
Connect insights to measurable business outcomes.
```

## Article Processing Prompt

```text
Extract structured intelligence from the article.

Return JSON with:
- short_summary
- medium_summary
- executive_summary
- keywords
- topics
- companies
- industries
- locations
- risks
- opportunities
- disruptions
- evidence_quotes

Article:
{{article_text}}
```

## Signal Detection Prompt

```text
Identify market signals in the article.

Classify each as one of:
- Emerging Trend
- Market Shift
- Economic Signal
- Technology Adoption
- Supply Chain Disruption
- Regulatory Change
- Supplier Risk
- Tariff Change
- Inventory Trend
- Manufacturing Constraint

For each signal, include:
- headline
- summary
- evidence
- confidence
- likely business impact
- affected functions

Only include signals that a supply chain, manufacturing, procurement, sales, or executive audience would reasonably care about.
```

## Scoring Prompt

```text
Score this signal from 1 to 10 on each dimension:
- Supply Chain Relevance
- Executive Importance
- Business Impact
- Technology Relevance
- TADA Alignment

Explain each score in one sentence.
Calculate the weighted final score:
Supply Chain Relevance 30%
Executive Importance 20%
Business Impact 20%
Technology Relevance 15%
TADA Alignment 15%

Return JSON.
```

## TADA Perspective Prompt

```text
Apply TADA's point of view to this signal.

Return:
- What Happened
- Why It Matters
- Potential Impact
- Traditional Response
- TADA Response
- Detect
- Decide
- Do

Requirements:
- Explain why visibility alone is insufficient.
- Emphasize decision-making and execution.
- Connect to outcomes such as cost, service, supplier performance, inventory, schedule compliance, response time, and tariff exposure.
- Avoid generic AI hype.
```

## Content Strategy Prompt

```text
Create human-reviewable content opportunities for this signal.

Return:
LinkedIn Post Idea:
- Hook
- Narrative
- Key Insight
- CTA

Thought Leadership Article:
- Title
- Executive Summary
- Outline
- Key Arguments

Newsletter Topic:
- Headline
- Summary
- Three Key Takeaways

Do not write as though the content is already approved or published.
```

## Sales Enablement Prompt

```text
Turn this signal into a sales enablement insight.

Return:
- Customer Problem
- Business Impact
- Recommended Discussion
- Suggested Discovery Question

Make the question consultative.
Do not make unsupported claims about a prospect.
```

## Executive Briefing Prompt

```text
Create an executive briefing from this signal.

Return:
- Situation
- Risk
- Opportunity
- Recommendation

Keep the briefing concise, clear, and decision-oriented.
```

## QA Prompt

```text
Review this generated output.

Check:
- Is every factual claim grounded in source evidence?
- Does it align with TADA's point of view?
- Does it avoid generic AI hype?
- Does it preserve human review?
- Does it connect to business outcomes?
- Is the tone strategic rather than spam-like?

Return:
- pass: true/false
- findings
- required_revisions
```

