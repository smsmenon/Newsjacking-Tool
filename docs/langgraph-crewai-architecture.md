# LangGraph / CrewAI Architecture

## LangGraph Recommended Flow

```mermaid
flowchart TD
  A["Start: New Article"] --> B["Research Node"]
  B --> C["Article Processing Node"]
  C --> D["Signal Detection Node"]
  D --> E["Scoring Node"]
  E --> F{"Surface Signal?"}
  F -->|"No"| G["Store Historical Memory"]
  F -->|"Yes"| H["TADA Perspective Node"]
  H --> I["Content Strategy Node"]
  H --> J["Sales Enablement Node"]
  H --> K["Executive Briefing Node"]
  I --> L["QA Node"]
  J --> L
  K --> L
  L --> M{"Pass QA?"}
  M -->|"No"| N["Needs Revision"]
  M -->|"Yes"| O["Create Draft Review Items"]
```

## LangGraph State

```python
class IntelligenceState(TypedDict):
    article_id: str
    article: dict
    extracted: dict
    candidate_signal: dict
    score: dict
    surfaced: bool
    tada_perspective: dict
    content_opportunities: dict
    sales_talking_points: dict
    executive_briefing: dict
    qa_findings: list[dict]
    review_status: str
```

## Control Rules

- If score < 7 and not breaking and not major analyst report, store in trend memory only.
- If QA finds missing evidence, route to revision.
- If output contains unsupported claims, route to revision.
- All successful generated outputs end in `draft`.

## CrewAI Role Design

Crew:

- Research Agent
- Signal Detection Agent
- Trend Analysis Agent
- TADA Perspective Agent
- Content Strategy Agent
- Sales Enablement Agent
- Executive Briefing Agent
- QA Agent

Recommended CrewAI use cases:

- Generating multiple content angles for a high-scoring signal
- Running a critique round before human review
- Creating weekly strategic synthesis from multiple trend clusters

## Hybrid Recommendation

Use LangGraph for the production pipeline because review states and scoring gates need deterministic control. Use CrewAI-style collaboration inside selected nodes where creative synthesis benefits from multiple perspectives.

