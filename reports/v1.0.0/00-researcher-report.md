# Researcher Report: Technology Choices for TADA Content Intelligence Platform
**Author:** @researcher (CC_GodMode)
**Date:** 2026-06-16
**Handoff To:** @architect

---

## 1. LangGraph vs CrewAI — Multi-Agent Orchestration (Enterprise 2025)

### Summary Recommendation
**LangGraph is the clear winner for enterprise production.** CrewAI is better for rapid prototyping and simpler role-based agent pipelines, but LangGraph's stateful graph model scales better, integrates tighter with observability tooling, and has LangChain's enterprise backing.

### LangGraph
- **Version:** 0.2.x (stable as of mid-2025); part of the LangChain ecosystem
- **Model:** Directed cyclic graph (DAG + cycles allowed), state machine with typed state schemas
- **Strengths:**
  - First-class support for **human-in-the-loop** checkpoints — pause/resume execution at any node
  - **Persistent state** via checkpointers (MemorySaver, SqliteSaver, PostgresSaver) — critical for long-running enterprise workflows
  - **LangGraph Platform** (cloud/self-hosted) provides scalable task queues, cron scheduling, and webhooks
  - Fine-grained control: conditional edges, parallel fan-out/fan-in, subgraphs
  - Native Langfuse and LangSmith integration
  - **Streaming** support for token-level and node-level events
- **Gotchas:**
  - Steeper learning curve — requires understanding graph primitives
  - State schema management can become complex in large graphs; use `TypedDict` or Pydantic models strictly
  - `PostgresSaver` requires `asyncpg`; mixing sync/async is a common trap — commit to fully async
  - Subgraph communication (passing state between parent/child graphs) has edge-case bugs in <0.2 — stay on 0.2+
  - LangGraph Platform adds cost; self-hosted requires Redis for distributed queuing

### CrewAI
- **Version:** 0.70+ (mid-2025)
- **Model:** Role-based crews with autonomous task assignment
- **Strengths:** Fast to prototype, natural language task definition, built-in memory types
- **Weaknesses for Enterprise:**
  - Less control over execution flow — agents can deviate
  - Weaker checkpointing / resumability story
  - Observability tooling less mature
  - Harder to enforce deterministic pipelines

### Production Recommendation
Use **LangGraph** with `PostgresSaver` for persistence. Structure agents as graph nodes with typed state. Use `interrupt_before`/`interrupt_after` for human approval gates. Deploy LangGraph Platform (self-hosted on Kubernetes) for horizontal scaling.

---

## 2. pgvector — Hybrid Search Best Practices (PostgreSQL)

### Version
- **pgvector 0.7.x** (2025): supports HNSW and IVFFlat indexes, half-precision (`halfvec`), and binary quantization
- **PostgreSQL 15/16** recommended; PG17 adds performance improvements for vector workloads

### Hybrid Search Pattern (Vector + Keyword)
Hybrid search combines dense vector similarity with sparse keyword (BM25/tsvector) matching using **Reciprocal Rank Fusion (RRF)**.

```sql
-- Hybrid search with RRF
WITH vector_results AS (
  SELECT id, content, embedding <=> $1::vector AS vec_distance,
         ROW_NUMBER() OVER (ORDER BY embedding <=> $1::vector) AS vec_rank
  FROM documents
  ORDER BY embedding <=> $1::vector
  LIMIT 60
),
keyword_results AS (
  SELECT id, content,
         ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', $2)) AS kw_score,
         ROW_NUMBER() OVER (ORDER BY ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', $2)) DESC) AS kw_rank
  FROM documents
  WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $2)
  LIMIT 60
)
SELECT COALESCE(v.id, k.id) AS id,
       COALESCE(v.content, k.content) AS content,
       (1.0 / (60 + COALESCE(v.vec_rank, 1000))) + (1.0 / (60 + COALESCE(k.kw_rank, 1000))) AS rrf_score
FROM vector_results v
FULL OUTER JOIN keyword_results k ON v.id = k.id
ORDER BY rrf_score DESC
LIMIT 10;
```

### Index Strategy
- **HNSW** (preferred for production): `CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);`
  - Better query performance than IVFFlat; no training phase needed
  - `ef_search` can be tuned at query time: `SET hnsw.ef_search = 100;`
- **GIN index** for keyword: `CREATE INDEX ON documents USING GIN(to_tsvector('english', content));`
- Store pre-computed `tsvector` in a generated column for performance

### Key Gotchas
- **Dimensions:** pgvector supports up to 2000 dimensions natively; for 3072-dim embeddings (text-embedding-3-large), use `halfvec` (0.7+) to halve storage
- **HNSW memory:** index is held in shared memory; size `maintenance_work_mem` and `max_parallel_maintenance_workers` appropriately (8GB+ RAM for large datasets)
- **NULL embeddings** cause index corruption — add a `CHECK (embedding IS NOT NULL)` constraint
- **Cosine vs L2:** Use cosine (`<=>`) for normalized embeddings; L2 (`<->`) for unnormalized
- **Vacuum:** pgvector HNSW indexes don't auto-update deleted vectors efficiently; schedule regular `VACUUM ANALYZE`
- **Connection pooling:** Use PgBouncer in transaction mode; pgvector queries are stateless-safe

### Production Architecture
- Use **pgvector** for primary hybrid search (avoid adding a separate vector DB like Pinecone for < 10M docs)
- At > 10M documents, consider offloading to **Qdrant** or **Weaviate** and keeping PostgreSQL for metadata
- Always store raw chunks + embeddings together; avoid foreign-key joins on hot search paths
- Use `pg_stat_statements` to monitor slow vector queries

---

## 3. n8n — Self-Hosted vs Cloud for Enterprise

### Version
- **n8n 1.x** (stable 2025); significant improvements in AI node integrations and multi-main HA mode

### Self-Hosted vs Cloud Comparison

| Factor | Self-Hosted | n8n Cloud |
|---|---|---|
| Data sovereignty | Full control | Data on n8n infra |
| Compliance (HIPAA/SOC2) | Achievable with proper setup | Cloud: SOC2 Type II |
| Cost at scale | Lower (infra only) | Higher (per-execution pricing) |
| HA/Scaling | Manual (queue mode) | Managed |
| Custom nodes | Full support | Supported |
| Air-gapped | Yes | No |

### Self-Hosted Production Patterns

**Queue Mode** (recommended for enterprise):
- Architecture: Redis (queue) + PostgreSQL (persistence) + n8n worker pool
- Main process handles webhooks; workers execute workflows
- Scale workers horizontally based on queue depth
- `docker-compose` with `N8N_EXECUTIONS_MODE=queue`

**Key Environment Config:**
```env
N8N_EXECUTIONS_MODE=queue
QUEUE_BULL_REDIS_HOST=redis
DB_TYPE=postgresdb
N8N_ENCRYPTION_KEY=<32-byte-secret>  # Critical — never rotate without migration
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168  # 7 days retention
N8N_BASIC_AUTH_ACTIVE=false  # Use SSO/LDAP instead
```

**HA Multi-Main** (n8n 1.x): Multiple main instances supported behind a load balancer with Redis coordination — avoids single-point-of-failure on webhook ingestion.

### Integration Patterns for AI Platforms
- Use n8n **AI Agent nodes** (LangChain integration built-in) for no-code agent workflows
- Webhook triggers for event-driven content processing pipelines
- HTTP Request nodes to call internal FastAPI microservices
- Use **subworkflows** to create reusable processing modules
- Store credentials in n8n's encrypted credential store, not in workflow JSON

### Gotchas
- `N8N_ENCRYPTION_KEY` rotation is destructive — all stored credentials become unreadable; treat like a root key
- Default SQLite is NOT suitable for production — always use PostgreSQL
- Memory leaks in long-running workflows with large binary data — use streaming/chunked processing
- Webhook URLs change on self-hosted URL changes — use a stable domain from day one
- n8n's built-in error handling is basic; implement dead-letter queues via Redis for critical workflows
- License: **Sustainable Use License** — fair-code, not fully open source; check enterprise feature gating (SSO, LDAP, log streaming require Enterprise license)

### Recommendation
Self-host in **queue mode** on Kubernetes for enterprise. Use n8n Cloud only for non-sensitive, low-volume workflows or prototyping. Budget for **Enterprise license** if SSO and audit logs are required.

---

## 4. FastAPI + Next.js — Architecture Patterns for Intelligence/Analytics Platforms

### Stack Versions
- **FastAPI 0.115+** (Python 3.11/3.12)
- **Next.js 15** (App Router, React 19)
- **SQLAlchemy 2.x** async ORM

### Recommended Architecture

```
┌─────────────────────────────────────────────────┐
│  Next.js 15 (App Router)                        │
│  - Server Components for data fetching          │
│  - Client Components for real-time updates      │
│  - API Routes only for BFF/auth layer           │
└─────────────┬───────────────────────────────────┘
              │ REST + SSE/WebSocket
┌─────────────▼───────────────────────────────────┐
│  FastAPI Backend                                 │
│  - /api/v1/* REST endpoints                     │
│  - /api/v1/stream/* SSE for LLM streaming       │
│  - Background tasks (Celery/ARQ)                │
│  - WebSocket for real-time analytics            │
└─────────────┬───────────────────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
  PostgreSQL      Redis/Valkey
  + pgvector      (cache + queues)
```

### FastAPI Patterns

**Async-first**: Use `asyncpg` + SQLAlchemy async sessions everywhere. Never block the event loop.

```python
# Dependency injection pattern for DB sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**LLM Streaming via SSE:**
```python
@router.get("/analyze/stream")
async def stream_analysis(query: str):
    async def event_generator():
        async for chunk in llm_chain.astream({"query": query}):
            yield f"data: {json.dumps({'chunk': chunk.content})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Background AI Tasks:** Use **ARQ** (async Redis queue) for long-running analysis jobs; avoid Celery for new projects (ARQ is async-native).

### Next.js 15 Patterns

- **Server Components** for initial data load (analytics dashboards, reports) — eliminates waterfall fetches
- **`use()` hook + Suspense** for streaming AI responses in UI
- Route handlers (`/app/api/`) only for **BFF** (auth cookie forwarding, response transformation) — avoid duplicating business logic
- Use **TanStack Query** (React Query) for client-side data with optimistic updates
- **Parallel Routes** for split-panel intelligence UIs (source panel + analysis panel)

### Key Gotchas
- FastAPI's `TestClient` is sync; use `httpx.AsyncClient` with `ASGITransport` for async tests
- Next.js App Router caches aggressively — set `cache: 'no-store'` for real-time analytics endpoints
- CORS: configure FastAPI CORS middleware carefully; Next.js server components bypass browser CORS but API routes don't
- Use **Pydantic v2** (FastAPI 0.100+ default) — 5-10x faster validation; avoid mixing v1/v2 models
- For large analytics payloads, stream with SSE rather than waiting for full JSON response
- Deploy FastAPI behind **Nginx/Caddy** with `--workers` (Gunicorn + Uvicorn workers); don't expose Uvicorn directly

### Authentication Pattern
- Next.js handles session (Auth.js / NextAuth v5) — stores JWT in HttpOnly cookie
- FastAPI validates JWT on every request via dependency injection
- Never store auth state in Next.js API routes; always forward to FastAPI

---

## 5. Langfuse — LLM Observability with LangGraph Integration

### Version
- **Langfuse 3.x** (self-hosted or cloud, 2025)
- **langfuse-python SDK 3.x** with native LangChain/LangGraph callback integration

### Core Concepts
- **Traces:** top-level unit (one user request = one trace)
- **Spans:** individual steps within a trace (LLM call, tool call, retrieval)
- **Generations:** LLM-specific spans with token counts, model, prompt/completion
- **Scores:** human or automated quality scores attached to traces

### LangGraph Integration Pattern

```python
from langfuse.callback import CallbackHandler
from langgraph.graph import StateGraph

# Per-request handler (recommended over global)
def create_langfuse_handler(user_id: str, session_id: str) -> CallbackHandler:
    return CallbackHandler(
        user_id=user_id,
        session_id=session_id,
        trace_name="content-analysis-pipeline",
        tags=["production", "v1"],
        metadata={"platform": "tada"}
    )

# Pass as config to graph invocation
handler = create_langfuse_handler(user_id, session_id)
result = await graph.ainvoke(
    input_state,
    config={"callbacks": [handler]}
)
```

### Key Integration Patterns

**1. Structured Tracing per Agent Node:**
Langfuse automatically captures each LangGraph node as a span when the callback handler is passed. Node names become span names — use descriptive node names in your graph definition.

**2. Manual Instrumentation for Non-LLM Steps:**
```python
from langfuse.decorators import observe

@observe(name="pgvector-retrieval")
async def retrieve_documents(query: str, k: int = 10) -> list[Document]:
    # pgvector search logic
    ...
```

**3. Evaluation / Scoring:**
```python
langfuse_client.score(
    trace_id=handler.get_trace_id(),
    name="relevance",
    value=0.87,
    comment="Auto-scored by LLM judge"
)
```

**4. Prompt Management:**
Store and version prompts in Langfuse, fetch at runtime:
```python
prompt = langfuse_client.get_prompt("content-analyzer-v2")
compiled = prompt.compile(content=article_text)
```

**5. Dataset Experiments:**
Create golden datasets in Langfuse for regression testing when updating prompts or models.

### Self-Hosted Deployment
- Docker Compose (single machine) or Helm chart (Kubernetes)
- Requires: PostgreSQL (traces storage), ClickHouse (analytics), Redis, S3/MinIO (media)
- ClickHouse is mandatory for the analytics dashboard — resource-intensive; size accordingly (4 vCPU, 8GB RAM minimum)

### Key Gotchas
- The `CallbackHandler` is **not thread-safe** — create one per request, not per application
- Langfuse flushes traces asynchronously; in short-lived scripts/tests, call `langfuse_client.flush()` before exit
- Token counting requires the model to report usage in the LLM response; some providers don't — configure `usage` manually if needed
- Self-hosted: ClickHouse migrations can be slow on large datasets; plan maintenance windows for upgrades
- **Sampling:** for high-volume production, implement sampling at the SDK level to reduce storage costs:
  ```python
  handler = CallbackHandler(sample_rate=0.1)  # 10% sampling
  ```
- Langfuse Cloud (EU/US regions) is SOC2 Type II — viable for most enterprise use cases and eliminates ClickHouse ops burden

### Recommendation
Use **Langfuse Cloud (EU)** for initial deployment to avoid ClickHouse ops overhead. Migrate to self-hosted only if data residency requirements mandate it. Always use per-request `CallbackHandler` instances, never global singletons.

---

## Cross-Cutting Recommendations

| Layer | Choice | Notes |
|---|---|---|
| Agent Orchestration | LangGraph 0.2+ | PostgresSaver for state persistence |
| Vector Search | pgvector 0.7 + HNSW | Hybrid RRF with tsvector |
| Workflow Automation | n8n self-hosted (queue mode) | Enterprise license for SSO |
| API + Frontend | FastAPI 0.115 + Next.js 15 | App Router, ARQ for background jobs |
| Observability | Langfuse 3.x (Cloud initially) | Per-request CallbackHandler |

## Handoff Notes for @architect

1. **State schema design** is the #1 LangGraph decision — define `TypedDict` schemas before building any nodes
2. **pgvector HNSW index parameters** (m, ef_construction) should be tuned based on expected document count; 10M docs needs different settings than 100K
3. **n8n encryption key** must be in secrets manager (AWS Secrets Manager / Vault) from day one
4. **FastAPI + LangGraph streaming** requires careful SSE backpressure handling on Next.js client side
5. **Langfuse trace IDs** should be propagated as request context headers for end-to-end debugging across services
