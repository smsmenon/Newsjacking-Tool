-- =============================================================================
-- TADA Content Intelligence Platform - Seed Data
-- Run after schema.sql
-- =============================================================================

-- =============================================================================
-- SOURCES (20 approved sources)
-- =============================================================================

INSERT INTO sources (name, url, type, category, trust_score, authority_score, influence_score) VALUES
-- Tier-1 business/tech news
('Harvard Business Review',         'https://hbr.org/feed',                     'rss',   'industry',    0.95, 0.97, 0.90),
('MIT Technology Review',           'https://www.technologyreview.com/feed',     'rss',   'research',    0.93, 0.96, 0.88),
('McKinsey Insights',               'https://www.mckinsey.com/insights/rss',     'rss',   'analyst',     0.95, 0.97, 0.92),
('Gartner Research',                'https://www.gartner.com/en/newsroom/feed',  'rss',   'analyst',     0.94, 0.96, 0.91),
('Forbes Technology',               'https://www.forbes.com/technology/feed2',   'rss',   'news',        0.82, 0.83, 0.88),
('TechCrunch',                      'https://techcrunch.com/feed/',              'rss',   'news',        0.80, 0.82, 0.90),
('Wired',                           'https://www.wired.com/feed/rss',            'rss',   'news',        0.84, 0.85, 0.87),
('Supply Chain Management Review',  'https://www.scmr.com/rss.xml',              'rss',   'industry',    0.88, 0.90, 0.75),
('Logistics Management',            'https://www.logisticsmgmt.com/rss',         'rss',   'industry',    0.86, 0.88, 0.74),
('FreightWaves',                    'https://www.freightwaves.com/news/feed',     'rss',   'industry',    0.87, 0.88, 0.80),
-- Research & analyst
('Deloitte Insights',               'https://www2.deloitte.com/us/en/insights/rss.html', 'rss', 'analyst', 0.92, 0.94, 0.89),
('Accenture Research',              'https://www.accenture.com/us-en/insights/technology/rss', 'rss', 'analyst', 0.91, 0.93, 0.88),
('PwC Strategy&',                   'https://www.pwc.com/gx/en/services/consulting/strategy/rss.html', 'rss', 'analyst', 0.91, 0.93, 0.87),
-- Social / community
('LinkedIn Pulse',                  'https://www.linkedin.com/pulse/rss',        'social', 'social',     0.65, 0.60, 0.85),
('Reddit r/supplychain',            'https://www.reddit.com/r/supplychain/.rss', 'social', 'community',  0.55, 0.50, 0.70),
('Reddit r/logistics',              'https://www.reddit.com/r/logistics/.rss',   'social', 'community',  0.55, 0.50, 0.68),
-- Government / regulatory
('US Federal Register',             'https://www.federalregister.gov/documents/feed.atom', 'government', 'government', 0.98, 0.99, 0.80),
('European Commission Press',       'https://ec.europa.eu/newsroom/all/news-releases/rss', 'government', 'government', 0.98, 0.99, 0.78),
-- Newsletters / podcasts
('Morning Brew',                    'https://www.morningbrew.com/daily/stories.rss', 'newsletter', 'news', 0.75, 0.70, 0.82),
('Stratechery',                     'https://stratechery.com/feed/',             'newsletter', 'analyst', 0.88, 0.90, 0.83)
ON CONFLICT (url) DO NOTHING;


-- =============================================================================
-- COMPETITORS (5 entries)
-- =============================================================================

INSERT INTO competitors (name, website, description, tier) VALUES
('SupplyChainIQ',   'https://www.supplychainiq.com',   'AI-driven supply chain analytics platform targeting mid-market logistics firms',             'tier1'),
('LogisticsMind',   'https://www.logisticsmind.io',    'Real-time freight intelligence and market signals SaaS',                                     'tier1'),
('FreightForce',    'https://www.freightforce.com',    'Predictive logistics platform with carrier and lane analytics',                               'tier2'),
('IntelliTrade',    'https://www.intellitrade.ai',     'Trade intelligence and regulatory monitoring tool for import/export teams',                   'tier2'),
('NexusSignal',     'https://www.nexussignal.io',      'Early-stage market intelligence startup focusing on disruption detection for supply chains',  'emerging')
ON CONFLICT (name) DO NOTHING;


-- =============================================================================
-- SAMPLE SIGNALS (3)
-- =============================================================================

INSERT INTO signals (
    title, description, signal_type, status,
    confidence_score, signal_strength, trend_momentum, evidence_score,
    relevance_score, urgency_score, business_impact_score,
    strategic_importance, tada_alignment, detected_at
) VALUES
(
    'AI-driven demand forecasting adoption accelerating in mid-market logistics',
    'Multiple reports and community discussions indicate that mid-market logistics providers (50–500 employees) are rapidly adopting AI-powered demand forecasting tools to counter inventory volatility post-pandemic. Vendor announcements and LinkedIn activity from operations directors suggest urgency.',
    'technology_emergence', 'confirmed',
    0.82, 0.78, 0.75, 0.80, 0.90, 0.70, 0.85,
    'high', 0.88,
    NOW() - INTERVAL '3 days'
),
(
    'New EU supply chain due diligence regulation takes effect Q1 2026',
    'The European Corporate Sustainability Due Diligence Directive (CS3D) imposes mandatory supply chain risk assessments for companies >1000 employees operating in EU. Non-compliance fines up to 5% of global revenue. Early compliance tools are gaining traction.',
    'regulatory_change', 'confirmed',
    0.97, 0.92, 0.85, 0.95, 0.88, 0.92, 0.90,
    'critical', 0.82,
    NOW() - INTERVAL '7 days'
),
(
    'SupplyChainIQ raises $40M Series B; accelerates enterprise sales motion',
    'Competitor SupplyChainIQ announced a $40M Series B led by Andreessen Horowitz. Funds earmarked for enterprise go-to-market expansion and integration with SAP/Oracle ERP. LinkedIn job postings confirm 20+ enterprise AE roles being hired.',
    'competitor_move', 'confirmed',
    0.95, 0.88, 0.70, 0.92, 0.85, 0.80, 0.88,
    'high', 0.75,
    NOW() - INTERVAL '1 day'
)
ON CONFLICT DO NOTHING;


-- =============================================================================
-- ADMIN USER PLACEHOLDER
-- Replace clerk_id with actual Clerk user ID after first login
-- =============================================================================

INSERT INTO users (clerk_id, email, name, role) VALUES
('REPLACE_WITH_CLERK_ID', 'admin@tadaintelligence.com', 'TADA Admin', 'admin')
ON CONFLICT (clerk_id) DO NOTHING;
