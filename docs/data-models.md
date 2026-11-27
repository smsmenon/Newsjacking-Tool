# Data Models

## Article

```json
{
  "id": "uuid",
  "source_id": "uuid",
  "title": "string",
  "author": "string",
  "source_name": "string",
  "publication_date": "datetime",
  "canonical_url": "string",
  "content_hash": "string",
  "category": "string",
  "full_text": "string",
  "short_summary": "string",
  "medium_summary": "string",
  "executive_summary": "string",
  "keywords": ["string"],
  "topics": ["string"],
  "companies": ["string"],
  "industries": ["string"],
  "locations": ["string"],
  "risks": ["string"],
  "opportunities": ["string"],
  "disruptions": ["string"]
}
```

## Signal

```json
{
  "id": "uuid",
  "article_id": "uuid",
  "headline": "string",
  "signal_type": "Technology Adoption",
  "summary": "string",
  "evidence": "string",
  "score": {
    "supply_chain_relevance": 8.5,
    "executive_importance": 7.0,
    "business_impact": 8.0,
    "technology_relevance": 7.5,
    "tada_alignment": 9.0,
    "final_score": 8.05
  },
  "surfaced": true
}
```

## TADA Perspective

```json
{
  "what_happened": "string",
  "why_it_matters": "string",
  "potential_impact": "string",
  "traditional_response": "string",
  "tada_response": "string",
  "detect": "string",
  "decide": "string",
  "do": "string"
}
```

## Content Opportunity

```json
{
  "linkedin_post": {
    "hook": "string",
    "narrative": "string",
    "key_insight": "string",
    "cta": "string"
  },
  "thought_leadership_article": {
    "title": "string",
    "executive_summary": "string",
    "outline": ["string"],
    "key_arguments": ["string"]
  },
  "newsletter_topic": {
    "headline": "string",
    "summary": "string",
    "three_key_takeaways": ["string"]
  },
  "review_status": "draft"
}
```

## Executive Briefing

```json
{
  "situation": "string",
  "risk": "string",
  "opportunity": "string",
  "recommendation": "string",
  "status": "draft"
}
```

## Review Event

```json
{
  "entity_type": "content_opportunity",
  "entity_id": "uuid",
  "from_status": "under_review",
  "to_status": "approved",
  "reviewer": "name@tada.com",
  "comments": "string",
  "created_at": "datetime"
}
```

