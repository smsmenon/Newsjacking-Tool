# TADA Intelligence Platform — Monitoring & Observability Guide

## Overview

TADA uses a two-layer observability strategy:
- **Langfuse** — LLM-specific observability (traces, token usage, cost, latency per agent)
- **Grafana + Prometheus** — infrastructure and application monitoring

Both layers are required for full operational visibility.

---

## 1. LLM Observability (Langfuse)

### 1.1 Integration with LangGraph Agents

Langfuse is integrated at the agent level via the `langfuse` Python SDK and LangChain callback:

```python
from langfuse.callback import CallbackHandler
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST
)

def get_langfuse_handler(trace_name: str, user_id: str = None, metadata: dict = None):
    return CallbackHandler(
        trace_name=trace_name,
        user_id=user_id,
        metadata=metadata or {}
    )

# In agent runner:
handler = get_langfuse_handler(
    trace_name="signal_detection",
    metadata={"article_id": article_id, "source": source_name}
)

result = await agent.ainvoke(
    {"article": article_content},
    config={"callbacks": [handler]}
)
```

### 1.2 Key Metrics Tracked

| Metric | Description | Alert Threshold |
|---|---|---|
| Trace latency (p50) | Median agent run time | >10s: warning |
| Trace latency (p95) | 95th percentile agent run time | >30s: alert |
| Token usage / trace | Average tokens consumed per agent run | >8000: review |
| Cost / trace | Estimated USD cost per agent run | >$0.05: review |
| Error rate | % of traces ending in error | >5%: alert |
| Daily LLM cost | Total daily spend across all agents | >2x 7-day avg: alert |

### 1.3 Custom Traces for Signal Detection Pipeline

Add generation-level tracking within each agent node:

```python
with langfuse.start_span(name="signal_extraction") as span:
    span.update(input={"article_text": article[:500]})
    result = await llm.ainvoke(signal_extraction_prompt)
    span.update(
        output=result.content,
        metadata={
            "model": "gpt-4o",
            "signal_count": len(extracted_signals),
            "confidence_avg": mean_confidence
        }
    )
```

**Trace hierarchy:**
```
signal_detection_pipeline (root trace)
├── content_preprocessing
│   └── generate_embedding
├── signal_extraction
│   └── gpt4o_call
├── signal_scoring
│   └── gpt4o_mini_call
└── insight_generation
    └── gpt4o_call
```

### 1.4 Langfuse Alerts Configuration

Navigate to Langfuse → Alerts and configure:

```yaml
alerts:
  - name: "High Latency"
    condition: p95_latency > 30000  # ms
    window: 15m
    notify: slack:#tada-alerts

  - name: "Agent Error Rate"
    condition: error_rate > 0.05
    window: 15m
    notify: slack:#tada-alerts

  - name: "Daily Cost Spike"
    condition: daily_cost > (7d_avg_daily_cost * 2)
    window: 24h
    notify: slack:#tada-alerts email:admin@tada.com
```

### 1.5 Langfuse Dashboards

Create the following views in Langfuse:

1. **Agent Performance** — latency and error rate by agent type over time
2. **Cost Tracker** — daily/weekly/monthly spend by model and agent
3. **Token Efficiency** — tokens per signal detected (lower is better)
4. **Trace Explorer** — filtered by `metadata.source` for source-specific debugging

---

## 2. Infrastructure Monitoring (Grafana + Prometheus)

### 2.1 Prometheus Metrics Exposed

The FastAPI backend exposes metrics at `/metrics` using `prometheus-fastapi-instrumentator`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

Custom metrics:

```python
from prometheus_client import Counter, Histogram, Gauge

signals_detected = Counter(
    'tada_signals_detected_total',
    'Total signals detected',
    ['source', 'signal_type', 'tier']
)

pipeline_duration = Histogram(
    'tada_pipeline_duration_seconds',
    'Duration of processing pipeline',
    ['stage'],
    buckets=[0.5, 1, 2, 5, 10, 30, 60]
)

review_queue_depth = Gauge(
    'tada_review_queue_depth',
    'Number of items awaiting review',
    ['priority']
)

articles_collected_daily = Counter(
    'tada_articles_collected_total',
    'Total articles collected',
    ['source_name', 'status']
)
```

### 2.2 Key Dashboards

#### Dashboard 1: Platform Health

**Panels:**
- API Uptime (last 30 days) — single stat, green/red
- Request rate (req/min) — time series
- Error rate (%) — time series with threshold line at 1%
- p50 / p95 / p99 response times — time series
- Active connections — gauge

**Key queries:**
```promql
# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100

# p95 response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

#### Dashboard 2: Pipeline Health

**Panels:**
- n8n workflow success rate (24h) — stat
- Articles collected today — stat
- Processing queue depth — gauge
- Workflow execution time by workflow — bar chart
- Collection failures by source — table

**Key queries:**
```promql
# Articles collected last 24h
increase(tada_articles_collected_total[24h])

# Queue depth
tada_review_queue_depth
```

#### Dashboard 3: Database Performance

**Panels:**
- Active connections vs pool max — gauge
- Query duration p95 — time series
- Cache hit rate — stat
- Storage used — gauge
- Slow queries (>1s) — table
- Replication lag (if applicable) — stat

#### Dashboard 4: Agent Performance

**Panels:**
- Agent runs per hour — time series by agent type
- Success rate by agent — bar chart
- Average run duration by agent — bar chart
- Total LLM cost today — stat (sourced from Langfuse API or custom metric)
- Errors by agent type — table

#### Dashboard 5: Business Metrics

**Panels:**
- Signals detected per day (30-day trend) — time series
- Articles processed per day — time series
- Content ideas generated per week — stat
- Active sources — stat
- Review queue throughput — time series
- Top signal categories (7 days) — pie chart

### 2.3 Alert Rules

Configure in Grafana → Alerting → Alert Rules:

```yaml
groups:
  - name: tada_critical
    interval: 1m
    rules:
      - alert: HighAPIErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) /
          rate(http_requests_total[5m]) * 100 > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API error rate above 1%"
          description: "Current error rate: {{ $value }}%"

      - alert: DatabaseConnectionsHigh
        expr: |
          pg_stat_database_numbackends / pg_settings_max_connections * 100 > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool above 80%"

      - alert: N8nWorkflowFailureRate
        expr: |
          tada_n8n_workflow_failures_total / tada_n8n_workflow_executions_total * 100 > 5
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "n8n workflow failure rate above 5%"

      - alert: AgentCostSpike
        expr: |
          tada_llm_cost_total > tada_llm_cost_baseline * 2
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "LLM cost more than 2x baseline"

      - alert: SourceCollectionFailure
        expr: |
          tada_source_collection_consecutive_failures > 3
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Source {{ $labels.source_name }} failing to collect"
```

**Alert notification channels:**
- Slack: `#tada-alerts` for warnings
- Slack: `#tada-critical` for critical
- PagerDuty (optional): for P1 incidents during off-hours

---

## 3. Application Logging

### 3.1 Structured Logging Format

All logs are emitted as JSON for easy parsing and aggregation:

```python
import structlog
import logging

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()
```

**Log format:**
```json
{
  "timestamp": "2026-06-16T10:23:45.123Z",
  "level": "info",
  "logger": "tada.api.signals",
  "event": "signal_approved",
  "signal_id": "sig_abc123",
  "reviewer_id": "user_xyz",
  "tier": "A",
  "duration_ms": 45,
  "request_id": "req_def456"
}
```

### 3.2 Log Levels by Environment

| Environment | Console Level | File Level |
|---|---|---|
| Development | DEBUG | DEBUG |
| Staging | INFO | DEBUG |
| Production | INFO | INFO |

Never log DEBUG in production — it can expose sensitive data and flood log systems.

### 3.3 Key Events to Log

| Event | Level | Fields |
|---|---|---|
| Request received | DEBUG | method, path, user_id |
| Request completed | INFO | method, path, status, duration_ms |
| Signal detected | INFO | signal_id, source, tier, score |
| Signal approved | INFO | signal_id, reviewer_id |
| Agent started | INFO | agent_type, article_id |
| Agent completed | INFO | agent_type, duration_ms, signal_count |
| Agent error | ERROR | agent_type, error_type, article_id |
| Collection started | INFO | source_name, url_count |
| Collection failed | ERROR | source_name, error, consecutive_failures |
| Authentication failure | WARNING | ip_address, reason |
| Rate limit hit | WARNING | user_id, endpoint |
| Webhook received | DEBUG | workflow_name, payload_size |

### 3.4 Log Aggregation

Railway logs are shipped to an external aggregator. Options:

**Option A: Datadog**
```bash
# Add Railway log drain
railway logs --drain datadog://api.datadoghq.com/v1/input/$DD_API_KEY
```

**Option B: Better Stack (Logtail)**
```bash
railway logs --drain logtail://in.logtail.com/$LOGTAIL_SOURCE_TOKEN
```

**Option C: Grafana Loki** (self-hosted on Railway)
Deploy `grafana/loki:latest` on Railway and configure Promtail as a sidecar.

---

## 4. Health Checks

### 4.1 /health Endpoint Design

```python
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    checks = {
        "database": await check_database(db),
        "redis": await check_redis(),
        "supabase": await check_supabase(),
        "openai": await check_openai(),
    }

    all_healthy = all(v["status"] == "ok" for v in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "dependencies": checks
    }
```

Response example:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-16T10:30:00Z",
  "version": "1.0.0",
  "dependencies": {
    "database": {"status": "ok", "latency_ms": 2},
    "redis": {"status": "ok", "latency_ms": 1},
    "supabase": {"status": "ok", "latency_ms": 45},
    "openai": {"status": "ok", "latency_ms": 120}
  }
}
```

Railway uses `/health` as the health check endpoint with a 30-second timeout. Return 200 for healthy/degraded (service still running), 503 only if the service cannot serve any requests.

### 4.2 Dependency Health Checks

```python
async def check_database(db: AsyncSession) -> dict:
    try:
        start = time.monotonic()
        await db.execute(text("SELECT 1"))
        latency = round((time.monotonic() - start) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def check_redis() -> dict:
    try:
        start = time.monotonic()
        await redis_client.ping()
        latency = round((time.monotonic() - start) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### 4.3 n8n Workflow Health Monitoring

A dedicated endpoint reports n8n workflow status:

```python
@router.get("/health/workflows")
async def workflow_health(
    user: dict = Depends(require_role("admin"))
):
    # Fetch from n8n API
    workflows = await n8n_client.get_workflow_statuses()
    return {
        "workflows": [
            {
                "name": wf["name"],
                "active": wf["active"],
                "last_execution": wf["lastExecution"],
                "last_success": wf["lastSuccess"],
                "consecutive_failures": wf["consecutiveFailures"]
            }
            for wf in workflows
        ]
    }
```

### 4.4 Source Availability Monitoring

Track collection health per source:

```sql
-- Source health view
CREATE VIEW source_health AS
SELECT
    s.id,
    s.name,
    s.url,
    COUNT(a.id) FILTER (WHERE a.created_at > NOW() - INTERVAL '24 hours') AS articles_24h,
    MAX(a.created_at) AS last_article_at,
    CASE
        WHEN MAX(a.created_at) < NOW() - INTERVAL '48 hours' THEN 'stale'
        WHEN MAX(a.created_at) < NOW() - INTERVAL '24 hours' THEN 'warning'
        ELSE 'healthy'
    END AS health_status
FROM sources s
LEFT JOIN articles a ON a.source_id = s.id
WHERE s.active = true
GROUP BY s.id, s.name, s.url;
```

The Source Health Dashboard queries this view to show which sources are stale.
