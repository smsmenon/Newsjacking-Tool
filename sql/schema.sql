-- TADA Supply Chain Content Intelligence Platform
-- PostgreSQL / Supabase schema. Enable pgvector in Supabase before running:
-- create extension if not exists vector;

create type review_status as enum ('draft', 'under_review', 'approved', 'rejected', 'published');
create type trend_status as enum ('emerging', 'stable', 'declining');
create type source_health_status as enum ('healthy', 'degraded', 'failed');

create table sources (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  category text not null,
  url text not null,
  rss_url text,
  access_method text not null default 'rss',
  trust_tier int not null default 2 check (trust_tier between 1 and 3),
  is_active boolean not null default true,
  health_status source_health_status not null default 'healthy',
  last_checked_at timestamptz,
  last_success_at timestamptz,
  failure_count int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table articles (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  title text not null,
  author text,
  source_name text not null,
  publication_date timestamptz,
  canonical_url text not null unique,
  content_hash text not null unique,
  category text not null,
  full_text text,
  short_summary text,
  medium_summary text,
  executive_summary text,
  keywords text[] not null default '{}',
  topics text[] not null default '{}',
  companies text[] not null default '{}',
  industries text[] not null default '{}',
  locations text[] not null default '{}',
  risks text[] not null default '{}',
  opportunities text[] not null default '{}',
  disruptions text[] not null default '{}',
  embedding vector(1536),
  ingested_at timestamptz not null default now(),
  processed_at timestamptz
);

create table signals (
  id uuid primary key default gen_random_uuid(),
  article_id uuid not null references articles(id) on delete cascade,
  headline text not null,
  signal_type text not null,
  summary text not null,
  evidence text not null,
  supply_chain_relevance numeric(4,2) not null,
  executive_importance numeric(4,2) not null,
  business_impact numeric(4,2) not null,
  technology_relevance numeric(4,2) not null,
  tada_alignment numeric(4,2) not null,
  final_score numeric(4,2) not null,
  is_breaking boolean not null default false,
  is_major_analyst_report boolean not null default false,
  surfaced boolean not null default false,
  created_at timestamptz not null default now()
);

create table tada_perspectives (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid not null references signals(id) on delete cascade,
  what_happened text not null,
  why_it_matters text not null,
  potential_impact text not null,
  traditional_response text not null,
  tada_response text not null,
  detect text not null,
  decide text not null,
  do_action text not null,
  created_at timestamptz not null default now()
);

create table content_opportunities (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid not null references signals(id) on delete cascade,
  linkedin_hook text not null,
  linkedin_narrative text not null,
  linkedin_key_insight text not null,
  linkedin_cta text not null,
  article_title text not null,
  article_executive_summary text not null,
  article_outline jsonb not null,
  article_key_arguments text[] not null,
  newsletter_headline text not null,
  newsletter_summary text not null,
  newsletter_takeaways text[] not null,
  status review_status not null default 'draft',
  reviewer text,
  reviewed_at timestamptz,
  review_comments text,
  created_at timestamptz not null default now()
);

create table sales_talking_points (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid not null references signals(id) on delete cascade,
  customer_problem text not null,
  business_impact text not null,
  recommended_discussion text not null,
  suggested_discovery_question text not null,
  status review_status not null default 'draft',
  created_at timestamptz not null default now()
);

create table executive_briefings (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid not null references signals(id) on delete cascade,
  situation text not null,
  risk text not null,
  opportunity text not null,
  recommendation text not null,
  status review_status not null default 'draft',
  created_at timestamptz not null default now()
);

create table trends (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  category text not null,
  status trend_status not null default 'emerging',
  week_over_week_delta numeric(8,2),
  month_over_month_delta numeric(8,2),
  quarter_over_quarter_delta numeric(8,2),
  signal_count int not null default 0,
  average_score numeric(4,2),
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

create table trend_signal_links (
  trend_id uuid not null references trends(id) on delete cascade,
  signal_id uuid not null references signals(id) on delete cascade,
  similarity numeric(5,4) not null,
  primary key (trend_id, signal_id)
);

create table reports (
  id uuid primary key default gen_random_uuid(),
  report_type text not null,
  period_start date not null,
  period_end date not null,
  title text not null,
  body jsonb not null,
  status review_status not null default 'draft',
  created_at timestamptz not null default now()
);

create table review_events (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  from_status review_status,
  to_status review_status not null,
  reviewer text not null,
  comments text,
  created_at timestamptz not null default now()
);

create index idx_articles_source_date on articles(source_id, publication_date desc);
create index idx_articles_topics on articles using gin(topics);
create index idx_articles_keywords on articles using gin(keywords);
create index idx_signals_score on signals(final_score desc);
create index idx_signals_type on signals(signal_type);
create index idx_content_status on content_opportunities(status);
create index idx_reports_type_period on reports(report_type, period_start, period_end);
-- create index idx_articles_embedding on articles using ivfflat (embedding vector_cosine_ops) with (lists = 100);
