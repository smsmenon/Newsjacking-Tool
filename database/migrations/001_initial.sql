-- =============================================================================
-- Migration: 001_initial
-- TADA Content Intelligence Platform — initial schema
-- Created: 2026-06-16
-- Reversible: YES (see DOWN section at the bottom)
-- =============================================================================

-- ============================================================
-- UP
-- ============================================================

BEGIN;

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Track applied migrations
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Guard: skip if already applied
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '001_initial') THEN
        RAISE NOTICE 'Migration 001_initial already applied — skipping.';
        RETURN;
    END IF;
END
$$;

-- ----------------------------------------------------------------
-- Utility
-- ----------------------------------------------------------------

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------
-- Core data tables
-- ----------------------------------------------------------------

CREATE TABLE sources (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    type            TEXT NOT NULL CHECK (type IN ('rss', 'api', 'scrape', 'social', 'newsletter', 'podcast', 'research', 'government', 'other')),
    category        TEXT NOT NULL CHECK (category IN ('news', 'industry', 'competitor', 'social', 'research', 'government', 'analyst', 'community', 'other')),
    trust_score     NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (trust_score BETWEEN 0 AND 1),
    authority_score NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (authority_score BETWEEN 0 AND 1),
    influence_score NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (influence_score BETWEEN 0 AND 1),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_sources_type ON sources (type);
CREATE INDEX idx_sources_category ON sources (category);
CREATE INDEX idx_sources_is_active ON sources (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_sources_trust_score ON sources (trust_score DESC);
CREATE TRIGGER trg_sources_updated_at BEFORE UPDATE ON sources FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE raw_content (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id       UUID NOT NULL REFERENCES sources (id) ON DELETE RESTRICT,
    title           TEXT,
    author          TEXT,
    url             TEXT NOT NULL,
    content         TEXT NOT NULL,
    published_at    TIMESTAMPTZ,
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash    CHAR(64) NOT NULL UNIQUE,
    language        TEXT NOT NULL DEFAULT 'en',
    word_count      INTEGER GENERATED ALWAYS AS (array_length(string_to_array(trim(content), ' '), 1)) STORED,
    metadata        JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_raw_content_source_id ON raw_content (source_id);
CREATE INDEX idx_raw_content_published_at ON raw_content (published_at DESC NULLS LAST);
CREATE INDEX idx_raw_content_collected_at ON raw_content (collected_at DESC);
CREATE INDEX idx_raw_content_content_hash ON raw_content (content_hash);
CREATE INDEX idx_raw_content_title_trgm ON raw_content USING gin (title gin_trgm_ops);

CREATE TABLE processed_content (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_content_id      UUID NOT NULL UNIQUE REFERENCES raw_content (id) ON DELETE CASCADE,
    short_summary       TEXT,
    medium_summary      TEXT,
    executive_summary   TEXT,
    keywords            TEXT[] NOT NULL DEFAULT '{}',
    topics              TEXT[] NOT NULL DEFAULT '{}',
    industries          TEXT[] NOT NULL DEFAULT '{}',
    companies           TEXT[] NOT NULL DEFAULT '{}',
    risks               TEXT[] NOT NULL DEFAULT '{}',
    opportunities       TEXT[] NOT NULL DEFAULT '{}',
    geographies         TEXT[] NOT NULL DEFAULT '{}',
    technologies        TEXT[] NOT NULL DEFAULT '{}',
    sentiment_score     NUMERIC(4,3) CHECK (sentiment_score BETWEEN -1 AND 1),
    embedding           VECTOR(1536),
    model_used          TEXT NOT NULL DEFAULT 'gpt-4o',
    prompt_version      TEXT NOT NULL DEFAULT '1.0.0',
    processed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_processed_content_raw_content_id ON processed_content (raw_content_id);
CREATE INDEX idx_processed_content_processed_at ON processed_content (processed_at DESC);
CREATE INDEX idx_processed_content_industries ON processed_content USING gin (industries);
CREATE INDEX idx_processed_content_topics ON processed_content USING gin (topics);
CREATE INDEX idx_processed_content_companies ON processed_content USING gin (companies);
CREATE INDEX idx_processed_content_keywords ON processed_content USING gin (keywords);
CREATE INDEX idx_processed_content_embedding ON processed_content USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE signals (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title                   TEXT NOT NULL,
    description             TEXT NOT NULL,
    signal_type             TEXT NOT NULL CHECK (signal_type IN (
        'market_shift', 'competitor_move', 'technology_emergence',
        'regulatory_change', 'customer_pain', 'economic_indicator',
        'partnership', 'funding', 'talent_movement', 'sentiment_shift', 'other'
    )),
    status                  TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'confirmed', 'monitoring', 'resolved', 'dismissed')),
    confidence_score        NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (confidence_score BETWEEN 0 AND 1),
    signal_strength         NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (signal_strength BETWEEN 0 AND 1),
    trend_momentum          NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (trend_momentum BETWEEN 0 AND 1),
    evidence_score          NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (evidence_score BETWEEN 0 AND 1),
    relevance_score         NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (relevance_score BETWEEN 0 AND 1),
    urgency_score           NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (urgency_score BETWEEN 0 AND 1),
    business_impact_score   NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (business_impact_score BETWEEN 0 AND 1),
    strategic_importance    TEXT CHECK (strategic_importance IN ('critical', 'high', 'medium', 'low')),
    supply_chain_relevance  NUMERIC(4,3) CHECK (supply_chain_relevance BETWEEN 0 AND 1),
    executive_importance    NUMERIC(4,3) CHECK (executive_importance BETWEEN 0 AND 1),
    technology_relevance    NUMERIC(4,3) CHECK (technology_relevance BETWEEN 0 AND 1),
    tada_alignment          NUMERIC(4,3) CHECK (tada_alignment BETWEEN 0 AND 1),
    composite_score         NUMERIC(4,3) GENERATED ALWAYS AS (
        ROUND(
            (confidence_score * 0.2 + signal_strength * 0.15 + evidence_score * 0.15 +
             relevance_score * 0.15 + urgency_score * 0.15 + business_impact_score * 0.2)::NUMERIC,
            3
        )
    ) STORED,
    detected_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_signals_type ON signals (signal_type);
CREATE INDEX idx_signals_status ON signals (status);
CREATE INDEX idx_signals_composite_score ON signals (composite_score DESC);
CREATE INDEX idx_signals_detected_at ON signals (detected_at DESC);
CREATE INDEX idx_signals_strategic ON signals (strategic_importance) WHERE strategic_importance IN ('critical', 'high');
CREATE TRIGGER trg_signals_updated_at BEFORE UPDATE ON signals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE signal_sources (
    signal_id           UUID NOT NULL REFERENCES signals (id) ON DELETE CASCADE,
    raw_content_id      UUID NOT NULL REFERENCES raw_content (id) ON DELETE CASCADE,
    relevance_weight    NUMERIC(4,3) NOT NULL DEFAULT 1.0 CHECK (relevance_weight BETWEEN 0 AND 1),
    PRIMARY KEY (signal_id, raw_content_id)
);
CREATE INDEX idx_signal_sources_raw_content_id ON signal_sources (raw_content_id);

CREATE TABLE trends (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                TEXT NOT NULL UNIQUE,
    description         TEXT NOT NULL,
    category            TEXT NOT NULL CHECK (category IN (
        'technology', 'market', 'regulatory', 'economic', 'social',
        'competitive', 'customer', 'supply_chain', 'other'
    )),
    status              TEXT NOT NULL DEFAULT 'emerging' CHECK (status IN ('emerging', 'growing', 'stable', 'declining', 'dead')),
    frequency_count     INTEGER NOT NULL DEFAULT 1,
    growth_rate         NUMERIC(6,3),
    momentum_score      NUMERIC(4,3) CHECK (momentum_score BETWEEN 0 AND 1),
    velocity            NUMERIC(6,3),
    sentiment_score     NUMERIC(4,3) CHECK (sentiment_score BETWEEN -1 AND 1),
    embedding           VECTOR(1536),
    first_detected_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_trends_status ON trends (status);
CREATE INDEX idx_trends_category ON trends (category);
CREATE INDEX idx_trends_momentum ON trends (momentum_score DESC);
CREATE INDEX idx_trends_frequency ON trends (frequency_count DESC);
CREATE INDEX idx_trends_last_updated ON trends (last_updated_at DESC);
CREATE INDEX idx_trends_embedding ON trends USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE TRIGGER trg_trends_updated_at BEFORE UPDATE ON trends FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE trend_signals (
    trend_id    UUID NOT NULL REFERENCES trends (id) ON DELETE CASCADE,
    signal_id   UUID NOT NULL REFERENCES signals (id) ON DELETE CASCADE,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trend_id, signal_id)
);
CREATE INDEX idx_trend_signals_signal_id ON trend_signals (signal_id);

CREATE TABLE competitors (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL UNIQUE,
    website     TEXT,
    description TEXT,
    tier        TEXT NOT NULL DEFAULT 'tier2' CHECK (tier IN ('tier1', 'tier2', 'tier3', 'emerging')),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_competitors_tier ON competitors (tier);
CREATE INDEX idx_competitors_is_active ON competitors (is_active) WHERE is_active = TRUE;
CREATE TRIGGER trg_competitors_updated_at BEFORE UPDATE ON competitors FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE competitor_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id   UUID NOT NULL REFERENCES competitors (id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL CHECK (event_type IN (
        'product_launch', 'partnership', 'acquisition', 'funding',
        'messaging_change', 'leadership_change', 'pricing_change',
        'expansion', 'contraction', 'other'
    )),
    title           TEXT NOT NULL,
    description     TEXT,
    url             TEXT,
    source          TEXT,
    significance    TEXT CHECK (significance IN ('high', 'medium', 'low')),
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_competitor_events_competitor_id ON competitor_events (competitor_id);
CREATE INDEX idx_competitor_events_event_type ON competitor_events (event_type);
CREATE INDEX idx_competitor_events_detected_at ON competitor_events (detected_at DESC);
CREATE INDEX idx_competitor_events_high_significance ON competitor_events (competitor_id, detected_at DESC) WHERE significance = 'high';

CREATE TABLE pain_points (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    source_platform     TEXT NOT NULL CHECK (source_platform IN (
        'reddit', 'linkedin', 'twitter', 'g2', 'capterra', 'trustpilot',
        'community_forum', 'support_ticket', 'sales_call', 'survey', 'other'
    )),
    frequency_count     INTEGER NOT NULL DEFAULT 1,
    sentiment_score     NUMERIC(4,3) CHECK (sentiment_score BETWEEN -1 AND 1),
    categories          TEXT[] NOT NULL DEFAULT '{}',
    related_signals     UUID[] NOT NULL DEFAULT '{}',
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_pain_points_source_platform ON pain_points (source_platform);
CREATE INDEX idx_pain_points_frequency ON pain_points (frequency_count DESC);
CREATE INDEX idx_pain_points_categories ON pain_points USING gin (categories);
CREATE INDEX idx_pain_points_detected_at ON pain_points (detected_at DESC);
CREATE TRIGGER trg_pain_points_updated_at BEFORE UPDATE ON pain_points FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------
-- Intelligence output tables
-- ----------------------------------------------------------------

CREATE TABLE insights (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id           UUID REFERENCES signals (id) ON DELETE SET NULL,
    insight_type        TEXT NOT NULL CHECK (insight_type IN (
        'market_opportunity', 'competitive_threat', 'technology_shift',
        'regulatory_risk', 'customer_need', 'strategic_recommendation',
        'executive_briefing_item', 'other'
    )),
    what_happened       TEXT NOT NULL,
    why_it_matters      TEXT NOT NULL,
    potential_impact    TEXT,
    traditional_response TEXT,
    tada_response       TEXT,
    detect_action       TEXT,
    decide_action       TEXT,
    do_action           TEXT,
    expected_outcome    TEXT,
    model_used          TEXT NOT NULL DEFAULT 'gpt-4o',
    prompt_version      TEXT NOT NULL DEFAULT '1.0.0',
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_insights_signal_id ON insights (signal_id);
CREATE INDEX idx_insights_insight_type ON insights (insight_type);
CREATE INDEX idx_insights_generated_at ON insights (generated_at DESC);
CREATE TRIGGER trg_insights_updated_at BEFORE UPDATE ON insights FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_id    TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'analyst', 'reviewer', 'viewer')),
    team        TEXT CHECK (team IN ('marketing', 'sales', 'leadership', 'customer_success', 'product', 'partnership', 'operations')),
    preferences JSONB NOT NULL DEFAULT '{}',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_clerk_id ON users (clerk_id);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_team ON users (team);
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE recommendations (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    insight_id              UUID NOT NULL REFERENCES insights (id) ON DELETE CASCADE,
    team                    TEXT NOT NULL CHECK (team IN (
        'marketing', 'sales', 'leadership', 'customer_success',
        'product', 'partnership', 'operations', 'all'
    )),
    recommendation_text     TEXT NOT NULL,
    rationale               TEXT,
    priority                TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    effort                  TEXT CHECK (effort IN ('hours', 'days', 'weeks', 'months')),
    timeline                TEXT,
    status                  TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'in_progress', 'done', 'dismissed')),
    assigned_to             UUID REFERENCES users (id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_recommendations_insight_id ON recommendations (insight_id);
CREATE INDEX idx_recommendations_team ON recommendations (team);
CREATE INDEX idx_recommendations_priority ON recommendations (priority);
CREATE INDEX idx_recommendations_status ON recommendations (status);
CREATE INDEX idx_recommendations_open ON recommendations (priority, created_at DESC) WHERE status IN ('draft', 'approved', 'in_progress');
CREATE TRIGGER trg_recommendations_updated_at BEFORE UPDATE ON recommendations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE content_ideas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id           UUID REFERENCES signals (id) ON DELETE SET NULL,
    trend_id            UUID REFERENCES trends (id) ON DELETE SET NULL,
    content_type        TEXT NOT NULL CHECK (content_type IN (
        'linkedin_post', 'long_form_article', 'newsletter', 'executive_briefing',
        'sales_talking_points', 'webinar', 'podcast', 'research_report',
        'case_study', 'infographic', 'video_script', 'other'
    )),
    title               TEXT NOT NULL,
    outline             TEXT,
    key_messages        TEXT[] NOT NULL DEFAULT '{}',
    target_audience     TEXT,
    recommended_timing  TEXT,
    estimated_impact    TEXT CHECK (estimated_impact IN ('high', 'medium', 'low')),
    status              TEXT NOT NULL DEFAULT 'idea' CHECK (status IN ('idea', 'approved', 'in_production', 'published', 'cancelled')),
    model_used          TEXT NOT NULL DEFAULT 'gpt-4o',
    prompt_version      TEXT NOT NULL DEFAULT '1.0.0',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_content_ideas_signal_id ON content_ideas (signal_id);
CREATE INDEX idx_content_ideas_trend_id ON content_ideas (trend_id);
CREATE INDEX idx_content_ideas_content_type ON content_ideas (content_type);
CREATE INDEX idx_content_ideas_status ON content_ideas (status);
CREATE INDEX idx_content_ideas_created_at ON content_ideas (created_at DESC);
CREATE TRIGGER trg_content_ideas_updated_at BEFORE UPDATE ON content_ideas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE content_calendar (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_start  DATE NOT NULL,
    month       SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    quarter     SMALLINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    year        SMALLINT NOT NULL,
    theme       TEXT,
    items       JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (week_start)
);
CREATE INDEX idx_content_calendar_year_quarter ON content_calendar (year, quarter);
CREATE INDEX idx_content_calendar_week_start ON content_calendar (week_start DESC);
CREATE TRIGGER trg_content_calendar_updated_at BEFORE UPDATE ON content_calendar FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------
-- Review system
-- ----------------------------------------------------------------

CREATE TABLE review_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_type       TEXT NOT NULL CHECK (item_type IN ('insight', 'recommendation', 'content_idea', 'executive_briefing', 'signal')),
    item_id         UUID NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'under_review', 'approved', 'rejected', 'published', 'archived')),
    reviewer_id     UUID REFERENCES users (id) ON DELETE SET NULL,
    review_date     TIMESTAMPTZ,
    comments        TEXT,
    changes_requested TEXT,
    submitted_by    UUID REFERENCES users (id) ON DELETE SET NULL,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_review_items_item_type_id ON review_items (item_type, item_id);
CREATE INDEX idx_review_items_status ON review_items (status);
CREATE INDEX idx_review_items_reviewer_id ON review_items (reviewer_id);
CREATE INDEX idx_review_items_pending ON review_items (submitted_at DESC) WHERE status IN ('draft', 'under_review');
CREATE TRIGGER trg_review_items_updated_at BEFORE UPDATE ON review_items FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE executive_briefings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    briefing_date           DATE NOT NULL,
    briefing_type           TEXT NOT NULL CHECK (briefing_type IN ('daily', 'weekly', 'monthly', 'quarterly', 'annual')),
    top_risks               JSONB NOT NULL DEFAULT '[]',
    top_opportunities       JSONB NOT NULL DEFAULT '[]',
    top_trends              JSONB NOT NULL DEFAULT '[]',
    market_sentiment        NUMERIC(4,3) CHECK (market_sentiment BETWEEN -1 AND 1),
    competitor_activity     JSONB NOT NULL DEFAULT '[]',
    recommended_actions     JSONB NOT NULL DEFAULT '[]',
    status                  TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'under_review', 'approved', 'published')),
    model_used              TEXT NOT NULL DEFAULT 'gpt-4o',
    created_by              UUID REFERENCES users (id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (briefing_date, briefing_type)
);
CREATE INDEX idx_executive_briefings_date ON executive_briefings (briefing_date DESC);
CREATE INDEX idx_executive_briefings_type ON executive_briefings (briefing_type);
CREATE INDEX idx_executive_briefings_status ON executive_briefings (status);
CREATE TRIGGER trg_executive_briefings_updated_at BEFORE UPDATE ON executive_briefings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------
-- Knowledge graph
-- ----------------------------------------------------------------

CREATE TABLE entities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    entity_type     TEXT NOT NULL CHECK (entity_type IN (
        'company', 'technology', 'trend', 'risk', 'geography',
        'person', 'product', 'regulation', 'event', 'concept'
    )),
    description     TEXT,
    aliases         TEXT[] NOT NULL DEFAULT '{}',
    properties      JSONB NOT NULL DEFAULT '{}',
    embedding       VECTOR(1536),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name, entity_type)
);
CREATE INDEX idx_entities_entity_type ON entities (entity_type);
CREATE INDEX idx_entities_name_trgm ON entities USING gin (name gin_trgm_ops);
CREATE INDEX idx_entities_aliases ON entities USING gin (aliases);
CREATE INDEX idx_entities_embedding ON entities USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE TRIGGER trg_entities_updated_at BEFORE UPDATE ON entities FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE entity_relationships (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity_id    UUID NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    target_entity_id    UUID NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    relationship_type   TEXT NOT NULL CHECK (relationship_type IN (
        'competes_with', 'partners_with', 'acquired_by', 'influences',
        'belongs_to', 'enables', 'threatens', 'located_in', 'mentioned_with', 'other'
    )),
    strength_score      NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (strength_score BETWEEN 0 AND 1),
    evidence_count      INTEGER NOT NULL DEFAULT 1,
    properties          JSONB NOT NULL DEFAULT '{}',
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_entity_id, target_entity_id, relationship_type)
);
CREATE INDEX idx_entity_relationships_source ON entity_relationships (source_entity_id);
CREATE INDEX idx_entity_relationships_target ON entity_relationships (target_entity_id);
CREATE INDEX idx_entity_relationships_type ON entity_relationships (relationship_type);
CREATE INDEX idx_entity_relationships_strength ON entity_relationships (strength_score DESC);
CREATE TRIGGER trg_entity_relationships_updated_at BEFORE UPDATE ON entity_relationships FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------
-- System tables
-- ----------------------------------------------------------------

CREATE TABLE alerts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type          TEXT NOT NULL CHECK (alert_type IN (
        'critical_signal', 'competitor_move', 'trend_emergence',
        'content_ready', 'briefing_ready', 'system_error', 'digest', 'other'
    )),
    title               TEXT NOT NULL,
    description         TEXT,
    severity            TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    channels            TEXT[] NOT NULL DEFAULT '{}',
    payload             JSONB NOT NULL DEFAULT '{}',
    sent_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at     TIMESTAMPTZ,
    acknowledged_by     UUID REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX idx_alerts_severity ON alerts (severity);
CREATE INDEX idx_alerts_alert_type ON alerts (alert_type);
CREATE INDEX idx_alerts_sent_at ON alerts (sent_at DESC);
CREATE INDEX idx_alerts_unacknowledged ON alerts (severity, sent_at DESC) WHERE acknowledged_at IS NULL;

CREATE TABLE source_discovery (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url             TEXT NOT NULL UNIQUE,
    name            TEXT,
    type            TEXT CHECK (type IN ('rss', 'api', 'scrape', 'social', 'newsletter', 'podcast', 'research', 'government', 'other')),
    suggested_by    UUID REFERENCES users (id) ON DELETE SET NULL,
    suggestion_note TEXT,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by     UUID REFERENCES users (id) ON DELETE SET NULL,
    review_note     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_source_discovery_status ON source_discovery (status);
CREATE INDEX idx_source_discovery_created_at ON source_discovery (created_at DESC);
CREATE TRIGGER trg_source_discovery_updated_at BEFORE UPDATE ON source_discovery FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE roi_metrics (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_date                 DATE NOT NULL UNIQUE,
    articles_collected          INTEGER NOT NULL DEFAULT 0,
    sources_monitored           INTEGER NOT NULL DEFAULT 0,
    signals_detected            INTEGER NOT NULL DEFAULT 0,
    trends_detected             INTEGER NOT NULL DEFAULT 0,
    insights_generated          INTEGER NOT NULL DEFAULT 0,
    content_ideas_generated     INTEGER NOT NULL DEFAULT 0,
    sales_opportunities         INTEGER NOT NULL DEFAULT 0,
    research_hours_saved        NUMERIC(8,2) NOT NULL DEFAULT 0,
    llm_tokens_used             BIGINT NOT NULL DEFAULT 0,
    llm_cost_usd                NUMERIC(10,4) NOT NULL DEFAULT 0,
    briefings_published         INTEGER NOT NULL DEFAULT 0,
    recommendations_actioned    INTEGER NOT NULL DEFAULT 0,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_roi_metrics_metric_date ON roi_metrics (metric_date DESC);

CREATE TABLE collection_jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id       UUID NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'success', 'failed', 'skipped')),
    items_collected INTEGER NOT NULL DEFAULT 0,
    items_new       INTEGER NOT NULL DEFAULT 0,
    items_duplicate INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_collection_jobs_source_id ON collection_jobs (source_id);
CREATE INDEX idx_collection_jobs_status ON collection_jobs (status);
CREATE INDEX idx_collection_jobs_created_at ON collection_jobs (created_at DESC);
CREATE INDEX idx_collection_jobs_failed ON collection_jobs (source_id, created_at DESC) WHERE status = 'failed';

-- Mark migration as applied
INSERT INTO schema_migrations (version) VALUES ('001_initial')
    ON CONFLICT (version) DO NOTHING;

COMMIT;


-- ============================================================
-- DOWN  (paste into psql manually — NOT run automatically)
-- ============================================================
/*

BEGIN;

DROP TABLE IF EXISTS collection_jobs CASCADE;
DROP TABLE IF EXISTS roi_metrics CASCADE;
DROP TABLE IF EXISTS source_discovery CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS entity_relationships CASCADE;
DROP TABLE IF EXISTS entities CASCADE;
DROP TABLE IF EXISTS executive_briefings CASCADE;
DROP TABLE IF EXISTS review_items CASCADE;
DROP TABLE IF EXISTS content_calendar CASCADE;
DROP TABLE IF EXISTS content_ideas CASCADE;
DROP TABLE IF EXISTS recommendations CASCADE;
DROP TABLE IF EXISTS insights CASCADE;
DROP TABLE IF EXISTS pain_points CASCADE;
DROP TABLE IF EXISTS competitor_events CASCADE;
DROP TABLE IF EXISTS competitors CASCADE;
DROP TABLE IF EXISTS trend_signals CASCADE;
DROP TABLE IF EXISTS trends CASCADE;
DROP TABLE IF EXISTS signal_sources CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS processed_content CASCADE;
DROP TABLE IF EXISTS raw_content CASCADE;
DROP TABLE IF EXISTS sources CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS schema_migrations CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
DROP EXTENSION IF EXISTS "pg_trgm";
DROP EXTENSION IF EXISTS "vector";
DROP EXTENSION IF EXISTS "uuid-ossp";

COMMIT;

*/
