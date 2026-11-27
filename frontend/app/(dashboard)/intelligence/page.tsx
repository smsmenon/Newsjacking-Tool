'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Filter, SortAsc, ExternalLink, Calendar, BarChart2 } from 'lucide-react';
import { useArticles } from '@/lib/api';
import type { Article, SourceType } from '@/lib/types';
import { SearchBar } from '@/components/search/SearchBar';
import { cn } from '@/lib/utils';

// ─── Article Card ─────────────────────────────────────────────

function ArticleCard({ article }: { article: Article }) {
  const sentimentColor =
    article.sentimentScore > 0.2
      ? 'text-signal-opportunity'
      : article.sentimentScore < -0.2
      ? 'text-signal-risk'
      : 'text-yellow-400';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="group rounded-lg border border-surface-border bg-surface-elevated p-4 hover:border-brand-500/40 transition-all"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className="rounded border border-surface-border px-1.5 py-0.5 uppercase font-semibold">
            {article.sourceType}
          </span>
          <span>{article.source}</span>
        </div>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <ExternalLink className="h-3 w-3 text-muted-foreground hover:text-brand-400" />
        </a>
      </div>

      {/* Title */}
      <h3 className="font-medium text-foreground text-sm leading-snug line-clamp-2 mb-2 group-hover:text-brand-300 transition-colors">
        {article.title}
      </h3>

      {/* Summary */}
      <p className="text-xs text-muted-foreground line-clamp-3 mb-3">{article.summary}</p>

      {/* Tags */}
      <div className="flex flex-wrap gap-1 mb-3">
        {article.tags.slice(0, 4).map((tag) => (
          <span
            key={tag}
            className="rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1">
          <Calendar className="h-3 w-3" />
          {new Date(article.publishedAt).toLocaleDateString()}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <BarChart2 className="h-3 w-3" />
            <span className="font-mono">{Math.round(article.relevanceScore * 100)}</span>
          </div>
          <span className={cn('font-semibold', sentimentColor)}>
            {article.sentimentScore > 0.2 ? '+' : ''}{article.sentimentScore.toFixed(2)}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Sidebar Filters ──────────────────────────────────────────

const SOURCE_TYPES: SourceType[] = ['news', 'blog', 'social', 'research', 'regulatory', 'podcast'];
const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'date',      label: 'Date' },
  { value: 'score',     label: 'Score' },
] as const;

function FilterSidebar({
  filters,
  onFiltersChange,
}: {
  filters: { sourceType?: string; sortBy?: string };
  onFiltersChange: (f: typeof filters) => void;
}) {
  return (
    <aside className="w-56 shrink-0 space-y-6">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Source Type</p>
        <div className="space-y-1">
          <button
            onClick={() => onFiltersChange({ ...filters, sourceType: undefined })}
            className={cn(
              'w-full text-left rounded px-2 py-1.5 text-xs transition-colors',
              !filters.sourceType ? 'bg-brand-500/20 text-brand-300' : 'text-muted-foreground hover:text-foreground hover:bg-surface-elevated'
            )}
          >
            All Sources
          </button>
          {SOURCE_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => onFiltersChange({ ...filters, sourceType: t })}
              className={cn(
                'w-full text-left rounded px-2 py-1.5 text-xs capitalize transition-colors',
                filters.sourceType === t ? 'bg-brand-500/20 text-brand-300' : 'text-muted-foreground hover:text-foreground hover:bg-surface-elevated'
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sort By</p>
        <div className="space-y-1">
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onFiltersChange({ ...filters, sortBy: opt.value })}
              className={cn(
                'w-full text-left rounded px-2 py-1.5 text-xs transition-colors',
                filters.sortBy === opt.value ? 'bg-brand-500/20 text-brand-300' : 'text-muted-foreground hover:text-foreground hover:bg-surface-elevated'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function IntelligencePage() {
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState<{ sourceType?: string; sortBy?: string }>({
    sortBy: 'relevance',
  });
  const [page, setPage] = useState(1);

  const { data, isLoading } = useArticles({
    page,
    pageSize: 18,
    search: search || undefined,
    sourceType: filters.sourceType as SourceType | undefined,
    sortBy: (filters.sortBy as 'relevance' | 'date' | 'score') ?? 'relevance',
  });

  const articles = data?.data ?? [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Market Intelligence Explorer</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Browse and filter all collected intelligence
          {data?.total !== undefined && ` · ${data.total.toLocaleString()} items`}
        </p>
      </div>

      {/* Search */}
      <SearchBar
        value={search}
        onChange={setSearch}
        onSearch={(q) => { setSearch(q); setPage(1); }}
        showModeSelector={false}
        placeholder="Filter by keyword…"
      />

      {/* Body */}
      <div className="flex gap-6">
        <FilterSidebar filters={filters} onFiltersChange={(f) => { setFilters(f); setPage(1); }} />

        <div className="flex-1 space-y-4">
          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[...Array(9)].map((_, i) => (
                <div key={i} className="h-52 skeleton rounded-lg" />
              ))}
            </div>
          ) : articles.length === 0 ? (
            <div className="flex h-64 items-center justify-center rounded-lg border border-surface-border">
              <p className="text-muted-foreground text-sm">No articles found. Try adjusting your filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {articles.map((a) => <ArticleCard key={a.id} article={a} />)}
            </div>
          )}

          {/* Pagination */}
          {(data?.hasMore || page > 1) && (
            <div className="flex items-center justify-center gap-3 pt-4">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="text-xs text-muted-foreground">Page {page}</span>
              <button
                disabled={!data?.hasMore}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
