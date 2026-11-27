# TADA Intelligence Platform — Cost Estimates

## Overview

All estimates are monthly unless noted. Ranges reflect low-usage vs. high-usage scenarios at launch scale (approximately 500 articles/day, 10-20 active users).

---

## 1. Infrastructure Costs

### Hosting & Services

| Service | Plan | Monthly Cost | Notes |
|---|---|---|---|
| Vercel | Pro | $20 | Frontend hosting, custom domain, analytics |
| Railway — Backend (FastAPI) | Starter | $20–35 | 512MB RAM, auto-scaling |
| Railway — n8n | Starter | $15–25 | 512MB RAM, persistent volume |
| Railway — PostgreSQL | Starter | $10–20 | 1GB RAM, 10GB storage |
| Railway — Redis | Starter | $5–10 | 256MB RAM |
| Railway — Agent Service | Starter | $10–20 | LangGraph runners |
| Supabase | Pro | $25 | Storage, realtime, 8GB DB included |
| Clerk | Pro | $25 | Up to 10,000 monthly active users |
| Langfuse | Cloud (Free tier) | $0–49 | Free tier: 50k events/month |

**Infrastructure subtotal: $130–$229/month**

---

## 2. AI / LLM Costs

### OpenAI Pricing Reference (as of mid-2026)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| GPT-4o | $5.00 | $15.00 |
| GPT-4o-mini | $0.15 | $0.60 |
| text-embedding-3-small | $0.02 | — |
| text-embedding-3-large | $0.13 | — |

### Signal Detection (Primary cost driver)

- **Volume:** 500 articles/day × 30 days = 15,000 articles/month
- **Model:** GPT-4o for signal extraction
- **Tokens per article:** ~2,000 input (article + prompt) + ~400 output
- **Cost per article:** (2000/1M × $5) + (400/1M × $15) = $0.01 + $0.006 = $0.016
- **Monthly cost:** 15,000 × $0.016 = **$240/month**

However, not all articles warrant GPT-4o. Using a two-stage approach:
1. GPT-4o-mini pre-filter (90% of articles): 13,500 × ~$0.001 = $13.50
2. GPT-4o deep analysis (10% of articles): 1,500 × $0.016 = $24

**Optimized signal detection: ~$37/month**

### Embeddings

- 15,000 articles × 1,000 tokens (average) = 15M tokens/month
- text-embedding-3-small: 15M / 1M × $0.02 = **$0.30/month**
- Cached embeddings reduce this further (re-use for similar articles)

### TADA Perspective Engine

- ~50 insights/day × 30 = 1,500 insights/month
- GPT-4o: 3,000 input + 1,000 output per insight
- Cost: 1,500 × ((3000/1M × $5) + (1000/1M × $15)) = 1,500 × $0.030 = **$45/month**

### Content Strategy Engine

- ~100 content ideas/week × 4 = 400 ideas/month
- GPT-4o: 2,000 input + 800 output per idea
- Cost: 400 × ((2000/1M × $5) + (800/1M × $15)) = 400 × $0.022 = **$8.80/month**

### Executive Briefings

- 1 daily briefing × 30 = 30 briefings/month
- GPT-4o: 5,000 input + 2,000 output per briefing
- Cost: 30 × ((5000/1M × $5) + (2000/1M × $15)) = 30 × $0.055 = **$1.65/month**

### Search & Query

- ~200 semantic searches/day × 30 = 6,000 searches/month
- Embedding only (no LLM generation): 6,000 × 100 tokens = 0.6M tokens
- Cost: 0.6M / 1M × $0.02 = **$0.012/month** (essentially free)

### AI Cost Summary

| Use Case | Monthly Cost |
|---|---|
| Signal detection (two-stage) | $37 |
| Embeddings | $0.30 |
| Perspective Engine (insights) | $45 |
| Content Strategy Engine | $8.80 |
| Executive Briefings | $1.65 |
| Misc (knowledge graph, summaries) | $10 |
| **AI/LLM Total** | **~$103/month** |

---

## 3. Data / API Costs

| Service | Cost | Notes |
|---|---|---|
| News APIs (NewsAPI, GDELT) | $0–49/month | Free tiers often sufficient at launch |
| LinkedIn API | $0 (Developer tier) | Rate-limited; enterprise tier if needed |
| Twitter/X API | $0–100/month | Basic API tier; Pro if volume increases |
| RSS feeds | $0 | Free |
| Web scraping egress | ~$0–10 | Railway bandwidth costs |

**Data/API subtotal: $0–$159/month**

---

## 4. Total Monthly Cost Estimate

| Category | Low Estimate | High Estimate |
|---|---|---|
| Infrastructure | $130 | $229 |
| AI / LLM | $85 | $120 |
| Data / APIs | $0 | $159 |
| **Total** | **$215** | **$508** |

**Expected range at launch: $215–$350/month** (mid-range assumptions, basic news APIs)

---

## 5. Scale Projections

| Volume | Articles/Day | Expected Monthly Cost |
|---|---|---|
| Launch (current) | 500 | $215–$350 |
| 2x growth | 1,000 | $300–$500 |
| 5x growth | 2,500 | $500–$800 |
| 10x growth | 5,000 | $800–$1,400 |
| Enterprise scale | 10,000+ | $1,500–$3,000 |

At 10x volume, Railway plans will need upgrading and a dedicated vector store (Qdrant) becomes cost-effective vs. pgvector on a large database.

---

## 6. Cost Optimization Strategies

### 6.1 Two-Stage LLM Processing

Route articles to cheaper models first:

```python
async def classify_article_cost_tier(article: Article) -> str:
    # Quick heuristic check before expensive LLM call
    if article.relevance_score < 0.3:  # from keyword matching
        return "skip"
    elif article.relevance_score < 0.6:
        return "mini"  # GPT-4o-mini
    else:
        return "full"  # GPT-4o
```

Potential savings: 50–70% on signal detection costs.

### 6.2 Embedding Cache

Cache embeddings in the database — avoid re-embedding the same or near-duplicate content:

```python
async def get_or_create_embedding(text: str, text_hash: str) -> list[float]:
    # Check cache
    cached = await db.get(Embedding, text_hash)
    if cached:
        return cached.vector

    # Generate and cache
    embedding = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    await db.add(Embedding(hash=text_hash, vector=embedding.data[0].embedding))
    return embedding.data[0].embedding
```

Estimated savings: 20–40% on embedding costs.

### 6.3 Batch Processing

Use OpenAI batch API for non-real-time processing (signal detection, insight generation):

```python
# Batch up to 1000 requests per batch job
# 50% discount vs. synchronous API
response = await openai_client.batches.create(
    input_file_id=file_id,
    endpoint="/v1/chat/completions",
    completion_window="24h"
)
```

Best for: overnight briefing generation, weekly trend analysis, bulk re-scoring.

### 6.4 Model Selection by Task

| Task | Recommended Model | Rationale |
|---|---|---|
| Article pre-filtering | GPT-4o-mini | Fast, cheap, good enough |
| Signal extraction | GPT-4o | High accuracy needed |
| Insight generation | GPT-4o | Quality matters |
| Content ideas | GPT-4o-mini | Creative but not critical |
| Summaries | GPT-4o-mini | Summarization doesn't need full GPT-4o |
| Executive briefings | GPT-4o | Leadership-facing, quality critical |

### 6.5 Collection Frequency Optimization

Not all sources need to be checked every 30 minutes:

| Source Type | Collection Frequency |
|---|---|
| Breaking news (Reuters, AP) | Every 15 minutes |
| Industry news | Every 60 minutes |
| Competitor blogs | Every 4 hours |
| Academic/research | Daily |
| Social media | Every 30 minutes (during business hours only) |

Reducing off-hours collection cuts processing volume by ~30%.

### 6.6 Railway Cost Management

- Use Railway's **usage-based billing** and set spending limits
- Enable **auto-sleep** for staging environment (not production)
- Use Railway's **private networking** for service-to-service communication (no egress charges)
- Right-size services: start with 512MB RAM, scale up only when needed

---

## 7. Cost Monitoring

Set up automated cost alerts:

**OpenAI:**
- Set budget alert in OpenAI dashboard: alert at $80/month, hard limit at $150/month
- Monitor daily spend via Langfuse cost tracking

**Railway:**
- Set Railway spending limit: $200/month
- Review monthly invoice for unexpected spikes

**Vercel:**
- Monitor bandwidth usage (included 1TB/month in Pro plan)

**Monthly Cost Review Checklist:**
```
[ ] Review OpenAI spend vs. budget
[ ] Review Railway service costs
[ ] Check Supabase storage usage growth
[ ] Identify any cost anomalies from previous month
[ ] Update projections based on actual volume
[ ] Evaluate model/architecture optimizations
```
