// ============================================================
// TADA Intelligence Platform - API Client + SWR Hooks
// ============================================================

import useSWR, { type SWRConfiguration } from 'swr';
import type {
  Signal,
  Article,
  Trend,
  Competitor,
  CompetitorEvent,
  ContentIdea,
  ReviewItem,
  KnowledgeGraph,
  ExecutiveBriefing,
  ROIMetrics,
  DashboardStats,
  PaginatedResponse,
  SearchResult,
  SavedSearch,
  Alert,
  SearchFilters,
  SearchMode,
} from './types';

// ─── Config ─────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

// ─── Core Fetcher ────────────────────────────────────────────

async function fetcher<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      // Auth header will be injected by Clerk middleware on the server side
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Network error' }));
    throw new Error(error.message ?? `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

// ─── SWR Default Config ──────────────────────────────────────

export const SWR_CONFIG: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 30_000,
  errorRetryCount: 3,
};

// ─── Dashboard ───────────────────────────────────────────────

export function useDashboardStats() {
  return useSWR<DashboardStats>(apiUrl('/dashboard/stats'), fetcher, {
    ...SWR_CONFIG,
    refreshInterval: 60_000,
  });
}

// ─── Signals ─────────────────────────────────────────────────

export interface SignalsParams {
  page?: number;
  pageSize?: number;
  type?: string;
  urgency?: string;
  dateFrom?: string;
  dateTo?: string;
  sortBy?: 'score' | 'date' | 'urgency';
  search?: string;
}

export function useSignals(params: SignalsParams = {}) {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return useSWR<PaginatedResponse<Signal>>(
    apiUrl(`/signals?${qs}`),
    fetcher,
    SWR_CONFIG
  );
}

export function useSignal(id: string | null) {
  return useSWR<Signal>(id ? apiUrl(`/signals/${id}`) : null, fetcher, SWR_CONFIG);
}

export async function approveSignal(id: string): Promise<void> {
  await fetcher(apiUrl(`/signals/${id}/approve`), { method: 'POST' });
}

// ─── Articles / Intelligence ──────────────────────────────────

export interface ArticlesParams {
  page?: number;
  pageSize?: number;
  sourceType?: string;
  topic?: string;
  dateFrom?: string;
  dateTo?: string;
  sortBy?: 'relevance' | 'date' | 'score';
  search?: string;
  scoreMin?: number;
}

export function useArticles(params: ArticlesParams = {}) {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return useSWR<PaginatedResponse<Article>>(
    apiUrl(`/articles?${qs}`),
    fetcher,
    SWR_CONFIG
  );
}

export function useArticle(id: string | null) {
  return useSWR<Article>(id ? apiUrl(`/articles/${id}`) : null, fetcher, SWR_CONFIG);
}

// ─── Trends ──────────────────────────────────────────────────

export interface TrendsParams {
  page?: number;
  pageSize?: number;
  category?: string;
  momentum?: string;
  search?: string;
}

export function useTrends(params: TrendsParams = {}) {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return useSWR<PaginatedResponse<Trend>>(
    apiUrl(`/trends?${qs}`),
    fetcher,
    SWR_CONFIG
  );
}

export function useTrend(id: string | null) {
  return useSWR<Trend>(id ? apiUrl(`/trends/${id}`) : null, fetcher, SWR_CONFIG);
}

// ─── Competitors ─────────────────────────────────────────────

export function useCompetitors() {
  return useSWR<Competitor[]>(apiUrl('/competitors'), fetcher, {
    ...SWR_CONFIG,
    refreshInterval: 120_000,
  });
}

export function useCompetitor(id: string | null) {
  return useSWR<Competitor>(id ? apiUrl(`/competitors/${id}`) : null, fetcher, SWR_CONFIG);
}

export function useCompetitorEvents(params: { competitorId?: string; limit?: number } = {}) {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return useSWR<CompetitorEvent[]>(apiUrl(`/competitors/events?${qs}`), fetcher, SWR_CONFIG);
}

// ─── Content ─────────────────────────────────────────────────

export interface ContentParams {
  page?: number;
  pageSize?: number;
  type?: string;
  status?: string;
  dateFrom?: string;
  dateTo?: string;
}

export function useContentIdeas(params: ContentParams = {}) {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return useSWR<PaginatedResponse<ContentIdea>>(
    apiUrl(`/content?${qs}`),
    fetcher,
    SWR_CONFIG
  );
}

export async function updateContentStatus(
  id: string,
  status: ContentIdea['status']
): Promise<ContentIdea> {
  return fetcher<ContentIdea>(apiUrl(`/content/${id}/status`), {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

// ─── Review Queue ─────────────────────────────────────────────

export interface ReviewParams {
  itemType?: ReviewItem['itemType'];
  status?: ReviewItem['status'];
  assignedTo?: string;
  page?: number;
  pageSize?: number;
}

export function useReviewQueue(params: ReviewParams = {}) {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return useSWR<PaginatedResponse<ReviewItem>>(
    apiUrl(`/review?${qs}`),
    fetcher,
    SWR_CONFIG
  );
}

export async function submitReview(
  id: string,
  action: 'approve' | 'reject' | 'request_changes',
  feedback?: string
): Promise<ReviewItem> {
  return fetcher<ReviewItem>(apiUrl(`/review/${id}`), {
    method: 'POST',
    body: JSON.stringify({ action, feedback }),
  });
}

export async function assignReviewer(id: string, userId: string): Promise<ReviewItem> {
  return fetcher<ReviewItem>(apiUrl(`/review/${id}/assign`), {
    method: 'PATCH',
    body: JSON.stringify({ userId }),
  });
}

// ─── Knowledge Graph ─────────────────────────────────────────

export function useKnowledgeGraph(entityTypes?: string[]) {
  const qs = entityTypes?.length
    ? `?types=${entityTypes.join(',')}`
    : '';
  return useSWR<KnowledgeGraph>(
    apiUrl(`/graph${qs}`),
    fetcher,
    { ...SWR_CONFIG, revalidateOnFocus: false }
  );
}

// ─── Executive Briefing ──────────────────────────────────────

export function useExecutiveBriefings() {
  return useSWR<ExecutiveBriefing[]>(apiUrl('/briefings'), fetcher, SWR_CONFIG);
}

export function useLatestBriefing() {
  return useSWR<ExecutiveBriefing>(apiUrl('/briefings/latest'), fetcher, {
    ...SWR_CONFIG,
    refreshInterval: 300_000,
  });
}

export async function generateBriefingPDF(id: string): Promise<{ url: string }> {
  return fetcher<{ url: string }>(apiUrl(`/briefings/${id}/pdf`), { method: 'POST' });
}

// ─── Analytics / ROI ─────────────────────────────────────────

export function useROIMetrics(period: '7d' | '30d' | '90d' = '30d') {
  return useSWR<ROIMetrics>(apiUrl(`/analytics/roi?period=${period}`), fetcher, {
    ...SWR_CONFIG,
    refreshInterval: 300_000,
  });
}

// ─── Search ──────────────────────────────────────────────────

export async function search(
  query: string,
  mode: SearchMode,
  filters: SearchFilters,
  page = 1,
  pageSize = 20
): Promise<PaginatedResponse<SearchResult>> {
  return fetcher<PaginatedResponse<SearchResult>>(apiUrl('/search'), {
    method: 'POST',
    body: JSON.stringify({ query, mode, filters, page, pageSize }),
  });
}

export function useSavedSearches() {
  return useSWR<SavedSearch[]>(apiUrl('/search/saved'), fetcher, SWR_CONFIG);
}

export async function saveSearch(
  name: string,
  query: string,
  mode: SearchMode,
  filters: SearchFilters
): Promise<SavedSearch> {
  return fetcher<SavedSearch>(apiUrl('/search/saved'), {
    method: 'POST',
    body: JSON.stringify({ name, query, mode, filters }),
  });
}

export async function deleteSavedSearch(id: string): Promise<void> {
  await fetcher(apiUrl(`/search/saved/${id}`), { method: 'DELETE' });
}

// ─── Alerts ──────────────────────────────────────────────────

export function useAlerts(unreadOnly = false) {
  return useSWR<Alert[]>(
    apiUrl(`/alerts${unreadOnly ? '?unread=true' : ''}`),
    fetcher,
    { ...SWR_CONFIG, refreshInterval: 30_000 }
  );
}

export async function markAlertRead(id: string): Promise<void> {
  await fetcher(apiUrl(`/alerts/${id}/read`), { method: 'PATCH' });
}

export async function markAllAlertsRead(): Promise<void> {
  await fetcher(apiUrl('/alerts/read-all'), { method: 'POST' });
}
