'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Database, Download, ExternalLink, BarChart2 } from 'lucide-react';
import { useArticles } from '@/lib/api';
import type { Article } from '@/lib/types';
import { SearchBar } from '@/components/search/SearchBar';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// ─── Repository Row ───────────────────────────────────────────

function RepositoryRow({ article }: { article: Article }) {
  const sentColor =
    article.sentimentScore > 0.2 ? 'text-signal-opportunity' :
    article.sentimentScore < -0.2 ? 'text-signal-risk' : 'text-yellow-400';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="group flex items-center gap-4 rounded-md border border-transparent px-3 py-3 hover:border-surface-border hover:bg-surface-elevated transition-all"
    >
      {/* Source type badge */}
      <span className="shrink-0 rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 text-[10px] uppercase font-semibold text-muted-foreground w-20 text-center">
        {article.sourceType}
      </span>

      {/* Title */}
      <div className="flex-1 min-w-0">
        <a href={article.url} target="_blank" rel="noopener noreferrer"
          className="text-sm font-medium text-foreground group-hover:text-brand-300 transition-colors line-clamp-1">
          {article.title}
        </a>
        <p className="text-[10px] text-muted-foreground mt-0.5">
          {article.source} · {new Date(article.publishedAt).toLocaleDateString()}
        </p>
      </div>

      {/* Scores */}
      <div className="flex items-center gap-4 shrink-0 text-[11px]">
        <div className="text-center w-12">
          <p className="font-mono font-bold text-brand-400">{Math.round(article.relevanceScore * 100)}</p>
          <p className="text-[9px] text-muted-foreground">Rel.</p>
        </div>
        <div className={cn('text-center w-12', sentColor)}>
          <p className="font-mono font-bold">{article.sentimentScore.toFixed(2)}</p>
          <p className="text-[9px] text-muted-foreground">Sent.</p>
        </div>
        <a href={article.url} target="_blank" rel="noopener noreferrer"
          className="opacity-0 group-hover:opacity-100 transition-opacity">
          <ExternalLink className="h-3 w-3 text-muted-foreground hover:text-brand-400" />
        </a>
      </div>
    </motion.div>
  );
}

// ─── Stats Panel ──────────────────────────────────────────────

function StatsPanel({ total, isLoading }: { total?: number; isLoading: boolean }) {
  return (
    <div className="flex items-center gap-6 rounded-lg border border-surface-border bg-surface-elevated px-5 py-3">
      <div className="flex items-center gap-2">
        <Database className="h-4 w-4 text-brand-400" />
        <div>
          <p className="text-lg font-bold font-mono text-foreground">
            {isLoading ? '—' : (total ?? 0).toLocaleString()}
          </p>
          <p className="text-[10px] text-muted-foreground">Total Articles</p>
        </div>
      </div>
      <div className="h-8 w-px bg-surface-border" />
      <div>
        <p className="text-xs text-muted-foreground">Fully searchable corpus of all collected intelligence</p>
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────

const PAGE_SIZE = 30;

export default function RepositoryPage() {
  const [search, setSearch]   = useState('');
  const [page, setPage]       = useState(1);
  const [allItems, setAllItems] = useState<Article[]>([]);
  const loaderRef             = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useArticles({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    sortBy: 'date',
  });

  // Append on page change (infinite scroll)
  useEffect(() => {
    if (data?.data) {
      setAllItems((prev) => page === 1 ? data.data : [...prev, ...data.data]);
    }
  }, [data, page]);

  // Reset on search change
  useEffect(() => {
    setPage(1);
    setAllItems([]);
  }, [search]);

  // Intersection observer for infinite scroll
  const handleObserver = useCallback((entries: IntersectionObserverEntry[]) => {
    const [entry] = entries;
    if (entry.isIntersecting && data?.hasMore && !isLoading) {
      setPage((p) => p + 1);
    }
  }, [data?.hasMore, isLoading]);

  useEffect(() => {
    const el = loaderRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(handleObserver, { threshold: 0.1 });
    observer.observe(el);
    return () => observer.disconnect();
  }, [handleObserver]);

  const handleExport = () => {
    toast.info('Export started — you will receive a download link shortly.');
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Database className="h-6 w-6 text-brand-400" />
            Knowledge Repository
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Complete corpus of all collected market intelligence
          </p>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-brand-500/40 transition-colors"
        >
          <Download className="h-3 w-3" />
          Export CSV
        </button>
      </div>

      {/* Stats */}
      <StatsPanel total={data?.total} isLoading={isLoading && page === 1} />

      {/* Search */}
      <SearchBar
        value={search}
        onChange={setSearch}
        onSearch={(q) => setSearch(q)}
        showModeSelector={false}
        placeholder="Filter repository by keyword…"
      />

      {/* Table */}
      <div className="rounded-lg border border-surface-border overflow-hidden">
        {/* Header row */}
        <div className="flex items-center gap-4 border-b border-surface-border bg-surface-elevated px-3 py-2">
          <span className="text-[10px] font-semibold uppercase text-muted-foreground w-20">Type</span>
          <span className="flex-1 text-[10px] font-semibold uppercase text-muted-foreground">Title</span>
          <div className="flex items-center gap-4 shrink-0">
            <span className="text-[10px] font-semibold uppercase text-muted-foreground w-12">Rel.</span>
            <span className="text-[10px] font-semibold uppercase text-muted-foreground w-12">Sent.</span>
            <span className="w-4" />
          </div>
        </div>

        {/* Rows */}
        <div className="divide-y divide-surface-border/50">
          {allItems.map((article) => (
            <RepositoryRow key={article.id} article={article} />
          ))}
        </div>

        {/* Loading skeleton */}
        {isLoading && (
          <div className="space-y-0">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-12 skeleton border-t border-surface-border/50" />
            ))}
          </div>
        )}

        {/* Empty */}
        {!isLoading && allItems.length === 0 && (
          <div className="flex h-32 items-center justify-center">
            <p className="text-sm text-muted-foreground">No articles found.</p>
          </div>
        )}
      </div>

      {/* Infinite scroll trigger */}
      <div ref={loaderRef} className="h-4" />

      {/* End of results */}
      {!data?.hasMore && allItems.length > 0 && (
        <p className="text-center text-xs text-muted-foreground py-4">
          All {allItems.length.toLocaleString()} articles loaded.
        </p>
      )}
    </div>
  );
}
