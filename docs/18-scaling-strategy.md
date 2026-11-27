# TADA Intelligence Platform — Scaling Strategy

## Overview

The platform is designed to scale incrementally. The current architecture handles 500–1,000 articles/day comfortably. This document defines the path from launch scale to 10x and 100x volume.

---

## 1. Current Architecture Limits

| Component | Current Capacity | Practical Limit |
|---|---|---|
| FastAPI (Railway Starter) | ~100 req/s | ~200 req/s before needing more RAM |
| PostgreSQL (Railway Starter) | ~100 concurrent queries | 100 connections pool |
| pgvector | Fast up to ~1M vectors | Degrades significantly above 5M |
| Redis | Session/cache store | 256MB RAM → ~500K cached keys |
| n8n | Single-node | ~500 workflow executions/hour |
| LangGraph agents | 3 concurrent | Configurable via `AGENT_CONCURRENCY` |

---

## 2. Horizontal Scaling

### 2.1 FastAPI: Railway Auto-Scaling

Railway supports horizontal scaling via replicas. Enable in `railway.toml`:

```toml
[deploy]
numReplicas = 2
healthcheckPath = "/health"
healthcheckTimeout = 30
```

**When to scale out:** When Railway CPU utilization consistently exceeds 70% or p95 latency exceeds 1 second.

For stateless scaling, ensure:
- Session state is in Redis (not in-process)
- File uploads go to Supabase (not local disk)
- Any in-memory caches use Redis

**Load balancer:** Railway handles load balancing automatically across replicas.

### 2.2 Database: Read Replicas

At 5,000+ articles/day, search queries and dashboard loads will create read pressure. Add a read replica:

**Railway PostgreSQL** (when read replicas are supported) or migrate to **Supabase** (which provides read replicas in Pro+ plans):

```python
# In database configuration:
from sqlalchemy.ext.asyncio import create_async_engine

write_engine = create_async_engine(settings.DATABASE_URL)
read_engine = create_async_engine(settings.DATABASE_READ_REPLICA_URL)

# Route read-heavy operations to replica:
async def get_read_db():
    async with AsyncSession(read_engine) as session:
        yield session

# Use on search endpoints:
@router.get("/search")
async def search(db: AsyncSession = Depends(get_read_db)):
    ...
```

Read queries to route to replica: search, signal listing, dashboard metrics, source listing.

Write queries to route to primary: signal creation, review actions, article ingestion.

### 2.3 n8n: Separate Queue Workers

At 2,000+ articles/day, n8n processing becomes the bottleneck. Move to n8n queue mode:

```env
# n8n queue mode configuration
EXECUTIONS_MODE=queue
QUEUE_BULL_REDIS_HOST=redis.railway.internal
QUEUE_BULL_REDIS_PORT=6379
QUEUE_BULL_REDIS_DB=1
```

Deploy separate **n8n worker** services (can run multiple):

```bash
# Worker command (instead of main n8n command)
n8n worker
```

The main n8n instance handles scheduling and UI; workers handle execution. Add workers as load increases.

### 2.4 Vector Search: pgvector Optimization at Scale

pgvector performance with `ivfflat` index:

```sql
-- Create IVFFlat index (for scale)
CREATE INDEX ON article_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- sqrt(row_count) is a good starting point

-- Set probes at query time (higher = more accurate, slower)
SET ivfflat.probes = 10;
```

**Tuning guidance:**
- Up to 1M vectors: `lists = 100`, `probes = 10` is a good balance
- 1M–5M vectors: `lists = 1000`, `probes = 20`
- Above 5M vectors: consider migrating to a dedicated vector store

---

## 3. Performance Optimization

### 3.1 Caching Layers

**Layer 1: Redis API response cache**

Cache expensive, frequently-read endpoints:

```python
import functools
from app.core.cache import redis_cache

@router.get("/api/v1/dashboard/executive")
@redis_cache(ttl=300, key_prefix="executive_dashboard")
async def executive_dashboard(user: dict = Depends(verify_clerk_token)):
    # Expensive aggregation — cached for 5 minutes
    ...
```

**Cache TTL strategy:**
| Data | TTL |
|---|---|
| Executive dashboard | 5 minutes |
| Signal listing (default filters) | 2 minutes |
| Source health | 1 minute |
| Search results | 30 seconds |
| User profile | 10 minutes |
| Static reference data (source list) | 1 hour |

**Layer 2: Embedding cache**

Hash article content → store embedding in DB → skip OpenAI call for duplicates or near-duplicates.

**Layer 3: Database query result cache**

For expensive aggregation queries (trend data, ROI metrics), cache results in Redis with a 15-minute TTL and refresh in background.

### 3.2 Background Job Queuing

Replace synchronous agent triggers with an async queue for resilience:

**Using ARQ (async job queue with Redis):**

```python
# Define job
async def process_article_job(ctx, article_id: str):
    await signal_detection_agent.run(article_id)
    await insight_generation_agent.run(article_id)

# Enqueue from n8n webhook
async def enqueue_article_processing(article_id: str):
    await arq_pool.enqueue_job("process_article_job", article_id)

# Worker process (separate Railway service)
# python -m app.workers.arq_worker
```

Benefits: articles queue up during spikes, workers process at sustainable rate, failed jobs retry automatically.

### 3.3 Database Query Optimization

**Index strategy for common queries:**

```sql
-- Signal listing with filters (most common query)
CREATE INDEX idx_signals_tier_created ON signals (tier, created_at DESC);
CREATE INDEX idx_signals_source_created ON signals (source_id, created_at DESC);

-- Article search by date range
CREATE INDEX idx_articles_published ON articles (published_at DESC);
CREATE INDEX idx_articles_source ON articles (source_id, published_at DESC);

-- Review queue
CREATE INDEX idx_reviews_status ON reviews (status, priority, created_at);

-- Full text search (complement to vector search)
CREATE INDEX idx_articles_fts ON articles USING gin(to_tsvector('english', title || ' ' || content));
```

**Connection pooling:** Use PgBouncer (available as Railway add-on) to pool connections, especially with multiple FastAPI replicas:

```env
DATABASE_URL=postgresql+asyncpg://pgbouncer.railway.internal:5432/tada?pool_size=20&max_overflow=10
```

### 3.4 Pagination and Cursor-Based Listing

Replace offset pagination (slow at scale) with cursor pagination for article and signal listings:

```python
# Cursor-based: efficient at any page depth
@router.get("/api/v1/signals")
async def list_signals(
    cursor: Optional[str] = None,  # Base64 encoded (id, created_at)
    limit: int = Query(default=20, le=100)
):
    query = select(Signal).order_by(Signal.created_at.desc()).limit(limit + 1)

    if cursor:
        cursor_data = decode_cursor(cursor)
        query = query.where(
            Signal.created_at < cursor_data["created_at"]
        )

    signals = await db.execute(query)
    has_more = len(signals) > limit
    next_cursor = encode_cursor(signals[-1]) if has_more else None

    return {
        "signals": signals[:limit],
        "next_cursor": next_cursor,
        "has_more": has_more
    }
```

---

## 4. Scale Milestones

### Milestone 1: Launch (0–1,000 articles/day)

**Architecture:** Current stack, no changes needed.

**Actions:**
- Monitor Railway resource usage weekly
- Ensure connection pool is properly configured (20 connections per service)
- Set OpenAI rate limit headroom (request tier increase proactively)

**Cost:** $215–$350/month

### Milestone 2: Growth (1,000–5,000 articles/day)

**Architecture changes:**
- Add Redis caching for API responses
- Add ARQ background job queue
- Add FastAPI second replica on Railway
- Tune pgvector index (`lists = 200`)
- Implement two-stage LLM routing

**When to trigger:** When p95 API latency > 1s consistently, or daily cost > $500.

**Cost:** $400–$700/month

### Milestone 3: Scale (5,000–10,000 articles/day)

**Architecture changes:**
- Add PostgreSQL read replica
- Move n8n to queue mode with 2–3 workers
- Migrate to dedicated vector store (Qdrant on Railway or Qdrant Cloud)
- Add PgBouncer for connection pooling
- Upgrade Railway plans to Pro

**When to trigger:** When pgvector search latency > 2s, or database CPU > 70%.

**Cost:** $800–$1,500/month

### Milestone 4: Enterprise (10,000+ articles/day)

**Architecture changes:**
- Evaluate moving to Kubernetes (Railway PRO or AWS EKS)
- Separate search service (Elasticsearch or Qdrant dedicated cluster)
- CDN for static assets and API responses where applicable
- Consider dedicated GPU inference for local embedding model
- Multi-region deployment for latency

**Cost:** $2,000–$5,000+/month

---

## 5. Data Growth

### Storage Growth Estimates

| Data Type | Growth Rate | Storage/Article |
|---|---|---|
| Article metadata | 500/day | ~2KB → 1MB/day |
| Article full text | 500/day | ~10KB → 5MB/day |
| Raw HTML (Supabase) | 500/day | ~50KB → 25MB/day |
| Embeddings (1536 floats) | 500/day | ~6KB → 3MB/day |
| Signals and insights | 20/day | ~5KB → 0.1MB/day |

**Total database growth:** ~10MB/day → ~3.5GB/year (manageable)
**Supabase storage growth:** ~30MB/day → ~10GB/year (within Pro plan)

### Archival Strategy

Articles older than 2 years should be archived to cold storage:

```python
# Monthly archival job (n8n scheduled workflow)
async def archive_old_articles():
    cutoff = datetime.utcnow() - timedelta(days=730)

    old_articles = await db.execute(
        select(Article).where(Article.published_at < cutoff)
    )

    # Move to Supabase cold bucket
    for article in old_articles:
        await supabase.storage.from_("articles-archive").upload(
            f"{article.id}.json",
            article.to_json()
        )

    # Remove full text from DB, keep metadata
    await db.execute(
        update(Article)
        .where(Article.published_at < cutoff)
        .values(content=None, archived=True)
    )
```

Archived articles are searchable by metadata but not by full-text or semantic similarity.

### Search Index Optimization

For text search performance, maintain optimized tsvector columns:

```sql
-- Add generated column for full-text search
ALTER TABLE articles ADD COLUMN fts_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
) STORED;

CREATE INDEX idx_articles_fts_vector ON articles USING gin(fts_vector);
```

Rebuild indexes during low-traffic periods if index bloat becomes an issue:

```sql
REINDEX INDEX CONCURRENTLY idx_articles_fts_vector;
```
