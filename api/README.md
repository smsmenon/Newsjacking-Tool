# TADA Intelligence Platform — API Reference

Base URL: `https://api.tada.ai` (production) / `http://localhost:8000` (dev)

Interactive docs: `GET /api/docs` (Swagger UI) | `GET /api/redoc`
OpenAPI spec: `GET /api/openapi.json`

---

## Authentication

All endpoints (except `/health` and webhooks) require a **Clerk JWT** passed as:

```http
Authorization: Bearer <token>
```

### Obtaining a Token

Clerk tokens are issued by the TADA frontend after the user authenticates.
For server-to-server calls (n8n, scripts), create a Clerk **Machine Token** in the Clerk dashboard.

### Validation Flow

1. Client sends `Authorization: Bearer <jwt>`
2. API fetches Clerk's JWKS (`https://api.clerk.dev/v1/jwks`) — cached in memory
3. JWT is verified using RS256 with the matching public key
4. `sub` claim is extracted as `user_id`; `org_id` and `roles` are read from `public_metadata`

### Error Responses

| Status | Meaning |
|--------|---------|
| `401 Unauthorized` | Missing, expired, or malformed JWT |
| `403 Forbidden` | Token valid but insufficient role |

---

## Rate Limiting

| Endpoint group | Limit |
|----------------|-------|
| Default | 100 req/min per user |
| `POST /api/v1/content/search` | 30 req/min |
| Webhook endpoints | 500 req/min (service account) |

Rate limit headers returned on every response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1718200000
```

---

## Request / Response Examples

### List Content

```http
GET /api/v1/content?topic=AI&min_score=0.7&page=1&page_size=10
Authorization: Bearer <token>
```

```json
{
  "items": [
    {
      "id": "018e2f3a-...",
      "title": "OpenAI releases GPT-5",
      "url": "https://openai.com/blog/gpt-5",
      "source": "openai.com",
      "topic": "AI",
      "relevance_score": 0.92,
      "status": "reviewed",
      "collected_at": "2026-06-15T09:12:00Z",
      "tags": ["llm", "product-launch"]
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 10,
    "total": 347,
    "total_pages": 35
  }
}
```

### Get Signal Detail

```http
GET /api/v1/signals/018e2f3b-dead-beef-0000-000000000001
Authorization: Bearer <token>
```

```json
{
  "id": "018e2f3b-...",
  "title": "Surge in enterprise AI adoption in Southeast Asia",
  "signal_type": "market_signal",
  "strength": 0.85,
  "confidence": 0.78,
  "status": "pending_review",
  "detected_at": "2026-06-15T08:00:00Z",
  "sources": [{ "id": "...", "title": "...", "url": "..." }],
  "review_history": []
}
```

### Review a Signal

```http
POST /api/v1/signals/018e2f3b-.../review
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "approve",
  "notes": "Verified with 3 independent sources. High confidence."
}
```

```json
{
  "id": "018e2f3b-...",
  "status": "approved",
  ...
}
```

### Update a Recommendation

```http
PATCH /api/v1/recommendations/018e2f3c-...
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "in_progress",
  "notes": "Assigned to content team, draft due Friday"
}
```

---

## Search Guide

### Endpoint

```http
POST /api/v1/content/search
```

### Search Types

#### keyword

Uses PostgreSQL `plainto_tsquery` over a GIN-indexed `tsvector` column (title + content).
Best for: exact terms, Boolean AND queries, names, product names.

```json
{
  "query": "generative AI enterprise adoption",
  "search_type": "keyword",
  "top_k": 20
}
```

#### semantic

Uses pgvector cosine similarity on `text-embedding-3-small` (1536-dim) embeddings.
Best for: paraphrase queries, conceptual search, "find similar to this idea".

```json
{
  "query": "companies integrating AI into their supply chains",
  "search_type": "semantic",
  "top_k": 20
}
```

#### hybrid (default)

Applies **Reciprocal Rank Fusion (RRF)** to combine keyword and semantic results:

```
RRF score = Σ  1 / (k + rank_i)
```

- `k` (default 60) — controls influence of lower-ranked results
- Lower `k` → sharper top-of-list bias; Higher `k` → smoother blending
- Both retrievers run over `top_k * 2` candidates before fusion

```json
{
  "query": "AI regulation Europe",
  "search_type": "hybrid",
  "top_k": 20,
  "rrf_k": 60,
  "filters": {
    "topic": ["regulation", "AI"],
    "date_from": "2026-01-01",
    "min_score": 0.5
  }
}
```

**Response** includes `search_score` (RRF), `keyword_rank`, and `semantic_rank` per result:

```json
{
  "results": [
    {
      "id": "...",
      "title": "EU AI Act enforcement begins",
      "search_score": 0.0327,
      "keyword_rank": 2,
      "semantic_rank": 1,
      "matched_excerpt": null
    }
  ],
  "query": "AI regulation Europe",
  "search_type": "hybrid",
  "total": 15,
  "took_ms": 42
}
```

---

## Webhook Guide (n8n Integration)

Webhooks use the same JWT bearer auth. Use a **Clerk Machine Token** scoped to n8n.

### Content Collected

Called by n8n when a scraping / RSS workflow finishes.

```http
POST /api/v1/webhooks/content-collected
Authorization: Bearer <machine-token>
Content-Type: application/json

{
  "source_id": "018e2f3a-...",
  "url": "https://techcrunch.com/2026/06/15/ai-news",
  "title": "Breaking: New AI model released",
  "content": "Full article text here...",
  "published_at": "2026-06-15T07:00:00Z",
  "author": "Jane Smith",
  "metadata": { "word_count": 1200, "language": "en" }
}
```

**Response:**

```json
{ "received": true, "id": "018e2f40-...", "message": "Content queued for processing" }
```

### Signal Detected

Called by a LangGraph agent when it identifies a signal in collected content.

```http
POST /api/v1/webhooks/signal-detected
Authorization: Bearer <machine-token>
Content-Type: application/json

{
  "signal_type": "market_signal",
  "title": "Rising demand for AI governance tools",
  "description": "Three independent sources in the last 24h...",
  "strength": 0.82,
  "source_content_ids": ["018e2f40-...", "018e2f41-..."],
  "langgraph_run_id": "run_abc123",
  "metadata": { "confidence": 0.79, "topics": ["AI", "governance"] }
}
```

### Alert Trigger

Called by n8n or a LangGraph agent to dispatch an alert to Slack / email / Teams.

```http
POST /api/v1/webhooks/alert-trigger
Authorization: Bearer <machine-token>
Content-Type: application/json

{
  "alert_type": "breaking_signal",
  "title": "Competitor acquired major AI startup",
  "description": "Acme Corp acquired DeepMind-spin-off for $2B...",
  "severity": "critical",
  "channels": ["slack", "email"],
  "related_item_id": "018e2f42-...",
  "related_item_type": "signal"
}
```

Alerts are **deduplicated** within a 1-hour window (same `alert_type` + `title` hash). Duplicate calls return the existing alert ID with `"deduplicated": true`.

---

## Pagination

All list endpoints support:

| Parameter | Default | Max |
|-----------|---------|-----|
| `page` | `1` | — |
| `page_size` | `20` | `100` |
| `sort_by` | endpoint-specific | — |
| `sort_order` | `desc` | — |

Response includes a `meta` object:

```json
{
  "meta": {
    "page": 2,
    "page_size": 20,
    "total": 347,
    "total_pages": 18
  }
}
```

---

## Error Format

All errors follow a consistent envelope:

```json
{
  "error": "not_found",
  "detail": "Signal with id 018e2f42-... not found",
  "request_id": "req_7f3a..."
}
```

The `X-Request-ID` header on every response matches `request_id`.

---

## Observability

- **OpenTelemetry**: spans exported to OTLP endpoint (configurable via `OTEL_ENDPOINT`)
- **Langfuse**: LLM call tracing for LangGraph agents (`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`)
- **Process time**: every response includes `X-Process-Time: <ms>ms`
- **Health**: `GET /health` returns DB connectivity status

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `CLERK_JWKS_URL` | Yes | Clerk JWKS endpoint for JWT validation |
| `OPENAI_API_KEY` | Yes | For embedding generation |
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook for alerts |
| `SENDGRID_API_KEY` | No | SendGrid for email alerts |
| `TEAMS_WEBHOOK_URL` | No | Microsoft Teams webhook for alerts |
| `OTEL_ENABLED` | No | `true` to enable OpenTelemetry (default `false`) |
| `OTEL_ENDPOINT` | No | OTLP endpoint (default `localhost:4317`) |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse project key |
