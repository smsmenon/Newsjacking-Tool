-- =============================================================================
-- TADA Content Intelligence Platform - Database Schema
-- PostgreSQL 15+ with pgvector extension
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- for full-text trigram search

-- =============================================================================
-- UTILITY: updated_at trigger function
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- CORE DATA TABLES
-- =============================================================================

-- Sources: where content is collected from
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

CREATE TRIGGER trg_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON COLUMN sources.trust_score IS 'Reliability of factual accuracy (0-1)';
COMMENT ON COLUMN sources.authority_score IS 'Domain expertise and credibility (0-1)';
COMMENT ON COLUMN sources.influence_score IS 'Reach and impact in the market (0-1)';


-- Raw content: all collected articles, posts, reports before processing
CREATE TABLE raw_content (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id       UUID NOT NULL REFERENCES sources (id) ON DELETE RESTRICT,
    title           TEXT,
    author          TEXT,
    url             TEXT NOT NULL,
    content         TEXT NOT NULL,
    published_at    TIMESTAMPTZ,
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- SHA-256 hash of normalised content for deduplication
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

COMMENT ON COLUMN raw_content.content_hash IS 'SHA-256 of normalised (lowercased, whitespace-collapsed) content for dedup';


-- Processed content: NLP analysis + embeddings for each raw article
CREATE TABLE processed_content (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_content_id      UUID NOT NULL UNIQUE REFERENCES raw_content (id) ON DELETE CASCADE,
    short_summary       TEXT,            -- 1-2 sentences
    medium_summary      TEXT,            -- 1 paragraph
    executive_summary   TEXT,            -- executive-level framing
    keywords            TEXT[] NOT NULL DEFAULT '{}',
    topics              TEXT[] NOT NULL DEFAULT '{}',
    industries          TEXT[] NOT NULL DEFAULT '{}',
    companies           TEXT[] NOT NULL DEFAULT '{}',
    risks               TEXT[] NOT NULL DEFAULT '{}',
    opportunities       TEXT[] NOT NULL DEFAULT '{}',
    geographies         TEXT[] NOT NULL DEFAULT '{}',
    technologies        TEXT[] NOT NULL DEFAULT '{}',
    sentiment_score     NUMERIC(4,3) CHECK (sentiment_score BETWEEN -1 AND 1),
    -- 1536-dim OpenAI text-embedding-3-small / ada-002 vectors
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
-- IVFFlat index for approximate nearest-neighbour cosine similarity search
CREATE INDEX idx_processed_content_embedding ON processed_content USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMENT ON COLUMN processed_content.embedding IS '1536-dim vector from OpenAI text-embedding-3-small; used for semantic search';
COMMENT ON COLUMN processed_content.sentiment_score IS '-1 (very negative) to +1 (very positive)';


-- =============================================================================
-- SIGNALS
-- =============================================================================

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
    -- Scoring dimensions (all 0-1)
    confidence_score        NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (confidence_score BETWEEN 0 AND 1),
    signal_strength         NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (signal_strength BETWEEN 0 AND 1),
    trend_momentum          NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (trend_momentum BETWEEN 0 AND 1),
    evidence_score          NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (evidence_score BETWEEN 0 AND 1),
    relevance_score         NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (relevance_score BETWEEN 0 AND 1),
    urgency_score           NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (urgency_score BETWEEN 0 AND 1),
    business_impact_score   NUMERIC(4,3) NOT NULL DEFAULT 0.5 CHECK (business_impact_score BETWEEN 0 AND 1),
    -- Strategic dimensions
    strategic_importance    TEXT CHECK (strategic_importance IN ('critical', 'high', 'medium', 'low')),
    supply_chain_relevance  NUMERIC(4,3) CHECK (supply_chain_relevance BETWEEN 0 AND 1),
    executive_importance    NUMERIC(4,3) CHECK (executive_importance BETWEEN 0 AND 1),
    technology_relevance    NUMERIC(4,3) CHECK (technology_relevance BETWEEN 0 AND 1),
    tada_alignment          NUMERIC(4,3) CHECK (tada_alignment BETWEEN 0 AND 1),
    -- Composite score for sorting/ranking (computed on write by application)
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

CREATE TRIGGER trg_signals_updated_at
    BEFORE UPDATE ON signals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON COLUMN signals.composite_score IS 'Weighted average of scoring dimensions; used for default ranking';
COMMENT ON COLUMN signals.tada_alignment IS 'How closely signal aligns with TADA product positioning (0-1)';


-- Signal <-> raw_content evidence mapping
CREATE TABLE signal_sources (
    signal_id           UUID NOT NULL REFERENCES signals (id) ON DELETE CASCADE,
    raw_content_id      UUID NOT NULL REFERENCES raw_content (id) ON DELETE CASCADE,
    relevance_weight    NUMERIC(4,3) NOT NULL DEFAULT 1.0 CHECK (relevance_weight BETWEEN 0 AND 1),
    PRIMARY KEY (signal_id, raw_content_id)
);

CREATE INDEX idx_signal_sources_raw_content_id ON signal_sources (raw_content_id);


-- =============================================================================
-- TRENDS
-- =============================================================================

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
    growth_rate         NUMERIC(6,3),         -- % week-over-week
    momentum_score      NUMERIC(4,3) CHECK (momentum_score BETWEEN 0 AND 1),
    velocity            NUMERIC(6,3),          -- signals per day
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

CREATE TRIGGER trg_trends_updated_at
    BEFORE UPDATE ON trends
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON COLUMN trends.velocity IS 'Rate of new signals per day over rolling 7-day window';
COMMENT ON COLUMN trends.growth_rate IS 'Percentage change in signal frequency week-over-week';


-- Trend <-> signal mapping
CREATE TABLE trend_signals (
    trend_id    UUID NOT NULL REFERENCES trends (id) ON DELETE CASCADE,
    signal_id   UUID NOT NULL REFERENCES signals (id) ON DELETE CASCADE,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trend_id, signal_id)
);

CREATE INDEX idx_trend_signals_signal_id ON trend_signals (signal_id);


-- =============================================================================
-- COMPETITORS
-- =============================================================================

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

CREATE TRIGGER trg_competitors_updated_at
    BEFORE UPDATE ON competitors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON COLUMN competitors.tier IS 'tier1=direct primary; tier2=secondary; tier3=niche; emerging=watch list';


-- Competitor activity events
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


-- =============================================================================
-- PAIN POINTS (from community monitoring, reviews, social)
-- =============================================================================

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
    related_signals     UUID[] NOT NULL DEFAULT '{}',   -- denormalised for fast reads
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pain_points_source_platform ON pain_points (source_platform);
CREATE INDEX idx_pain_points_frequency ON pain_points (frequency_count DESC);
CREATE INDEX idx_pain_points_categories ON pain_points USING gin (categories);
CREATE INDEX idx_pain_points_detected_at ON pain_points (detected_at DESC);

CREATE TRIGGER trg_pain_points_updated_at
    BEFORE UPDATE ON pain_points
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON COLUMN pain_points.related_signals IS 'Denormalised array of signal UUIDs for fast lookup; keep in sync with signal_sources';


-- =============================================================================
-- INTELLIGENCE OUTPUT TABLES
-- =============================================================================

-- Insights: the "so what?" layer generated from signals
CREATE TABLE insights (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id           UUID REFERENCES signals (id) ON DELETE SET NULL,
    insight_type        TEXT NOT NULL CHECK (insight_type IN (
        'market_opportunity', 'competitive_threat', 'technology_shift',
        'regulatory_risk', 'customer_need', 'strategic_recommendation',
        'executive_briefing_item', 'other'
    )),
    -- Structured insight narrative
    what_happened       TEXT NOT NULL,
    why_it_matters      TEXT NOT NULL,
    potential_impact    TEXT,
    -- TADA-specific framing
    traditional_response TEXT,
    tada_response        TEXT,
    -- DDD (Detect / Decide / Do) framework
    detect_action       TEXT,
    decide_action       TEXT,
    do_action           TEXT,
    expected_outcome    TEXT,
    -- Metadata
    model_used          TEXT NOT NULL DEFAULT 'gpt-4o',
    prompt_version      TEXT NOT NULL DEFAULT '1.0.0',
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_insights_signal_id ON insights (signal_id);
CREATE INDEX idx_insights_insight_type ON insights (insight_type);
CREATE INDEX idx_insights_generated_at ON insights (generated_at DESC);

CREATE TRIGGER trg_insights_updated_at
    BEFORE UPDATE ON insights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON COLUMN insights.detect_action IS 'Action item for the "Detect" phase of DDD framework';
COMMENT ON COLUMN insights.decide_action IS 'Action item for the "Decide" phase of DDD framework';
COMMENT ON COLUMN insights.do_action IS 'Action item for the "Do" phase of DDD framework';


-- Recommendations: team-specific action items derived from insights
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
    assigned_to             UUID,    -- references users.id; nullable (FK added after users table)
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recommendations_insight_id ON recommendations (insight_id);
CREATE INDEX idx_recommendations_team ON recommendations (team);
CREATE INDEX idx_recommendations_priority ON recommendations (priority);
CREATE INDEX idx_recommendations_status ON recommendations (status);
CREATE INDEX idx_recommendations_open ON recommendations (priority, created_at DESC) WHERE status IN ('draft', 'approved', 'in_progress');

CREATE TRIGGER trg_recommendations_updated_at
    BEFORE UPDATE ON recommendations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Content ideas: generated from signals and trends
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

CREATE TRIGGER trg_content_ideas_updated_at
    BEFORE UPDATE ON content_ideas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Content calendar: weekly/monthly planning view
CREATE TABLE content_calendar (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_start  DATE NOT NULL,
    month       SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    quarter     SMALLINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    year        SMALLINT NOT NULL,
    theme       TEXT,
    -- items: array of {content_idea_id, slot, notes}
    items       JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (week_start)
);

CREATE INDEX idx_content_calendar_year_quarter ON content_calendar (year, quarter);
CREATE INDEX idx_content_calendar_week_start ON content_calendar (week_start DESC);

CREATE TRIGGER trg_content_calendar_updated_at
    BEFORE UPDATE ON content_calendar
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- REVIEW SYSTEM
-- =============================================================================

-- Users (synced from Clerk auth)
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

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Back-fill FK on recommendations after users table exists
ALTER TABLE recommendations
    ADD CONSTRAINT fk_recommendations_assigned_to
    FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE SET NULL;


-- Review workflow: human approval for AI-generated outputs
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

CREATE TRIGGER trg_review_items_updated_at
    BEFORE UPDATE ON review_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Executive briefings: compiled intelligence reports
CREATE TABLE executive_briefings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    briefing_date           DATE NOT NULL,
    briefing_type           TEXT NOT NULL CHECK (briefing_type IN ('daily', 'weekly', 'monthly', 'quarterly', 'annual')),
    top_risks               JSONB NOT NULL DEFAULT '[]',       -- [{signal_id, title, severity}]
    top_opportunities       JSONB NOT NULL DEFAULT '[]',       -- [{signal_id, title, impact}]
    top_trends              JSONB NOT NULL DEFAULT '[]',       -- [{trend_id, name, momentum}]
    market_sentiment        NUMERIC(4,3) CHECK (market_sentiment BETWEEN -1 AND 1),
    competitor_activity     JSONB NOT NULL DEFAULT '[]',       -- [{competitor_id, name, events[]}]
    recommended_actions     JSONB NOT NULL DEFAULT '[]',       -- [{team, action, priority}]
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

CREATE TRIGGER trg_executive_briefings_updated_at
    BEFORE UPDATE ON executive_briefings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- KNOWLEDGE GRAPH
-- =============================================================================

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

CREATE TRIGGER trg_entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


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

CREATE TRIGGER trg_entity_relationships_updated_at
    BEFORE UPDATE ON entity_relationships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- USER & SYSTEM TABLES
-- =============================================================================

-- Alerts: notifications sent out via email/slack/webhook
CREATE TABLE alerts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type          TEXT NOT NULL CHECK (alert_type IN (
        'critical_signal', 'competitor_move', 'trend_emergence',
        'content_ready', 'briefing_ready', 'system_error', 'digest', 'other'
    )),
    title               TEXT NOT NULL,
    description         TEXT,
    severity            TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    channels            TEXT[] NOT NULL DEFAULT '{}',   -- ['email', 'slack', 'webhook']
    payload             JSONB NOT NULL DEFAULT '{}',    -- alert-specific data
    sent_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at     TIMESTAMPTZ,
    acknowledged_by     UUID REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX idx_alerts_severity ON alerts (severity);
CREATE INDEX idx_alerts_alert_type ON alerts (alert_type);
CREATE INDEX idx_alerts_sent_at ON alerts (sent_at DESC);
CREATE INDEX idx_alerts_unacknowledged ON alerts (severity, sent_at DESC) WHERE acknowledged_at IS NULL;


-- Source discovery: user-submitted or auto-discovered sources awaiting approval
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

CREATE TRIGGER trg_source_discovery_updated_at
    BEFORE UPDATE ON source_discovery
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ROI metrics: daily snapshot of platform value metrics
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
    -- Time saved is estimated by formula: (articles * avg_read_min) / 60
    research_hours_saved        NUMERIC(8,2) NOT NULL DEFAULT 0,
    -- Cost metrics
    llm_tokens_used             BIGINT NOT NULL DEFAULT 0,
    llm_cost_usd                NUMERIC(10,4) NOT NULL DEFAULT 0,
    -- Engagement
    briefings_published         INTEGER NOT NULL DEFAULT 0,
    recommendations_actioned    INTEGER NOT NULL DEFAULT 0,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_roi_metrics_metric_date ON roi_metrics (metric_date DESC);

COMMENT ON COLUMN roi_metrics.research_hours_saved IS 'Estimated analyst hours saved; calculated as (articles_collected * 12min) / 60';
COMMENT ON COLUMN roi_metrics.llm_cost_usd IS 'Total OpenAI/LLM API cost for the day in USD';


-- =============================================================================
-- COLLECTION JOB TRACKING
-- =============================================================================

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
