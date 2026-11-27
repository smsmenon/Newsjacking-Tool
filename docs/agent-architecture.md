# Agent Architecture

## Agent Roles

### Research Agent

Purpose:

- Collect articles from approved sources
- Normalize metadata
- Validate source category
- Deduplicate by URL and content hash

Guardrails:

- Never ingest unapproved sources without admin approval
- Preserve canonical URL and publication date

### Signal Detection Agent

Purpose:

- Extract risks, disruptions, opportunities, and market changes
- Classify signal type
- Capture evidence spans

Guardrails:

- Must cite source evidence
- Must distinguish fact from inference

### Trend Analysis Agent

Purpose:

- Cluster related signals
- Calculate trend frequency and velocity
- Assign emerging, stable, or declining status

Guardrails:

- Do not declare a trend from a single weak article unless the source is a major analyst firm or breaking development

### TADA Perspective Agent

Purpose:

- Apply TADA's strategic point of view
- Translate signal into Detect, Decide, Do
- Avoid generic AI hype

Guardrails:

- Must connect to business outcomes
- Must explain why visibility alone is insufficient

### Content Strategy Agent

Purpose:

- Generate LinkedIn, article, newsletter, and content calendar ideas
- Keep outputs strategic and human-reviewable

Guardrails:

- Never claim TADA has published or endorsed a draft until reviewed
- Never create fear-based or spam-like content

### Sales Enablement Agent

Purpose:

- Convert signals into discovery questions and account conversation starters
- Tie market changes to customer pain and business impact

Guardrails:

- No unsupported customer claims
- No competitor disparagement

### Executive Briefing Agent

Purpose:

- Summarize situation, risk, opportunity, recommendation
- Produce concise leadership-ready notes

Guardrails:

- Prefer clarity over breadth
- Highlight uncertainty where appropriate

### Quality Assurance Agent

Purpose:

- Check narrative consistency
- Verify review status
- Confirm citation and evidence links
- Flag hallucination risk

Guardrails:

- Reject outputs without evidence
- Reject outputs that bypass human review

## Agent Handoff Contract

Each agent passes structured JSON:

```json
{
  "entity_id": "uuid",
  "source_evidence": ["excerpt"],
  "confidence": 0.86,
  "outputs": {},
  "warnings": []
}
```

## Recommended Agent Runtime

Use LangGraph for deterministic orchestration when:

- The sequence is predictable
- Human approval states matter
- Retry and branching logic need to be explicit

Use CrewAI-style role decomposition when:

- Running exploratory research
- Generating competing content angles
- Asking multiple agents to critique the same signal

