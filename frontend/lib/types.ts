// ============================================================
// TADA Intelligence Platform - TypeScript Types
// ============================================================

// ─── Base Types ─────────────────────────────────────────────

export type UUID = string;

export type SignalType = 'risk' | 'opportunity' | 'trend' | 'threat' | 'emerging';
export type SignalUrgency = 'critical' | 'high' | 'medium' | 'low';
export type ContentStatus = 'draft' | 'approved' | 'scheduled' | 'published' | 'rejected';
export type ContentType =
  | 'linkedin_post'
  | 'article'
  | 'newsletter'
  | 'executive_briefing'
  | 'video_script'
  | 'podcast_outline'
  | 'webinar_outline'
  | 'case_study';
export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'changes_requested';
export type EntityType = 'company' | 'person' | 'technology' | 'market' | 'trend' | 'product';
export type SourceType = 'news' | 'blog' | 'social' | 'research' | 'regulatory' | 'podcast';

// ─── Signal ──────────────────────────────────────────────────

export interface Signal {
  id: UUID;
  title: string;
  summary: string;
  type: SignalType;
  urgency: SignalUrgency;
  confidenceScore: number;         // 0–1
  strengthScore: number;           // 0–1
  momentumScore: number;           // 0–1
  overallScore: number;            // 0–1
  sourceCount: number;
  tags: string[];
  categories: string[];
  detectedAt: string;              // ISO date
  updatedAt: string;
  perspective: TADAPerspective;
  recommendations: Recommendation[];
  relatedSignalIds: UUID[];
  contentIdeas: ContentIdea[];
  sourceArticles: Article[];
}

export interface TADAPerspective {
  what: string;
  why: string;
  impact: string;
  traditionalApproach: string;
  tadaApproach: string;
  dataPoints: string[];
}

export interface Recommendation {
  team: string;
  priority: 'immediate' | 'short_term' | 'long_term';
  action: string;
  rationale: string;
  estimatedImpact: string;
}

// ─── Article / Intelligence Item ─────────────────────────────

export interface Article {
  id: UUID;
  title: string;
  url: string;
  source: string;
  sourceType: SourceType;
  author?: string;
  publishedAt: string;
  collectedAt: string;
  summary: string;
  fullText?: string;
  relevanceScore: number;          // 0–1
  sentimentScore: number;          // -1 to 1
  tags: string[];
  topics: string[];
  companies: string[];
  entities: string[];
  signalIds: UUID[];
  trendIds: UUID[];
}

// ─── Trend ───────────────────────────────────────────────────

export interface Trend {
  id: UUID;
  title: string;
  description: string;
  category: string;
  momentum: 'accelerating' | 'steady' | 'decelerating' | 'emerging';
  momentumScore: number;           // 0–1
  relevanceScore: number;          // 0–1
  maturityLevel: 'emerging' | 'growing' | 'mainstream' | 'declining';
  timelineData: TrendDataPoint[];
  keyDrivers: string[];
  implications: string[];
  firstDetectedAt: string;
  updatedAt: string;
  tags: string[];
  relatedSignalIds: UUID[];
  articleCount: number;
}

export interface TrendDataPoint {
  date: string;                    // ISO date
  mentionCount: number;
  sentimentScore: number;
  relevanceScore: number;
}

// ─── Competitor ──────────────────────────────────────────────

export interface Competitor {
  id: UUID;
  name: string;
  website: string;
  description: string;
  logoUrl?: string;
  recentEvents: CompetitorEvent[];
  messagingGaps: MessagingGap[];
  strengthAreas: string[];
  weaknessAreas: string[];
  recentArticleCount: number;
  sentimentTrend: 'positive' | 'neutral' | 'negative';
  lastUpdated: string;
}

export interface CompetitorEvent {
  id: UUID;
  competitorId: UUID;
  eventType: 'product_launch' | 'funding' | 'partnership' | 'executive_change' | 'marketing' | 'regulatory';
  title: string;
  description: string;
  date: string;
  source: string;
  url?: string;
  significance: 'high' | 'medium' | 'low';
}

export interface MessagingGap {
  topic: string;
  competitorPosition: string;
  tadaOpportunity: string;
  priority: 'high' | 'medium' | 'low';
}

// ─── Content ─────────────────────────────────────────────────

export interface ContentIdea {
  id: UUID;
  title: string;
  type: ContentType;
  status: ContentStatus;
  summary: string;
  outline?: string[];
  fullContent?: string;
  targetAudience: string;
  estimatedImpact: string;
  generatedAt: string;
  scheduledFor?: string;
  publishedAt?: string;
  signalId?: UUID;
  trendId?: UUID;
  assignedTo?: string;
  tags: string[];
}

// ─── Review ──────────────────────────────────────────────────

export interface ReviewItem {
  id: UUID;
  itemType: 'insight' | 'recommendation' | 'content_idea' | 'briefing';
  itemId: UUID;
  title: string;
  summary: string;
  status: ReviewStatus;
  priority: 'critical' | 'high' | 'medium' | 'low';
  assignedTo?: string;
  reviewedBy?: string;
  reviewedAt?: string;
  feedback?: string;
  createdAt: string;
  updatedAt: string;
}

// ─── Entity (Knowledge Graph) ─────────────────────────────────

export interface Entity {
  id: UUID;
  name: string;
  type: EntityType;
  description?: string;
  properties: Record<string, unknown>;
  mentionCount: number;
  firstSeen: string;
  lastSeen: string;
}

export interface EntityRelationship {
  id: UUID;
  sourceEntityId: UUID;
  targetEntityId: UUID;
  relationshipType: string;
  weight: number;                  // 0–1
  evidenceCount: number;
  firstDetected: string;
}

export interface KnowledgeGraph {
  entities: Entity[];
  relationships: EntityRelationship[];
}

// ─── Executive Briefing ──────────────────────────────────────

export interface ExecutiveBriefing {
  id: UUID;
  title: string;
  period: string;                  // e.g. "Week of June 9–15, 2026"
  generatedAt: string;
  topRisks: Signal[];
  topOpportunities: Signal[];
  keyTrends: Trend[];
  competitorHighlights: CompetitorEvent[];
  strategicRecommendations: Recommendation[];
  marketSentiment: number;         // -1 to 1
  articlesCollected: number;
  signalsDetected: number;
  pdfUrl?: string;
}

// ─── Analytics / ROI ─────────────────────────────────────────

export interface AnalyticsMetric {
  label: string;
  value: number;
  unit?: string;
  trend: number;                   // % change vs prior period
  sparklineData: number[];
}

export interface ROIMetrics {
  articlesCollected: AnalyticsMetric;
  sourcesMonitored: AnalyticsMetric;
  signalsDetected: AnalyticsMetric;
  trendsTracked: AnalyticsMetric;
  contentIdeasGenerated: AnalyticsMetric;
  researchHoursSaved: AnalyticsMetric;
  activeUsers: AnalyticsMetric;
  reviewCompletionRate: AnalyticsMetric;
  weeklyTimeSeries: {
    week: string;
    articles: number;
    signals: number;
    content: number;
  }[];
}

// ─── Search ──────────────────────────────────────────────────

export type SearchMode = 'keyword' | 'semantic' | 'hybrid';

export interface SearchFilters {
  sourceTypes?: SourceType[];
  dateFrom?: string;
  dateTo?: string;
  topics?: string[];
  companies?: string[];
  scoreMin?: number;
  scoreMax?: number;
  signalTypes?: SignalType[];
}

export interface SearchResult {
  id: UUID;
  type: 'article' | 'signal' | 'trend' | 'content';
  title: string;
  summary: string;
  relevanceScore: number;
  relevanceExplanation: string;
  source?: string;
  date: string;
  tags: string[];
  url?: string;
}

export interface SavedSearch {
  id: UUID;
  name: string;
  query: string;
  mode: SearchMode;
  filters: SearchFilters;
  savedAt: string;
  lastRunAt?: string;
  resultCount?: number;
}

// ─── Notification / Alert ─────────────────────────────────────

export interface Alert {
  id: UUID;
  type: 'signal' | 'trend' | 'competitor' | 'system' | 'review';
  severity: 'critical' | 'high' | 'medium' | 'info';
  title: string;
  message: string;
  isRead: boolean;
  createdAt: string;
  linkedItemId?: UUID;
  linkedItemType?: string;
}

// ─── API Response Wrappers ────────────────────────────────────

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
  success: boolean;
}

// ─── Dashboard Stats ──────────────────────────────────────────

export interface DashboardStats {
  articlesCollectedToday: number;
  signalsDetectedThisWeek: number;
  trendsTracked: number;
  contentIdeasPending: number;
  reviewItemsPending: number;
  sourcesActive: number;
  marketSentiment: number;         // -1 to 1
  sentimentTrend: 'improving' | 'stable' | 'declining';
}
