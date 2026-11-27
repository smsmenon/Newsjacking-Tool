# API Architecture

## API Style

Recommended production API:

- REST for operational workflows
- GraphQL or typed dashboard queries if dashboard complexity grows
- Webhooks for n8n and downstream publishing tools

## Core Resources

### Sources

`GET /sources`

Returns configured sources and health status.

`POST /sources`

Creates a trusted source.

`PATCH /sources/{source_id}`

Updates polling, category, access method, or active status.

### Articles

`GET /articles`

Filters:

- source
- category
- publication_date
- topic
- keyword
- processed status

`GET /articles/{article_id}`

Returns raw and processed article details.

`POST /ingestion/run`

Starts a manual ingestion sweep.

### Signals

`GET /signals`

Filters:

- final_score_min
- signal_type
- surfaced
- date range
- source

`GET /signals/{signal_id}`

Returns signal, evidence, scoring breakdown, TADA perspective, and linked content opportunities.

`POST /signals/{signal_id}/reprocess`

Re-runs perspective and content generation with current prompt versions.

### Trends

`GET /trends`

Returns trend memory and velocity.

`GET /trends/{trend_id}`

Returns linked signals and historical movement.

### Content Opportunities

`GET /content-opportunities`

Filters:

- status
- content type
- topic
- created date

`PATCH /content-opportunities/{id}/status`

Updates review state.

Request:

```json
{
  "status": "approved",
  "reviewer": "reviewer@tada.com",
  "comments": "Good for newsletter draft."
}
```

### Reports

`POST /reports/daily`

Generates Daily Intelligence Digest.

`POST /reports/weekly`

Generates Weekly Strategic Report.

`GET /reports/{report_id}`

Returns report JSON.

## Internal Service APIs

### Processing Service

`POST /internal/process-article`

Input:

```json
{
  "article_id": "uuid",
  "prompt_version": "article-processing-v1"
}
```

Output:

```json
{
  "article_id": "uuid",
  "short_summary": "...",
  "keywords": ["tariff", "supplier risk"],
  "risks": ["Tariff exposure"],
  "opportunities": ["Supplier risk management"]
}
```

### Scoring Service

`POST /internal/score-signal`

Output includes five scoring dimensions and final weighted score.

### Generation Service

`POST /internal/generate-content`

Creates draft content opportunities and briefings.

## Authentication And Authorization

Roles:

- Admin: manage sources, settings, users
- Analyst: run ingestion, edit generated outputs, create reports
- Reviewer: approve, reject, comment
- Executive Viewer: read approved reports and briefings
- Sales Viewer: read approved sales talking points

All write actions should emit audit events.

