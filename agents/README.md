# TADA Intelligence Platform — AI Agent Architecture
## LangGraph Multi-Agent System

---

## Overview

The TADA agent system is a stateful multi-agent pipeline built on **LangGraph 0.2+**. Agents run as Python async functions (nodes) connected in directed graphs. State is persisted in PostgreSQL via `AsyncPostgresSaver`, enabling fault tolerance and human-in-the-loop interruptions.

All agents are observable via **Langfuse** — every run produces traces with per-node spans, token usage, latency, and cost tracking.

---

## Agent Inventory

| Agent Node | File | Model | Purpose |
|-----------|------|-------|---------|
| `content_extractor` | `nodes/content_extractor.py` | GPT-4o-mini | Extract summaries, keywords, entities from raw articles |
| `embedding_generator` | `nodes/embedding_generator.py` | text-embedding-3-small | Generate vector embeddings for semantic search |
| `signal_detector` | `nodes/signal_detection.py` | GPT-4o | Identify signals from content batches |
| `multi_source_validator` | `nodes/validator.py` | GPT-4o-mini | Cross-validate signals across multiple sources |
| `trend_updater` | `nodes/trend_updater.py` | GPT-4o-mini | Update trend frequency, momentum, velocity |
| `competitive_intel` | `nodes/competitive_intel.py` | GPT-4o | Analyze competitor content and identify gaps |
| `pain_point_extractor` | `nodes/pain_point.py` | GPT-4o-mini | Extract customer pain points from social content |
| `tada_perspective` | `nodes/tada_perspective.py` | GPT-4o | Apply TADA's Detect→Decide→Do lens |
| `recommendation_engine` | `nodes/recommendations.py` | GPT-4o-mini | Generate team-specific recommendations |
| `content_strategy` | `nodes/content_strategy.py` | GPT-4o-mini | Generate content ideas and calendar |
| `executive_briefing` | `nodes/executive_briefing.py` | GPT-4o | Compose executive briefings |
| `qa_reviewer` | `nodes/qa.py` | GPT-4o-mini | Quality gate before human review queue |
| `repository_writer` | `nodes/repository.py` | — | Store all outputs to PostgreSQL |

---

## Directory Structure

```
agents/
├── graph.py                    # Main LangGraph graph definitions (4 graphs)
├── state.py                    # AgentState TypedDict definition
├── observability.py            # Langfuse integration helpers
├── prompts/                    # Prompt templates (loaded at runtime)
│   ├── signal_detection.txt
│   ├── tada_perspective.txt
│   ├── competitive_intel.txt
│   └── ...
├── nodes/
│   ├── __init__.py
│   ├── content_extractor.py
│   ├── embedding_generator.py
│   ├── signal_detection.py
│   ├── validator.py
│   ├── trend_updater.py
│   ├── competitive_intel.py
│   ├── pain_point.py
│   ├── tada_perspective.py
│   ├── recommendations.py
│   ├── content_strategy.py
│   ├── executive_briefing.py
│   ├── qa.py
│   └── repository.py
└── README.md
```

---

## Running Agents

### Via FastAPI (primary — triggered by n8n)
```bash
# n8n calls this endpoint, which starts a LangGraph run
POST /api/v1/agents/signal-detection/run
POST /api/v1/agents/executive-briefing/run
POST /api/v1/agents/competitive-intel/run
POST /api/v1/agents/pain-point/run
```

### Manually (development/testing)
```bash
cd agents/
python -c "
import asyncio
from graph import main_pipeline

asyncio.run(main_pipeline.ainvoke({
    'content_ids': ['test-id-1', 'test-id-2'],
    'run_id': 'manual-test-001',
    'run_type': 'signal'
}))
"
```

### Resume from checkpoint
```python
# If a run was interrupted, resume using its thread_id
result = await compiled_graph.ainvoke(
    None,  # None = resume from checkpoint
    config={"configurable": {"thread_id": "run-id-here"}}
)
```

---

## Adding a New Agent

1. Create `agents/nodes/my_new_agent.py`:
```python
from ..state import AgentState
from ..observability import get_langfuse_handler

async def my_new_agent_node(state: AgentState) -> AgentState:
    """
    Brief description of what this agent does.
    
    Input:  state.field_it_reads
    Output: state.field_it_writes
    Model:  gpt-4o-mini or gpt-4o (justify choice)
    """
    handler = get_langfuse_handler(state["run_id"], "my_new_agent")
    
    # Implementation here
    
    return {**state, "new_field": result}
```

2. Add to `AgentState` TypedDict in `state.py` if new fields needed.
3. Register the node in `graph.py`:
```python
graph.add_node("my_new_agent", my_new_agent_node)
graph.add_edge("previous_node", "my_new_agent")
graph.add_edge("my_new_agent", "next_node")
```
4. Add prompt template to `agents/prompts/my_new_agent.txt`.
5. Add to Langfuse dashboard — create a custom metric if needed.

---

## Error Handling

All nodes follow this pattern:
```python
async def my_node(state: AgentState) -> AgentState:
    try:
        result = await run_with_retry(chain, inputs)
        return {**state, "output_field": result}
    except Exception as e:
        # Non-fatal: log error, continue graph with empty output
        errors = state.get("errors", [])
        errors.append(f"my_node failed: {str(e)}")
        return {**state, "errors": errors}
```

Fatal errors (e.g., DB write failure) raise and halt the graph → checkpoint preserves state → retry or manual intervention.

---

## Prompt Engineering Guidelines

1. **Always include TADA's philosophy** in system prompts — Detect→Decide→Do, outcomes over features
2. **Include negative examples** — what NOT to generate (generic AI hype, vague recommendations)
3. **Require JSON output** with strict schema — use `with_structured_output()` in LangChain
4. **Version your prompts** — use `prompt_version` field in `insights` table to track which prompt generated which output
5. **Test against golden set** — maintain `/tests/golden/` with known-good signal detection examples
6. **Monitor QA pass rate** in Langfuse — if it drops below 80%, a prompt may have regressed

---

## Human-in-the-Loop

Certain nodes use LangGraph's `interrupt()` to pause and wait for human input:

- `executive_briefing` graph: pauses after briefing generation, waits for reviewer approval
- `competitive_intel` graph: pauses after significant event detection (optional, configure per environment)

Resume flow:
1. Node calls `interrupt(payload)` → graph pauses
2. Review item created in database with `status = 'under_review'`
3. Human reviews in TADA platform → clicks Approve/Reject
4. API endpoint calls `graph.aupdate_state(config, {"action": "approved"})` + `graph.ainvoke(None, config)`
5. Graph resumes from interrupt point

---

## Observability Checklist

Before deploying any new agent node:
- [ ] Langfuse handler created per-request (not global)
- [ ] Node name is descriptive (becomes Langfuse span name)
- [ ] Token usage is tracked (automatic via LangChain callbacks)
- [ ] Latency is measured (automatic via Langfuse)
- [ ] Error is logged both to `state.errors` and Langfuse
- [ ] Cost estimate documented in node docstring
- [ ] Alert configured in Langfuse if latency > threshold
