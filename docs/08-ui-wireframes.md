# TADA Intelligence Platform — UI Wireframes
## Deliverable 8 of 20

All wireframes use a consistent dark-themed shell with a left sidebar (240px collapsed to 60px) and a top header bar (56px). Main content area is fluid. Color palette: `#0A0F1E` (bg), `#111827` (card), `#1F2937` (border), `#3B82F6` (primary accent), `#10B981` (positive/green), `#EF4444` (risk/red), `#F59E0B` (warning/amber), `#8B5CF6` (trend/purple).

---

## Page 1 — Executive Portal (Home) `/`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR (240px)          │  TOP HEADER                                    │
│                          │  [🔔 3] [Search...........] [Raunak ▾]        │
│  🏠 Executive Portal ←   ├────────────────────────────────────────────────│
│  📡 Intelligence         │                                                 │
│  ⚡ Signals              │  INTELLIGENCE BRIEFING — Jun 16, 2026          │
│  📈 Trends               │  ┌─────────────┐ ┌─────────────┐ ┌──────────┐│
│  🎯 Competitors          │  │ 🔴 RISKS    │ │ 🟢 OPPS     │ │⚡ SIGNALS││
│  🔍 Search               │  │      7      │ │      12     │ │    43    ││
│  💡 Content              │  │ +2 new      │ │ +5 new      │ │ today    ││
│  📋 Review Queue         │  └─────────────┘ └─────────────┘ └──────────┘│
│  📦 Repository           │  ┌─────────────────────┐ ┌───────────────────┐│
│  🕸 Knowledge Graph       │  │ TOP SIGNALS          │ │ COMPETITOR PULSE  ││
│  📊 Analytics            │  │ ┌──────────────────┐ │ │ Competitor A      ││
│  ⚙️ Settings             │  │ │🔴 Tariff escalation│ │ │ → New product    ││
│                          │  │ │ SC Dive + Bloomberg│ │ │   announced      ││
│  ─────────────────       │  │ │ Confidence: 94%   │ │ │                  ││
│  ✅ 12 pending review    │  │ │ [View Signal →]   │ │ │ Competitor B      ││
│  🔴 2 critical alerts    │  │ └──────────────────┘ │ │ → Series C raised ││
│                          │  │ ┌──────────────────┐ │ │   $50M            ││
│                          │  │ │🟡 Nearshoring surge│ │ └───────────────────┘
│                          │  │ │ McKinsey + Gartner │ │ ┌───────────────────┐│
│                          │  │ │ Confidence: 87%   │ │ │ MARKET SENTIMENT  ││
│                          │  │ │ [View Signal →]   │ │ │ ●●●●○  Cautious   ││
│                          │  │ └──────────────────┘ │ │ Supply Chain: ↓   ││
│                          │  └─────────────────────┘ │ Procurement: ↑    ││
│                          │  ┌──────────────────────────────────────────┐ ││
│                          │  │ RECOMMENDED ACTIONS                       │ ││
│                          │  │ [Marketing] Publish tariff impact post    │ ││
│                          │  │ [Sales] Alert accounts in affected sectors │ ││
│                          │  │ [Leadership] Review tariff exposure report │ ││
│                          │  └──────────────────────────────────────────┘ ││
└──────────────────────────────────────────────────────────────────────────┘
```

**Components:** StatCard (×3), SignalCard (×N), CompetitorFeed, SentimentGauge, ActionsList
**Data:** `/api/v1/executive/dashboard`, `/api/v1/signals?limit=5&sort=relevance`, `/api/v1/competitors/events?limit=5`
**Interactions:** Click signal → signal detail drawer; Click action → contextual panel; Bell → alert center

---

## Page 2 — Market Intelligence Explorer `/intelligence`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Intelligence Explorer                        [+ Add Source]   │
│         ├──────────────────────────────────────────────────────────────  │
│         │ FILTERS (collapsible left panel 280px)  │  RESULTS GRID        │
│         │ ┌────────────────────────────┐           │                      │
│         │ │ Source Type  [▾]           │  Sort: [Relevance ▾]  View:[⊞⊟]│
│         │ │ ☑ Industry News            │  ─────────────────────────────  │
│         │ │ ☑ Analyst Report           │  ┌───────────┐ ┌───────────┐   │
│         │ │ ☑ Social Post              │  │ ARTICLE   │ │ ARTICLE   │   │
│         │ │ ☐ Podcast                  │  │ Supply     │ │ Gartner:  │   │
│         │ │                            │  │ Chain Dive │ │ SC Risk   │   │
│         │ │ Topic  [▾]                 │  │            │ │           │   │
│         │ │ ☑ Supply Chain             │  │ Jun 16     │ │ Jun 15    │   │
│         │ │ ☐ Procurement              │  │ Score: 94  │ │ Score: 91 │   │
│         │ │ ☑ Manufacturing            │  │ [Signal ⚡]│ │ [Signal ⚡]│  │
│         │ │                            │  └───────────┘ └───────────┘   │
│         │ │ Date Range                 │  ┌───────────┐ ┌───────────┐   │
│         │ │ [Last 7 days    ▾]         │  │ REPORT    │ │ ARTICLE   │   │
│         │ │                            │  │ McKinsey  │ │ Mfg Dive  │   │
│         │ │ Relevance Score            │  │           │ │           │   │
│         │ │ Min: ──●────── 70          │  │ Jun 14    │ │ Jun 14    │   │
│         │ │                            │  │ Score: 88 │ │ Score: 85 │   │
│         │ │ Source                     │  │ [Signal ⚡]│ │           │   │
│         │ │ [Search sources...]        │  └───────────┘ └───────────┘   │
│         │ │                            │                                  │
│         │ │ [Clear Filters] [Apply]    │  Showing 1-12 of 1,847  [< >]  │
│         │ └────────────────────────────┘                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Components:** FilterPanel, ContentCard (grid/list toggle), Pagination, SortDropdown
**Data:** `/api/v1/content` with filter params
**Interactions:** Click card → opens article detail drawer with full content, summary, related signals

---

## Page 3 — Signals Dashboard `/signals`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Signal Intelligence                     [⚡ 43 signals today]  │
│         ├──────────────────────────────────────────────────────────────  │
│         │ [All] [🔴 Critical] [🟡 High] [🟢 Medium]  [Type ▾] [Date ▾] │
│         │                                                                  │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ 🔴 CRITICAL — Tariff Escalation: US-China 2026 Round 2   │   │
│         │ │ Detected Jun 16, 2026 · 4 sources · Confidence: 94%      │   │
│         │ │                                                            │   │
│         │ │ Supply Chain ████████████ 96%  Executive ████████████ 92%│   │
│         │ │ Business     ██████████░░ 88%  Technology ████░░░░░░░ 42%│   │
│         │ │ TADA Align   ████████████ 95%                             │   │
│         │ │                                                            │   │
│         │ │ Sources: Bloomberg · Supply Chain Dive · WSJ · Gartner   │   │
│         │ │                                    [View Full Analysis →] │   │
│         │ └──────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ 🟡 HIGH — Nearshoring Acceleration in Semiconductor Mfg  │   │
│         │ │ Detected Jun 15, 2026 · 6 sources · Confidence: 87%      │   │
│         │ │ Supply Chain ██████████░░ 84%  Executive ████████░░░░ 78%│   │
│         │ │ Sources: McKinsey · IDC · Manufacturing Dive · 3 more    │   │
│         │ │                                    [View Full Analysis →] │   │
│         │ └──────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ 🟢 MEDIUM — AI-Powered Demand Sensing Adoption Spike     │   │
│         │ │ Detected Jun 14, 2026 · 3 sources · Confidence: 79%      │   │
│         │ └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Components:** SignalCard (full), ScoreBar (5 dimensions), SourceChips, UrgencyBadge
**Data:** `/api/v1/signals` with urgency/type filters
**Interactions:** Click card → `/signals/[id]` detail page; Score bars are interactive tooltips

---

## Page 4 — Signal Detail `/signals/[id]`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  ← Back to Signals                                              │
│         ├──────────────────────────────────────────────────────────────  │
│         │ 🔴 Tariff Escalation: US-China 2026 Round 2                    │
│         │ Detected Jun 16, 2026  ·  Confidence 94%  ·  4 sources         │
│         │                                                                  │
│         │ ┌─── TADA PERSPECTIVE ─────────────────────────────────────┐   │
│         │ │ WHAT HAPPENED                                             │   │
│         │ │ The US announced a new 25% tariff on 340 Chinese-made    │   │
│         │ │ industrial components effective August 1, 2026...         │   │
│         │ │                                                            │   │
│         │ │ WHY IT MATTERS                                            │   │
│         │ │ Affects $47B in annual US manufacturing imports. 68% of  │   │
│         │ │ surveyed manufacturers have <30 day buffer stock...       │   │
│         │ │                                                            │   │
│         │ │ POTENTIAL IMPACT                                          │   │
│         │ │ ⚠ Cost increase 12-18% for affected component categories │   │
│         │ │ ⚠ Lead time extensions of 6-10 weeks likely              │   │
│         │ │ ⚠ Spot market pricing volatility expected                │   │
│         │ │                                                            │   │
│         │ │ ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│         │ │ │ 🔍 DETECT   │  │ 🧠 DECIDE   │  │ ⚡ DO          │  │   │
│         │ │ │ Real-time   │  │ Scenario     │  │ Automated      │  │   │
│         │ │ │ supplier     │  │ modeling of  │  │ supplier       │  │   │
│         │ │ │ exposure     │  │ 3 sourcing   │  │ outreach &     │  │   │
│         │ │ │ monitoring   │  │ alternatives │  │ RFQ generation │  │   │
│         │ │ └──────────────┘  └──────────────┘  └────────────────┘  │   │
│         │ │                                                            │   │
│         │ │ TRADITIONAL RESPONSE vs TADA RESPONSE                    │   │
│         │ │ Traditional: Wait for procurement review cycle (weeks)   │   │
│         │ │ TADA: Detect exposure today → Model scenarios → Execute  │   │
│         │ └───────────────────────────────────────────────────────────┘  │
│         │                                                                  │
│         │ RECOMMENDATIONS BY TEAM                                         │
│         │ [Marketing] [Sales] [Leadership] [Customer Success] [Product]   │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ SALES: Alert 23 accounts with high tariff exposure.      │   │
│         │ │ Use TADA's scenario modeling to show cost impact...       │   │
│         │ └──────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         │ SOURCE ARTICLES (4)          CONTENT IDEAS (7)                  │
│         │ [Bloomberg] [SC Dive] ...    [LinkedIn] [Article] [Newsletter]  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 5 — Trends Dashboard `/trends`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Trend Intelligence                                              │
│         ├──────────────────────────────────────────────────────────────  │
│         │ [All] [🔥 Emerging] [📈 Growing] [━ Stable] [📉 Declining]     │
│         │ Category: [Supply Chain ▾]                                      │
│         │                                                                  │
│         │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ │
│         │ │ 🔥 EMERGING     │ │ 📈 GROWING       │ │ 📈 GROWING      │ │
│         │ │ AI-Powered       │ │ Nearshoring      │ │ Tariff           │ │
│         │ │ Demand Sensing   │ │ Acceleration     │ │ Reshaping        │ │
│         │ │                  │ │                  │ │                  │ │
│         │ │ ╱╱╱╱╱╱╱╱       │ │ ╱╱╱╱╱╱╱         │ │ /\/\/\/\         │ │
│         │ │ Momentum: 94    │ │ Momentum: 87     │ │ Momentum: 82     │ │
│         │ │ Signals: 23     │ │ Signals: 41      │ │ Signals: 37      │ │
│         │ │ First: Mar 2026 │ │ First: Jan 2026  │ │ First: Apr 2026  │ │
│         │ │ [View →]        │ │ [View →]         │ │ [View →]         │ │
│         │ └──────────────────┘ └──────────────────┘ └──────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 6 — Advanced Search `/search`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Intelligence Search                                            │
│         ├──────────────────────────────────────────────────────────────  │
│         │ ┌────────────────────────────────────────────────────────────┐ │
│         │ │ 🔍  tariff impact supply chain                        [×] │ │
│         │ └────────────────────────────────────────────────────────────┘ │
│         │ Search mode: [● Hybrid] [○ Semantic] [○ Keyword]               │
│         │                                                                  │
│         │ FILTERS ────────────────────────────────────────────────────   │
│         │ Type: [Articles] [Signals] [Trends] [Content Ideas] [All ✓]    │
│         │ Date: [Last 30 days ▾]   Score: [70+ ▾]   Source: [Any ▾]     │
│         │                                                                  │
│         │ 247 results for "tariff impact supply chain"                    │
│         │                                                                  │
│         │ ⚡ SIGNAL  ──────────────────────────────── Relevance: 97%    │
│         │ Tariff Escalation: US-China 2026 Round 2                       │
│         │ 4 sources · Confidence 94% · Detected Jun 16                   │
│         │ "...manufacturers facing 12-18% cost increase across..."        │
│         │ [View Signal]                                                    │
│         │                                                                  │
│         │ 📄 ARTICLE  ─────────────────────────────── Relevance: 94%   │
│         │ How Tariffs Are Reshaping Global Supply Networks               │
│         │ Bloomberg · Jun 15, 2026 · Score: 91                           │
│         │ "...supply chain leaders are accelerating nearshoring..."       │
│         │ [Read Article]                                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 7 — Human Review Queue `/review`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Review Queue                              [12 awaiting review] │
│         ├──────────────────────────────────────────────────────────────  │
│         │ [Insights (5)] [Recommendations (3)] [Content Ideas (4)] [All] │
│         │ Priority: [High first ▾]   Assigned: [Me] [All]               │
│         │                                                                  │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ 🔴 HIGH PRIORITY                        INSIGHT #INS-041 │   │
│         │ │ Tariff Escalation Strategic Insight                       │   │
│         │ │ Generated Jun 16 · by TADA Perspective Agent              │   │
│         │ │                                                            │   │
│         │ │ Preview: "Organizations with >30% China-sourced..."        │   │
│         │ │                                                            │   │
│         │ │           [View Full] [✓ Approve] [✗ Reject] [↩ Revise] │   │
│         │ └──────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ 🟡 MEDIUM                               CONTENT #CON-089 │   │
│         │ │ LinkedIn Post: "Why Tariffs Demand Decision Intelligence" │   │
│         │ │ Generated Jun 16 · by Content Strategy Agent              │   │
│         │ │           [View Full] [✓ Approve] [✗ Reject] [↩ Revise] │   │
│         │ └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 8 — Knowledge Repository `/repository`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  TADA Intelligence Repository                   [Export CSV ↓] │
│         ├──────────────────────────────────────────────────────────────  │
│         │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│         │ │ 48,291   │ │  1,847   │ │   423    │ │  2,104   │          │
│         │ │ Articles │ │ Signals  │ │  Trends  │ │  Insights│          │
│         │ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│         │                                                                  │
│         │ [Search repository...]              [Articles ▾] [All time ▾]  │
│         │                                                                  │
│         │ ── Jun 16, 2026 ─────────────────────────────────────────      │
│         │ 📄 How AI Is Transforming Procurement Cycles · McKinsey        │
│         │    Score: 88 · Supply Chain, AI · Jun 16 · [⚡ View Signal]    │
│         │ 📄 Semiconductor Reshoring: State of Play Q2 2026 · IDC        │
│         │    Score: 91 · Manufacturing, Semiconductors · Jun 16           │
│         │ ⚡ SIGNAL: AI Demand Sensing Adoption Spike · 3 sources         │
│         │    Confidence 79% · Technology, Supply Chain · Jun 16           │
│         │                                                                  │
│         │ ── Jun 15, 2026 ─────────────────────────────────────────      │
│         │ [infinite scroll continues...]                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 9 — Knowledge Graph `/graph`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Knowledge Graph                [Filter ▾] [Layout ▾] [Export] │
│         ├──────────────────────────────────────────────────────────────  │
│         │ Entity Types: [● Company] [● Technology] [● Trend] [● Risk]   │
│         │                                                                  │
│         │  ┌─────────────────────────────────────────────────────────┐  │
│         │  │                    [REACT FLOW CANVAS]                  │  │
│         │  │                                                          │  │
│         │  │   [Tariffs]───────────[Supply Chain Disruption]         │  │
│         │  │      │                        │                         │  │
│         │  │      │               [Nearshoring]────[Manufacturing]   │  │
│         │  │      │                        │                         │  │
│         │  │   [Trade Policy]         [AI Adoption]                  │  │
│         │  │                               │                         │  │
│         │  │                    [Decision Intelligence]               │  │
│         │  │                                                          │  │
│         │  │  Legend: 🔵 Company  🟢 Technology  🟣 Trend  🔴 Risk  │  │
│         │  └─────────────────────────────────────────────────────────┘  │
│         │                                                                  │
│         │  SELECTED: Supply Chain Disruption                              │
│         │  Type: Risk · 23 related signals · 8 companies mentioned       │
│         │  [View All Signals] [View Articles]                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 10 — Content Strategy Hub `/content`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Content Strategy                            [Calendar View 📅] │
│         ├──────────────────────────────────────────────────────────────  │
│         │ [LinkedIn (18)] [Articles (9)] [Newsletter (6)] [Briefings (4)]│
│         │ Status: [Draft] [In Review] [Approved ✓] [All]                 │
│         │                                                                  │
│         │ ─── WEEK OF JUN 16, 2026 ──────────────────────────────────   │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ 📝 LinkedIn Post (DRAFT)                     Signal #041 │   │
│         │ │ "The tariff clock is ticking. Here's what supply chain   │   │
│         │ │  leaders need to do in the next 30 days..."              │   │
│         │ │ Target: SC Leaders · Est. reach: 8K–15K                  │   │
│         │ │ Tied to: Tariff Escalation Signal                        │   │
│         │ │              [Edit] [Send to Review →]                   │   │
│         │ └──────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ 📰 Thought Leadership Article (IN REVIEW)    Signal #038 │   │
│         │ │ "From Visibility to Action: Why Dashboards Fail in       │   │
│         │ │  Supply Chain Crisis Moments"                             │   │
│         │ │ 1,200 words · Target: CXOs · Newsletter + LinkedIn       │   │
│         │ │              [Preview] [Review Status: ⏳]               │   │
│         │ └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 11 — Analytics & ROI Dashboard `/analytics`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  ROI & Analytics Dashboard              [Last 30 days ▾]       │
│         ├──────────────────────────────────────────────────────────────  │
│         │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│         │ │  14,892  │ │    423   │ │    87    │ │   ≈ 2,400 hrs    │  │
│         │ │ Articles │ │ Signals  │ │  Trends  │ │ Research Saved   │  │
│         │ │ +18% MoM │ │ +31% MoM │ │ Tracked  │ │ @ 0.5 hr/article │  │
│         │ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│         │                                                                  │
│         │ ┌─────────────────────────────────────────────────────────┐   │
│         │ │ SIGNAL DETECTION VOLUME — Last 30 Days                  │   │
│         │ │                                                          │   │
│         │ │ 30 │                              ╱╲                    │   │
│         │ │ 20 │               ╱╲     ╱╲____╱  ╲___               │   │
│         │ │ 10 │__________╱╲__╱  ╲__╱                             │   │
│         │ │  0 └────────────────────────────────────────────────    │   │
│         │ │     May 17                                    Jun 16    │   │
│         │ └─────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         │ ┌──────────────────────┐  ┌──────────────────────────────┐    │
│         │ │ TOP TOPICS (30d)     │  │ SOURCE PERFORMANCE            │    │
│         │ │ 1. Tariffs      (89) │  │ Supply Chain Dive  ████ 94   │    │
│         │ │ 2. Nearshoring  (67) │  │ Gartner            ████ 91   │    │
│         │ │ 3. AI Adoption  (54) │  │ Bloomberg          ████ 90   │    │
│         │ │ 4. Semiconductors(41)│  │ McKinsey           ███░ 87   │    │
│         │ └──────────────────────┘  └──────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 12 — Competitive Intelligence `/competitors`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Competitive Intelligence                   [+ Add Competitor]  │
│         ├──────────────────────────────────────────────────────────────  │
│         │ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐      │
│         │ │ Competitor A   │ │ Competitor B   │ │ Competitor C   │      │
│         │ │ Tier 1         │ │ Tier 1         │ │ Tier 2         │      │
│         │ │                │ │                │ │                │      │
│         │ │ 🔴 3 new events│ │ 🟡 1 new event │ │ ○ No change   │      │
│         │ │ Last: Jun 16   │ │ Last: Jun 14   │ │ Last: Jun 10   │      │
│         │ │ [View →]       │ │ [View →]       │ │ [View →]       │      │
│         │ └────────────────┘ └────────────────┘ └────────────────┘      │
│         │                                                                  │
│         │ RECENT EVENTS TIMELINE ──────────────────────────────────────  │
│         │                                                                  │
│         │ Jun 16 · [Competitor A] 🚀 Product Launch                      │
│         │          Announced AI-powered demand planning module            │
│         │          [View] [Generate Response]                              │
│         │                                                                  │
│         │ Jun 14 · [Competitor B] 💰 Funding                             │
│         │          Raised $50M Series C — AI supply chain focus           │
│         │          [View] [Generate Response]                              │
│         │                                                                  │
│         │ POSITIONING GAP ANALYSIS                  [Generate Report →]   │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ TADA ADVANTAGE: Decision execution vs. visibility-only    │   │
│         │ │ GAP: Competitors pushing "AI-powered" without D-D-D lens  │   │
│         │ └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Page 13 — Executive Briefing Portal `/executive`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR │  Executive Briefings                        [📥 Export PDF]     │
│         ├──────────────────────────────────────────────────────────────  │
│         │ [Daily] [Weekly] [Monthly] [Quarterly]                          │
│         │                                                                  │
│         │ ┌──────────────────────────────────────────────────────────┐   │
│         │ │ DAILY INTELLIGENCE BRIEF                   Jun 16, 2026  │   │
│         │ │ Status: ✅ APPROVED by J. Smith  ·  Reviewed 7:42 AM     │   │
│         │ │                                                            │   │
│         │ │ TOP 3 SIGNALS                                             │   │
│         │ │ 🔴 Tariff Escalation — HIGH URGENCY                      │   │
│         │ │ 🟡 Nearshoring Acceleration — GROWING TREND               │   │
│         │ │ 🟢 AI Demand Sensing Adoption — OPPORTUNITY               │   │
│         │ │                                                            │   │
│         │ │ MARKET SENTIMENT: Cautious/Volatile                       │   │
│         │ │ COMPETITOR ACTIVITY: 2 events (Competitor A product launch)│  │
│         │ │                                                            │   │
│         │ │ RECOMMENDED ACTIONS                                       │   │
│         │ │ 1. Marketing: Publish tariff response content today       │   │
│         │ │ 2. Sales: Flag 23 high-exposure accounts for outreach     │   │
│         │ │ 3. Product: Accelerate tariff scenario modeling feature   │   │
│         │ │                               [Read Full Brief →]         │   │
│         │ └──────────────────────────────────────────────────────────┘   │
│         │                                                                  │
│         │ PREVIOUS BRIEFINGS                                               │
│         │ Jun 15 ✅ · Jun 14 ✅ · Jun 13 ✅ · [View All →]              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Responsive Behavior

| Viewport | Sidebar | Content | Cards |
|----------|---------|---------|-------|
| Desktop (1440px+) | 240px expanded | Full grid | 3 columns |
| Tablet (768-1439px) | 60px icon-only | Adaptive | 2 columns |
| Mobile (<768px) | Hidden (hamburger) | Full width | 1 column |

## Design System Summary

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0A0F1E` | Page background |
| `--bg-card` | `#111827` | Card surfaces |
| `--border` | `#1F2937` | All borders |
| `--accent-blue` | `#3B82F6` | Primary actions, links |
| `--signal-critical` | `#EF4444` | Critical signals, risks |
| `--signal-high` | `#F59E0B` | High priority |
| `--signal-medium` | `#10B981` | Medium/positive |
| `--trend-purple` | `#8B5CF6` | Trends, momentum |
| `--text-primary` | `#F9FAFB` | Primary text |
| `--text-muted` | `#6B7280` | Secondary text |
