# TADA Intelligence Platform — Database

PostgreSQL 15+ with the `pgvector` extension for vector similarity search.

---

## Schema Overview

### Core Data Layer

| Table | Purpose |
|---|---|
| `sources` | Approved content sources (RSS, API, social, etc.) |
| `raw_content` | Every collected article/post before processing |
| `processed_content` | NLP summaries, entity extraction, embeddings |
| `collection_jobs` | Audit trail for each source collection run |

### Signal & Trend Layer

| Table | Purpose |
|---|---|
| `signals` | Detected market signals with multi-dimension scoring |
| `signal_sources` | Evidence mapping: signals → raw content |
| `trends` | Aggregated, named trends emerging from signals |
| `trend_signals` | Many-to-many between trends and signals |

### Intelligence Output Layer

| Table | Purpose |
|---|---|
| `insights` | "So what?" narrative generated from signals (DDD framework) |
| `recommendations` | Team-specific action items derived from insights |
| `content_ideas` | AI-generated content concepts |
| `content_calendar` | Weekly planning view of approved content |
| `executive_briefings` | Compiled daily/weekly/monthly intelligence reports |

### Competitive Intelligence

| Table | Purpose |
|---|---|
| `competitors` | Tracked competitors with tier classification |
| `competitor_events` | Individual events (launches, funding, messaging changes) |
| `pain_points` | Customer pains detected from social/community monitoring |

### Knowledge Graph

| Table | Purpose |
|---|---|
| `entities` | Named entities (companies, technologies, geographies, etc.) |
| `entity_relationships` | Directed, typed relationships between entities |

### Review & System

| Table | Purpose |
|---|---|
| `users` | Platform users, synced from Clerk auth |
| `review_items` | Human approval workflow for AI outputs |
| `alerts` | Notification log |
| `source_discovery` | Source suggestions awaiting approval |
| `roi_metrics` | Daily snapshot of platform value metrics |

---

## Key Design Decisions

### 1. UUID primary keys
All tables use `uuid_generate_v4()` primary keys. This avoids sequential integer leakage, simplifies cross-service references, and is compatible with distributed insertion patterns.

### 2. content_hash for deduplication
`raw_content.content_hash` is a SHA-256 of normalised content (lowercased, whitespace-collapsed). The `UNIQUE` constraint ensures no article is stored twice even if collected from multiple sources.

### 3. Composite signal score as a generated column
`signals.composite_score` is a `GENERATED ALWAYS AS ... STORED` column, removing the need for application-layer calculation on read. The weights (confidence 20%, impact 20%, strength/evidence/relevance/urgency 15% each) are deliberately encoded in the schema — change them in a migration if the business model evolves.

### 4. JSONB for semi-structured data
`metadata`, `properties`, `preferences`, `payload`, `items` and the briefing section columns are JSONB. These fields vary per source type, content type, or briefing period, and are queried infrequently with exact-match patterns rather than range scans.

### 5. Array columns for multi-valued classifications
`keywords`, `topics`, `industries`, `companies`, `risks`, `opportunities`, `geographies`, `technologies`, `categories` are `TEXT[]` with GIN indexes. This allows `@>` containment queries (`WHERE topics @> ARRAY['AI']`) without a join table for these high-cardinality, low-selectivity sets.

### 6. Partial indexes
Several tables carry partial indexes that filter to the most-queried subset:
- `idx_sources_is_active` — only active sources
- `idx_signals_strategic` — only critical/high signals
- `idx_recommendations_open` — only actionable recommendations
- `idx_alerts_unacknowledged` — only pending alerts
- `idx_collection_jobs_failed` — only failed jobs

This keeps index size small and read performance high for the most common dashboard queries.

### 7. Soft-delete via status columns
Rather than hard-deleting rows, outputs (signals, insights, recommendations, content ideas) use status enum columns. This preserves history for audit and retraining.

---

## Index Strategy

### Standard B-tree indexes
Applied on all foreign keys, status/type enum columns, and timestamp columns used in ORDER BY or range filters.

### GIN indexes
Applied on all `TEXT[]` and `JSONB` columns that will be queried with containment operators (`@>`, `?`, `?|`, `?&`).

### GIN trigram indexes (`pg_trgm`)
`raw_content.title` and `entities.name` use `gin_trgm_ops` to support `ILIKE '%term%'` and similarity searches (`%` operator) efficiently.

### IVFFlat vector indexes
Three vector columns carry IVFFlat indexes tuned for cosine similarity:

| Table | lists param | Rationale |
|---|---|---|
| `processed_content.embedding` | 100 | Large table; high-recall ANN |
| `trends.embedding` | 50 | Smaller table; fewer lists needed |
| `entities.embedding` | 50 | Smaller table |

The `lists` parameter should be set to `sqrt(row_count)` as the table grows beyond 1M rows. Re-create the index with `REINDEX` or `CREATE INDEX CONCURRENTLY` after bulk loads.

---

## Vector Search Usage Guide

### Prerequisites

```sql
CREATE EXTENSION IF NOT EXISTS vector;
-- Set probes at session level for recall/speed tradeoff
SET ivfflat.probes = 10;  -- default 1; higher = slower but more accurate
```

### Semantic article search

```sql
-- Find the 10 articles most similar to a query embedding
SELECT
    rc.title,
    rc.url,
    pc.short_summary,
    1 - (pc.embedding <=> $1::vector) AS similarity
FROM processed_content pc
JOIN raw_content rc ON rc.id = pc.raw_content_id
WHERE pc.embedding IS NOT NULL
ORDER BY pc.embedding <=> $1::vector
LIMIT 10;
```

### Trend discovery from a signal

```sql
-- Find trends semantically similar to a given trend embedding
SELECT
    id,
    name,
    status,
    momentum_score,
    1 - (embedding <=> $1::vector) AS similarity
FROM trends
WHERE embedding IS NOT NULL
  AND status != 'dead'
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

### Entity similarity (knowledge graph)

```sql
-- Find entities similar to a search term embedding
SELECT
    name,
    entity_type,
    description,
    1 - (embedding <=> $1::vector) AS similarity
FROM entities
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT 20;
```

---

## Common Query Examples

### Latest high-priority signals with evidence count

```sql
SELECT
    s.title,
    s.signal_type,
    s.composite_score,
    s.strategic_importance,
    COUNT(ss.raw_content_id) AS evidence_count,
    s.detected_at
FROM signals s
LEFT JOIN signal_sources ss ON ss.signal_id = s.id
WHERE s.status IN ('new', 'confirmed')
  AND s.strategic_importance IN ('critical', 'high')
GROUP BY s.id
ORDER BY s.composite_score DESC, s.detected_at DESC
LIMIT 20;
```

### Content pipeline by status

```sql
SELECT
    ci.content_type,
    ci.title,
    ci.status,
    ri.status AS review_status,
    ci.estimated_impact,
    ci.created_at
FROM content_ideas ci
LEFT JOIN review_items ri ON ri.item_type = 'content_idea' AND ri.item_id = ci.id
ORDER BY ci.created_at DESC;
```

### Weekly briefing topics by momentum

```sql
SELECT
    t.name,
    t.category,
    t.status,
    t.momentum_score,
    t.frequency_count,
    COUNT(ts.signal_id) AS signal_count
FROM trends t
LEFT JOIN trend_signals ts ON ts.trend_id = t.id
WHERE t.status IN ('emerging', 'growing')
GROUP BY t.id
ORDER BY t.momentum_score DESC NULLS LAST, signal_count DESC
LIMIT 10;
```

### ROI summary for the past 30 days

```sql
SELECT
    SUM(articles_collected)       AS total_articles,
    SUM(signals_detected)         AS total_signals,
    SUM(content_ideas_generated)  AS total_content_ideas,
    ROUND(SUM(research_hours_saved), 1) AS hours_saved,
    ROUND(SUM(llm_cost_usd), 2)   AS total_llm_cost_usd
FROM roi_metrics
WHERE metric_date >= CURRENT_DATE - INTERVAL '30 days';
```

### Competitor activity feed (last 7 days)

```sql
SELECT
    c.name AS competitor,
    c.tier,
    ce.event_type,
    ce.title,
    ce.significance,
    ce.detected_at
FROM competitor_events ce
JOIN competitors c ON c.id = ce.competitor_id
WHERE ce.detected_at >= NOW() - INTERVAL '7 days'
ORDER BY ce.detected_at DESC;
```

---

## Setup

```bash
# 1. Create database
createdb tada_intelligence

# 2. Apply schema
psql tada_intelligence < database/schema.sql

# 3. Apply seed data
psql tada_intelligence < database/seed.sql

# 4. Or use the migration runner
psql tada_intelligence < database/migrations/001_initial.sql
```

### Environment variable

```
DATABASE_URL=postgresql://user:password@localhost:5432/tada_intelligence
```

---

## Performance Notes

- Run `VACUUM ANALYZE` after large bulk imports.
- The IVFFlat index on `processed_content.embedding` requires at least `lists * 39` rows to be useful. For early-stage data (< 4000 rows) you can drop the IVFFlat index and rely on sequential scan — pgvector will use exact search which is fast for small tables.
- Use `SET ivfflat.probes = 20` for higher recall at the cost of latency during embedding search.
- For production deployments with >500k rows in `processed_content`, consider upgrading to the HNSW index: `CREATE INDEX USING hnsw (embedding vector_cosine_ops)`.
