# Builder Report: Database Schema
**Component:** PostgreSQL + pgvector Schema
**Version:** 1.0.0
**Date:** 2026-06-16
**Status:** Complete

---

## What Was Built

Four files comprising the full database layer for the TADA Content Intelligence Platform:

| File | Purpose |
|---|---|
| `database/schema.sql` | Complete production schema |
| `database/seed.sql` | Bootstrap data (20 sources, 5 competitors, 3 signals, 1 admin user) |
| `database/migrations/001_initial.sql` | Reversible migration (UP + DOWN) |
| `database/README.md` | Schema guide, index strategy, query examples |

---

## Table Count & Coverage

**22 tables** across 6 logical layers:

| Layer | Tables |
|---|---|
| Core data | `sources`, `raw_content`, `processed_content`, `collection_jobs` |
| Signals & trends | `signals`, `signal_sources`, `trends`, `trend_signals` |
| Competitive intelligence | `competitors`, `competitor_events`, `pain_points` |
| Intelligence outputs | `insights`, `recommendations`, `content_ideas`, `content_calendar`, `executive_briefings` |
| Review system | `users`, `review_items` |
| System / ops | `alerts`, `source_discovery`, `roi_metrics`, `entity_relationships`, `entities` |

---

## Index Summary

**Total indexes: 64** including:

- B-tree indexes on all foreign keys, status/type enums, and timestamp columns
- GIN indexes on all `TEXT[]` columns (keywords, topics, industries, companies, etc.)
- GIN trigram indexes on `raw_content.title` and `entities.name` (ILIKE search)
- **3 IVFFlat vector indexes** for cosine similarity (ANN search):
  - `processed_content.embedding` — lists=100 (large table)
  - `trends.embedding` — lists=50
  - `entities.embedding` — lists=50
- 7 partial indexes for high-frequency filtered queries (active sources, open recommendations, unacknowledged alerts, etc.)

---

## Key Design Decisions

### Deduplication
`raw_content.content_hash` (CHAR(64), UNIQUE) stores the SHA-256 of normalised content. Prevents duplicate storage even when the same article is collected from multiple sources.

### Composite signal score
`signals.composite_score` is a `GENERATED ALWAYS AS ... STORED` column — a weighted average of 6 scoring dimensions. Eliminates application-side computation on every read. Weights are: confidence 20%, business_impact 20%, strength/evidence/relevance/urgency 15% each.

### DDD framework in insights
The `insights` table has dedicated columns for TADA's Detect/Decide/Do framework (`detect_action`, `decide_action`, `do_action`) plus `traditional_response` vs `tada_response` for competitive positioning narratives.

### JSONB for semi-structured sections
Executive briefing sections (`top_risks`, `top_opportunities`, `top_trends`, `competitor_activity`, `recommended_actions`) are stored as JSONB arrays. Structure is defined by application layer, not enforced by DB — allowing schema evolution without migrations.

### Updated_at triggers
All mutable tables carry a `trg_*_updated_at` trigger that calls the shared `update_updated_at_column()` function. No application code needs to set this field.

### FK integrity
All foreign keys are explicitly declared with appropriate `ON DELETE` actions:
- `CASCADE` on junction tables and child records
- `SET NULL` on optional soft references (e.g., reviewer, assigned_to)
- `RESTRICT` on `raw_content.source_id` to prevent orphan content

---

## Seed Data

- **20 sources**: Harvard Business Review, MIT Technology Review, McKinsey, Gartner, Deloitte, Accenture, PwC, Forbes, TechCrunch, Wired, Supply Chain Management Review, Logistics Management, FreightWaves, LinkedIn Pulse, Reddit r/supplychain, Reddit r/logistics, US Federal Register, European Commission, Morning Brew, Stratechery
- **5 competitors**: SupplyChainIQ (tier1), LogisticsMind (tier1), FreightForce (tier2), IntelliTrade (tier2), NexusSignal (emerging)
- **3 sample signals**: AI demand forecasting adoption, EU CS3D regulatory change, SupplyChainIQ Series B
- **1 admin user**: placeholder with Clerk ID to replace on first login

---

## Production Readiness Notes

1. **IVFFlat requires minimum rows**: The embedding index on `processed_content` needs `lists * 39 = 3,900` rows before it outperforms a sequential scan. For early-stage deployment, drop and recreate the index after initial data load.

2. **HNSW upgrade path**: When `processed_content` exceeds 500k rows, replace IVFFlat with `CREATE INDEX USING hnsw (embedding vector_cosine_ops)` for better recall at scale.

3. **Partitioning candidate**: `raw_content` and `collection_jobs` will grow unboundedly. Consider range partitioning on `collected_at` by month after 6 months of production data.

4. **schema_migrations table**: The `001_initial.sql` migration creates a `schema_migrations` table for tracking applied versions. Add future migrations as `002_*.sql`, etc.

---

## Files Produced

- `/database/schema.sql` — 380 lines
- `/database/seed.sql` — 80 lines
- `/database/migrations/001_initial.sql` — 290 lines (with commented DOWN block)
- `/database/README.md` — full documentation with query examples
