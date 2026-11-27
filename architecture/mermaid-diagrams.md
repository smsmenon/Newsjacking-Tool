# TADA Content Intelligence Platform — Mermaid Diagrams

**Version:** 1.0.0
**Date:** 2026-06-16

Eight production-grade diagrams covering every architectural dimension of the TADA platform.

---

## Diagram 1: System Overview (C4 Context)

```mermaid
C4Context
    title TADA Content Intelligence Platform — System Context

    Person(analyst, "Intelligence Analyst", "Monitors signals, reviews insights, manages sources")
    Person(reviewer, "Content Reviewer", "Approves/rejects insights before publication")
    Person(executive, "Executive", "Views briefings, risks, opportunities, actions")
    Person(sales, "Sales Team", "Receives signal-based sales intelligence")

    System(tada, "TADA Intelligence Platform", "Monitors 50+ sources, detects signals, generates strategic insights through Detect→Decide→Do framework. All outputs require human review.")

    System_Ext(rss, "RSS / Atom Feeds", "Industry news, analyst blogs, company announcements")
    System_Ext(social, "Social Platforms", "Twitter/X, LinkedIn, Reddit")
    System_Ext(apis, "External APIs", "News APIs, financial data, regulatory feeds")
    System_Ext(podcast, "Podcast / Video", "Industry podcasts, YouTube channels")
    System_Ext(slack, "Slack / Teams", "Alert delivery channel")
    System_Ext(email, "Email", "Newsletter ingestion + alert delivery")
    System_Ext(clerk, "Clerk Auth", "Identity and access management")

    Rel(analyst, tada, "Browses signals, manages sources, submits for review")
    Rel(reviewer, tada, "Reviews and approves insights")
    Rel(executive, tada, "Reads briefings and alerts")
    Rel(sales, tada, "Receives sales intelligence")

    Rel(tada, rss, "Polls every 15 min")
    Rel(tada, social, "Polls every 30-60 min")
    Rel(tada, apis, "Polls every 1 hr")
    Rel(tada, podcast, "Processes every 24 hr")
    Rel(tada, email, "Ingests via IMAP every 4 hr")
    Rel(tada, slack, "Pushes breaking alerts")
    Rel(tada, email, "Sends digest alerts")
    Rel(clerk, tada, "Authenticates all users")
```

---

## Diagram 2: Module Architecture (Component Diagram)

```mermaid
graph TB
    subgraph COLLECTION["COLLECTION LAYER (Modules 1-3)"]
        M01[01 Data Collection Engine<br/>RSS · API · Scrape · Social · Podcast · Video]
        M02[02 Source Quality Engine<br/>Trust · Authority · Influence Scoring]
        M03[03 Content Extraction Engine<br/>Summary · Keywords · Entities · Embeddings]
    end

    subgraph SIGNAL["SIGNAL INTELLIGENCE (Modules 4-7)"]
        M04[04 Signal Detection Engine<br/>Anomaly · Event Taxonomy · Pattern Match]
        M05[05 Multi-Source Validation<br/>Cross-source Confirmation · Confidence]
        M06[06 Trend Engine<br/>Frequency · Momentum · Velocity]
        M07[07 Pain Point Detection<br/>Reddit · LinkedIn · X Sentiment]
    end

    subgraph INTELLIGENCE["INTELLIGENCE GENERATION (Modules 8-10)"]
        M08[08 Relevance Scoring<br/>Supply Chain 30% · Executive 20%<br/>Business 20% · Tech 15% · TADA 15%]
        M09[09 TADA Perspective Engine<br/>What · Why · Impact<br/>Traditional Response · TADA Response · D-D-D]
        M10[10 Strategic Recommendation Engine<br/>Marketing · Sales · Leadership · CS · Product]
    end

    subgraph CONTENT["CONTENT & CALENDAR (Modules 11-12)"]
        M11[11 Content Strategy Engine<br/>LinkedIn · Articles · Newsletters · Briefings]
        M12[12 Content Calendar Engine<br/>Weekly · Monthly · Quarterly]
    end

    subgraph KNOWLEDGE["KNOWLEDGE INFRASTRUCTURE (Modules 13-17)"]
        M13[13 Knowledge Repository<br/>Permanent · Append-only · Never Delete]
        M14[14 MI Explorer<br/>Browsable Portal]
        M15[15 Advanced Search<br/>Keyword · Semantic · Hybrid · Vector]
        M16[16 Knowledge Graph<br/>Entity Relationship Maps]
        M17[17 Trend Timeline<br/>Longitudinal Visualization]
    end

    subgraph DECISION["DECISION SUPPORT & OPS (Modules 18-21)"]
        M18[18 Executive Portal<br/>Risks · Opportunities · Trends · Actions]
        M19[19 Alerting System<br/>Slack · Teams · Email · WebSocket]
        M20[20 Human Review System<br/>Draft → Review → Approved → Published]
        M21[21 AI Agent Architecture<br/>13 Specialized Agents]
    end

    M01 --> M02
    M01 --> M03
    M02 -.->|quality score| M03
    M03 --> M04
    M04 --> M05
    M05 --> M06
    M05 --> M07
    M06 --> M08
    M07 --> M08
    M08 --> M09
    M09 --> M10
    M10 --> M11
    M10 --> M18
    M11 --> M12
    M12 --> M20
    M20 --> M13
    M13 --> M14
    M13 --> M15
    M13 --> M16
    M13 --> M17
    M18 --> M19
    M21 -.->|orchestrates| M01
    M21 -.->|orchestrates| M03
    M21 -.->|orchestrates| M04
    M21 -.->|orchestrates| M09
    M21 -.->|orchestrates| M10
```

---

## Diagram 3: Data Flow — Article Ingestion to Published Insight

```mermaid
sequenceDiagram
    autonumber
    participant n8n as n8n Scheduler
    participant CA as Collection Agent
    participant SQ as Source Quality Engine
    participant CE as Content Extraction Engine
    participant SD as Signal Detection Agent
    participant MV as Multi-Source Validation
    participant RS as Relevance Scoring
    participant PE as TADA Perspective Engine
    participant RE as Recommendation Engine
    participant HR as Human Review System
    participant KR as Knowledge Repository
    participant AL as Alerting System

    n8n->>CA: Trigger: daily_collection_workflow (cron: */15 * * * *)
    CA->>CA: Fetch raw content from 50+ sources
    CA->>CA: Deduplicate (SHA-256 fingerprint check)
    CA->>SQ: Submit source + content for quality scoring
    SQ-->>CA: Quality score (0-100)
    
    alt Quality score >= 40
        CA->>CE: Send raw content for extraction
        CE->>CE: Run LLM pipeline (summary, keywords, entities)
        CE->>CE: Generate embedding (text-embedding-3-large → pgvector)
        CE-->>SD: Structured content item + embedding
    else Quality score < 40
        CA->>CA: Quarantine (store, flag, do not process)
    end

    SD->>SD: Pattern match against signal taxonomies
    SD->>SD: Anomaly detection vs. baseline
    
    alt Signal confidence >= 0.65
        SD->>MV: Submit signal for cross-source validation
        MV->>MV: Query pgvector: similar signals in last 48hr
        MV->>MV: Check ≥ 2 independent sources
        MV-->>SD: Validated (multi_source_confirmed = true/false)
        SD->>RS: Submit validated signal for relevance scoring
        RS->>RS: Apply 5-dimension weighted scoring
        
        alt Relevance score >= 45
            RS->>PE: Send signal + context for TADA perspective
            PE->>PE: Generate What/Why/Impact/TraditionalResponse/TADAResponse/D-D-D
            PE->>RE: Send framed insight for recommendations
            RE->>RE: Generate per-persona recommendations (5 personas)
            RE->>HR: Create DRAFT insight record in review queue
            HR->>HR: Assign reviewer based on topic domain
            HR-->>AL: Notify: "New insight in review queue" → Slack
        else Score < 45
            RS->>KR: Archive signal (low relevance — searchable but not surfaced)
        end
    else Confidence < 0.65
        SD->>KR: Store as low_confidence signal
    end

    Note over HR: Human reviewer evaluates insight
    
    alt Reviewer approves
        HR->>KR: Publish to Knowledge Repository (permanent)
        HR-->>AL: Notify stakeholders per alert config
        AL->>AL: Dispatch to Slack / Teams / Email
    else Reviewer rejects with notes
        HR->>HR: Record rejection reason
        HR->>KR: Archive (soft-delete, not removed)
    else Reviewer requests revision
        HR->>PE: Return to Perspective Engine with notes
        PE->>PE: Regenerate with reviewer feedback
        PE->>HR: Submit revised DRAFT
    end
```

---

## Diagram 4: AI Agent Architecture

```mermaid
graph LR
    subgraph TRIGGER["Triggers"]
        T1[n8n Webhook]
        T2[API Endpoint]
        T3[Scheduled Cron]
    end

    subgraph ORCHESTRATOR["LangGraph Orchestrator"]
        ORCH[Agent Router<br/>Determines which graph to execute]
    end

    subgraph COLLECTION_GRAPH["Collection Graph"]
        AG_CA[Collection Agent<br/>Fetches from 50+ sources<br/>Tools: fetch_rss, fetch_api, scrape_web]
        AG_RE[Research Agent<br/>Deep-dives on demand<br/>Tools: web_search, read_page, fetch_pdf]
    end

    subgraph SIGNAL_GRAPH["Signal Graph"]
        AG_SD[Signal Detection Agent<br/>Pattern + anomaly detection<br/>Tools: query_vectors, classify_event]
        AG_TR[Trend Agent<br/>Frequency/momentum/velocity<br/>Tools: trend_query, compute_momentum]
        AG_CI[Competitive Intel Agent<br/>Competitor monitoring<br/>Tools: competitor_search, diff_content]
        AG_PP[Pain Point Agent<br/>Community sentiment<br/>Tools: reddit_scan, twitter_scan, linkedin_scan]
    end

    subgraph INTELLIGENCE_GRAPH["Intelligence Graph"]
        AG_PE[TADA Perspective Agent<br/>What/Why/Impact/D-D-D<br/>Tools: generate_perspective, validate_ddd]
        AG_RC[Recommendation Agent<br/>Per-persona strategic recs<br/>Tools: persona_lookup, generate_rec]
        AG_CS[Content Strategy Agent<br/>Content format mapping<br/>Tools: format_content, schedule_slot]
        AG_SA[Sales Agent<br/>Sales intelligence extraction<br/>Tools: crm_lookup, generate_talking_points]
    end

    subgraph BRIEFING_GRAPH["Briefing Graph"]
        AG_EB[Executive Briefing Agent<br/>Weekly/daily briefing compilation<br/>Tools: aggregate_insights, rank_priority]
        AG_QA[QA Agent<br/>Quality and accuracy checking<br/>Tools: fact_check, consistency_check]
        AG_RO[Repository Agent<br/>Knowledge store management<br/>Tools: store_insight, update_graph, index_search]
    end

    T1 --> ORCH
    T2 --> ORCH
    T3 --> ORCH

    ORCH -->|collection trigger| AG_CA
    ORCH -->|research request| AG_RE
    ORCH -->|signal pipeline| AG_SD
    ORCH -->|briefing trigger| AG_EB

    AG_CA -->|raw content| AG_SD
    AG_RE -->|research output| AG_SD
    AG_SD -->|validated signals| AG_TR
    AG_SD -->|validated signals| AG_CI
    AG_SD -->|validated signals| AG_PP
    AG_TR -->|trend data| AG_PE
    AG_CI -->|competitive context| AG_PE
    AG_PP -->|pain point context| AG_PE
    AG_PE -->|framed insight| AG_RC
    AG_PE -->|framed insight| AG_SA
    AG_RC -->|recommendations| AG_CS
    AG_RC -->|recommendations| AG_QA
    AG_CS -->|content plan| AG_QA
    AG_QA -->|validated insight| AG_RO
    AG_EB -->|briefing draft| AG_QA
    AG_RO -->|stored| KR[(Knowledge Repository)]

    style COLLECTION_GRAPH fill:#dbeafe,stroke:#3b82f6
    style SIGNAL_GRAPH fill:#fef9c3,stroke:#eab308
    style INTELLIGENCE_GRAPH fill:#dcfce7,stroke:#22c55e
    style BRIEFING_GRAPH fill:#fce7f3,stroke:#ec4899
```

---

## Diagram 5: Database ERD

```mermaid
erDiagram
    SOURCE {
        uuid id PK
        string name
        string url
        string source_type "rss|api|social|podcast|video|web"
        string category
        boolean is_active
        timestamp last_fetched_at
        timestamp created_at
    }

    SOURCE_QUALITY_SCORE {
        uuid id PK
        uuid source_id FK
        float trust_score
        float authority_score
        float influence_score
        float accuracy_score
        float composite_score
        timestamp scored_at
    }

    RAW_CONTENT {
        uuid id PK
        uuid source_id FK
        string sha256_fingerprint
        text raw_text
        string url
        string title
        timestamp published_at
        timestamp ingested_at
        string status "new|processing|processed|quarantined"
    }

    CONTENT_ITEM {
        uuid id PK
        uuid raw_content_id FK
        text summary_short
        text summary_long
        string[] keywords
        json entities
        vector embedding_3072
        float quality_gate_score
        timestamp extracted_at
    }

    SIGNAL {
        uuid id PK
        uuid content_item_id FK
        string signal_type "event|trend|disruption|risk|opportunity"
        string event_category
        float detection_confidence
        boolean multi_source_confirmed
        integer source_count
        string status "detected|validated|low_confidence|archived"
        timestamp detected_at
    }

    TREND {
        uuid id PK
        string topic
        string slug
        float frequency_per_day
        float momentum_score
        float velocity_score
        string trend_direction "rising|falling|stable|emerging"
        timestamp first_seen_at
        timestamp last_seen_at
    }

    TREND_DATA_POINT {
        uuid id PK
        uuid trend_id FK
        date data_date
        integer mention_count
        float sentiment_score
        json source_breakdown
    }

    INSIGHT {
        uuid id PK
        uuid signal_id FK
        string title
        text what_is_happening
        text why_it_matters
        text business_impact
        text traditional_response
        text tada_response
        text detect_decide_do
        float relevance_score
        json relevance_breakdown
        string status "draft|under_review|approved|rejected|published"
        uuid assigned_reviewer_id
        timestamp created_at
        timestamp reviewed_at
        timestamp published_at
    }

    RECOMMENDATION {
        uuid id PK
        uuid insight_id FK
        string persona "marketing|sales|leadership|cs|product"
        text recommendation_text
        string priority "high|medium|low"
        string action_type
        json metadata
    }

    REVIEW_RECORD {
        uuid id PK
        uuid insight_id FK
        uuid reviewer_id
        string action "submitted|approved|rejected|revision_requested"
        text reviewer_notes
        timestamp actioned_at
    }

    KNOWLEDGE_ITEM {
        uuid id PK
        uuid insight_id FK
        string title
        text content
        string[] tags
        string[] categories
        vector embedding_3072
        boolean is_archived
        timestamp published_at
        timestamp archived_at
    }

    ENTITY {
        uuid id PK
        string name
        string entity_type "company|person|product|technology|regulation|location"
        json metadata
        timestamp first_seen_at
    }

    ENTITY_RELATIONSHIP {
        uuid id PK
        uuid source_entity_id FK
        uuid target_entity_id FK
        string relationship_type
        float strength_score
        timestamp observed_at
    }

    CALENDAR_ENTRY {
        uuid id PK
        uuid insight_id FK
        string content_type "linkedin|article|newsletter|briefing"
        string title
        date scheduled_date
        string persona_target
        string status "planned|in_progress|ready|published"
    }

    ALERT {
        uuid id PK
        uuid insight_id FK
        string alert_type "breaking|weekly_digest|trending"
        string[] channels
        json payload
        string status "pending|dispatched|failed"
        timestamp dispatched_at
    }

    COMPETITOR {
        uuid id PK
        string name
        string website
        string[] monitored_topics
        boolean is_active
    }

    COMPETITOR_ACTIVITY {
        uuid id PK
        uuid competitor_id FK
        uuid content_item_id FK
        string activity_type
        text summary
        timestamp observed_at
    }

    SOURCE ||--o{ SOURCE_QUALITY_SCORE : "scored by"
    SOURCE ||--o{ RAW_CONTENT : "produces"
    RAW_CONTENT ||--|| CONTENT_ITEM : "extracted to"
    CONTENT_ITEM ||--o{ SIGNAL : "generates"
    SIGNAL ||--o{ TREND : "contributes to"
    TREND ||--o{ TREND_DATA_POINT : "tracked by"
    SIGNAL ||--|| INSIGHT : "becomes"
    INSIGHT ||--o{ RECOMMENDATION : "generates"
    INSIGHT ||--o{ REVIEW_RECORD : "reviewed by"
    INSIGHT ||--|| KNOWLEDGE_ITEM : "published as"
    KNOWLEDGE_ITEM ||--o{ ENTITY : "mentions"
    ENTITY ||--o{ ENTITY_RELATIONSHIP : "relates to"
    INSIGHT ||--o{ CALENDAR_ENTRY : "scheduled in"
    INSIGHT ||--o{ ALERT : "triggers"
    COMPETITOR ||--o{ COMPETITOR_ACTIVITY : "tracked by"
    CONTENT_ITEM ||--o{ COMPETITOR_ACTIVITY : "sourced from"
```

---

## Diagram 6: API Architecture

```mermaid
graph TB
    subgraph CLIENT["Clients"]
        WEB[Next.js Web App]
        N8N_WH[n8n Webhooks]
        MOBILE[Future: Mobile]
    end

    subgraph GATEWAY["API Layer (FastAPI)"]
        subgraph MIDDLEWARE["Middleware Stack"]
            AUTH[Clerk JWT Auth]
            RATE[Rate Limiting<br/>100 req/min]
            LOG[Structured Logging]
            OTEL[OpenTelemetry Traces]
        end

        subgraph ROUTES["API Routes — /api/v1/"]
            R_INSIGHTS["POST /insights<br/>GET /insights<br/>GET /insights/{id}<br/>PATCH /insights/{id}"]
            R_SIGNALS["GET /signals<br/>GET /signals/{id}<br/>POST /signals/detect"]
            R_SOURCES["GET /sources<br/>POST /sources<br/>PUT /sources/{id}<br/>DELETE /sources/{id}"]
            R_SEARCH["POST /search<br/>body: {query, mode, filters}<br/>mode: keyword|semantic|hybrid|vector"]
            R_TRENDS["GET /trends<br/>GET /trends/{id}<br/>GET /trends/{id}/timeline"]
            R_KNOWLEDGE["GET /knowledge<br/>GET /knowledge/{id}<br/>GET /knowledge/graph"]
            R_REVIEW["GET /review/queue<br/>PATCH /review/{id}/status<br/>POST /review/{id}/comment"]
            R_EXECUTIVE["GET /executive/briefings<br/>GET /executive/risks<br/>GET /executive/opportunities<br/>GET /executive/trends"]
            R_CALENDAR["GET /calendar<br/>POST /calendar/entries<br/>PATCH /calendar/entries/{id}"]
            R_ALERTS["GET /alerts<br/>POST /alerts/config<br/>GET /alerts/history"]
            R_GRAPH["GET /graph/nodes<br/>GET /graph/edges<br/>GET /graph/neighbors/{id}"]
            R_AGENTS["POST /agents/run<br/>GET /agents/status/{run_id}"]
            R_WEBHOOKS["POST /webhooks/n8n<br/>(internal, key auth)"]
            R_WS["WS /ws/alerts<br/>(WebSocket live feed)"]
        end
    end

    subgraph SERVICES["Service Layer"]
        SVC_DB[(PostgreSQL +<br/>pgvector)]
        SVC_CACHE[(Redis Cache)]
        SVC_STORAGE[(Supabase Storage)]
        SVC_LG[LangGraph<br/>Agent Executor]
        SVC_LF[Langfuse<br/>Observability]
    end

    WEB --> AUTH
    N8N_WH --> R_WEBHOOKS
    AUTH --> RATE
    RATE --> LOG
    LOG --> OTEL
    OTEL --> ROUTES
    ROUTES --> SVC_DB
    ROUTES --> SVC_CACHE
    ROUTES --> SVC_STORAGE
    R_AGENTS --> SVC_LG
    SVC_LG --> SVC_LF
    R_WS --> SVC_CACHE
```

---

## Diagram 7: n8n Workflow Overview

```mermaid
graph TB
    subgraph TRIGGERS["Triggers"]
        CRON1[Cron: */15 min]
        CRON2[Cron: */60 min]
        CRON3[Cron: 0 6 * * * daily 6am]
        CRON4[Cron: 0 7 * * 1 Mon 7am]
        WEBHOOK1[Webhook: signal_detected]
        WEBHOOK2[Webhook: insight_approved]
        WEBHOOK3[Webhook: high_priority_signal]
    end

    subgraph WORKFLOWS["n8n Workflows"]
        WF01[01 Daily Collection<br/>RSS · API · Social · Web]
        WF02[02 Signal Detection<br/>Pattern · Anomaly · Taxonomy]
        WF03[03 Trend Analysis<br/>Frequency · Momentum · Velocity]
        WF04[04 Competitive Intelligence<br/>Competitor monitoring · Diff]
        WF05[05 Pain Point Detection<br/>Reddit · LinkedIn · X scan]
        WF06[06 Executive Briefing<br/>Daily/weekly briefing gen]
        WF07[07 Content Calendar<br/>Weekly/monthly scheduling]
        WF08[08 Alert Trigger<br/>Slack · Teams · Email dispatch]
        WF09[09 Human Review Notification<br/>Reviewer assignment + notify]
        WF10[10 Repository Sync<br/>Knowledge graph + search index]
    end

    subgraph API_CALLS["FastAPI Endpoints Called"]
        API1[POST /agents/run?agent=collection]
        API2[POST /agents/run?agent=signal]
        API3[POST /agents/run?agent=trend]
        API4[POST /agents/run?agent=competitive]
        API5[POST /agents/run?agent=pain_point]
        API6[POST /agents/run?agent=executive_briefing]
        API7[POST /calendar/entries]
        API8[POST /alerts/dispatch]
        API9[POST /review/notify]
        API10[POST /knowledge/sync]
    end

    CRON1 --> WF01 --> API1
    WF01 -->|on new signals| WEBHOOK1
    WEBHOOK1 --> WF02 --> API2
    CRON2 --> WF03 --> API3
    CRON2 --> WF04 --> API4
    CRON2 --> WF05 --> API5
    CRON3 --> WF06 --> API6
    CRON4 --> WF07 --> API7
    WEBHOOK3 --> WF08 --> API8
    WF02 -->|new insight draft| WF09 --> API9
    WEBHOOK2 --> WF10 --> API10
    WF10 -->|sync complete| WF08

    style WF01 fill:#dbeafe
    style WF02 fill:#fef9c3
    style WF06 fill:#fce7f3
    style WF08 fill:#fee2e2
```

---

## Diagram 8: Deployment Architecture

```mermaid
graph TB
    subgraph INTERNET["Internet / Users"]
        USER_WEB[Web Browser]
        USER_SLACK[Slack / Teams]
        USER_EMAIL[Email Client]
    end

    subgraph VERCEL["Vercel (Frontend CDN + Edge)"]
        VCL_EDGE[Vercel Edge Network<br/>Global CDN]
        VCL_NEXT[Next.js App<br/>SSR + RSC + API Routes]
        VCL_STATIC[Static Assets<br/>CDN-cached]
    end

    subgraph RAILWAY["Railway (Backend Infrastructure)"]
        subgraph RAIL_API["API Service"]
            RW_API[FastAPI App<br/>4 workers · 2GB RAM]
            RW_CELERY[Celery Workers<br/>2 workers · async tasks]
        end

        subgraph RAIL_AGENTS["Agents Service"]
            RW_AGENTS[LangGraph Agent Runner<br/>2 workers · 4GB RAM]
        end

        subgraph RAIL_N8N["Workflow Service"]
            RW_N8N[n8n (self-hosted)<br/>queue mode]
            RW_N8N_WORKER[n8n Worker<br/>2 workers]
        end

        subgraph RAIL_DATA["Data Services"]
            RW_PG[(PostgreSQL 15<br/>+ pgvector extension<br/>+ PgBouncer pool)]
            RW_REDIS[(Redis 7<br/>cache + pub/sub<br/>+ Celery broker)]
        end
    end

    subgraph SUPABASE["Supabase (Storage)"]
        SB_STORAGE[Object Storage<br/>PDFs · Audio · Images]
        SB_AUTH_HOOK[Auth Webhook Receiver]
    end

    subgraph CLERK["Clerk (Auth SaaS)"]
        CL_AUTH[JWT Issuance<br/>User Management<br/>RBAC Roles]
    end

    subgraph OBSERVABILITY["Observability"]
        LF[Langfuse Cloud<br/>AI Traces + Eval]
        PROM[Prometheus<br/>Metrics Scrape]
        GRAF[Grafana Cloud<br/>Dashboards + Alerts]
    end

    subgraph EXTERNAL_APIS["External APIs & Sources"]
        EXT[OpenAI API<br/>Twitter API<br/>Reddit API<br/>Proxycurl<br/>News APIs<br/>YouTube API]
    end

    USER_WEB -->|HTTPS| VCL_EDGE
    VCL_EDGE --> VCL_NEXT
    VCL_NEXT -->|API calls| RW_API
    RW_API -->|async tasks| RW_CELERY
    RW_API -->|agent triggers| RW_AGENTS
    RW_N8N -->|webhooks| RW_API
    RW_N8N --> RW_N8N_WORKER
    RW_API --> RW_PG
    RW_API --> RW_REDIS
    RW_CELERY --> RW_PG
    RW_CELERY --> RW_REDIS
    RW_AGENTS --> RW_PG
    RW_AGENTS --> EXT
    RW_API --> SB_STORAGE
    CL_AUTH -->|JWT| RW_API
    CL_AUTH -->|JWT verify| VCL_NEXT
    RW_AGENTS -->|traces| LF
    RW_API -->|metrics| PROM
    PROM --> GRAF
    RW_API -->|alerts| USER_SLACK
    RW_N8N -->|alerts| USER_SLACK
    RW_N8N -->|alerts| USER_EMAIL

    style VERCEL fill:#000,color:#fff
    style RAILWAY fill:#7c3aed,color:#fff
    style SUPABASE fill:#1a1a2e,color:#fff
    style CLERK fill:#6c47ff,color:#fff
    style OBSERVABILITY fill:#f0fdf4,stroke:#22c55e
```
