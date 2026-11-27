'use client';

import { useState, useTransition } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search as SearchIcon, Bookmark, BookmarkCheck, ExternalLink, Filter } from 'lucide-react';
import { SearchBar } from '@/components/search/SearchBar';
import { search as searchApi, saveSearch, useSavedSearches } from '@/lib/api';
import type { SearchMode, SearchFilters, SearchResult } from '@/lib/types';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// ─── Result Card ──────────────────────────────────────────────

function ResultCard({ result }: { result: SearchResult }) {
  const typeColors: Record<string, string> = {
    article: 'text-brand-400',
    signal:  'text-signal-trend',
    trend:   'text-signal-opportunity',
    content: 'text-yellow-400',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="group rounded-lg border border-surface-border bg-surface-elevated p-4 hover:border-brand-500/40 transition-all"
    >
      <div className="flex items-start gap-4">
        {/* Score */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-surface-muted">
          <span className="text-xs font-bold font-mono text-brand-400">
            {Math.round(result.relevanceScore * 100)}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 mb-1">
              <span className={cn('text-[10px] font-semibold uppercase', typeColors[result.type] ?? 'text-muted-foreground')}>
                {result.type}
              </span>
              {result.source && (
                <span className="text-[10px] text-muted-foreground">{result.source}</span>
              )}
              <span className="text-[10px] text-muted-foreground">
                {new Date(result.date).toLocaleDateString()}
              </span>
            </div>
            {result.url && (
              <a href={result.url} target="_blank" rel="noopener noreferrer"
                className="opacity-0 group-hover:opacity-100 transition-opacity">
                <ExternalLink className="h-3 w-3 text-muted-foreground hover:text-brand-400" />
              </a>
            )}
          </div>
          <h3 className="font-medium text-foreground text-sm leading-snug mb-1 group-hover:text-brand-300 transition-colors">
            {result.title}
          </h3>
          <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{result.summary}</p>
          {/* Relevance explanation */}
          <p className="text-[10px] text-accent-400 italic">{result.relevanceExplanation}</p>
          {/* Tags */}
          <div className="flex flex-wrap gap-1 mt-2">
            {result.tags.slice(0, 4).map((t) => (
              <span key={t} className="rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Filter Panel ─────────────────────────────────────────────

function FilterPanel({
  filters,
  onFiltersChange,
}: {
  filters: SearchFilters;
  onFiltersChange: (f: SearchFilters) => void;
}) {
  return (
    <aside className="w-56 shrink-0 rounded-lg border border-surface-border bg-surface-elevated p-4 h-fit space-y-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
        <Filter className="h-3 w-3" />
        Filters
      </p>

      {/* Date range */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Date Range</p>
        <div className="space-y-1.5">
          <input type="date" value={filters.dateFrom ?? ''} onChange={(e) => onFiltersChange({ ...filters, dateFrom: e.target.value })}
            className="w-full rounded border border-surface-border bg-surface-muted px-2 py-1 text-[11px] text-foreground outline-none" />
          <input type="date" value={filters.dateTo ?? ''} onChange={(e) => onFiltersChange({ ...filters, dateTo: e.target.value })}
            className="w-full rounded border border-surface-border bg-surface-muted px-2 py-1 text-[11px] text-foreground outline-none" />
        </div>
      </div>

      {/* Score range */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Min Relevance Score: <span className="text-brand-400">{filters.scoreMin ?? 0}</span>
        </p>
        <input
          type="range" min={0} max={100} value={(filters.scoreMin ?? 0) * 100}
          onChange={(e) => onFiltersChange({ ...filters, scoreMin: parseInt(e.target.value) / 100 })}
          className="w-full accent-brand-500"
        />
      </div>

      {/* Reset */}
      <button
        onClick={() => onFiltersChange({})}
        className="w-full rounded border border-surface-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-brand-500/40 transition-colors"
      >
        Reset Filters
      </button>
    </aside>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function SearchPage() {
  const [query, setQuery]         = useState('');
  const [mode, setMode]           = useState<SearchMode>('hybrid');
  const [filters, setFilters]     = useState<SearchFilters>({});
  const [results, setResults]     = useState<SearchResult[]>([]);
  const [total, setTotal]         = useState(0);
  const [page, setPage]           = useState(1);
  const [hasSearched, setHasSearched] = useState(false);
  const [isPending, startTransition] = useTransition();

  const { data: savedSearches } = useSavedSearches();

  const handleSearch = (q: string, m: SearchMode, p = 1) => {
    if (!q.trim()) return;
    startTransition(async () => {
      try {
        const res = await searchApi(q, m, filters, p, 20);
        setResults(res.data);
        setTotal(res.total);
        setPage(p);
        setHasSearched(true);
      } catch (e) {
        toast.error('Search failed. Please try again.');
      }
    });
  };

  const handleSaveSearch = async () => {
    if (!query.trim()) return;
    try {
      await saveSearch(`Search: ${query}`, query, mode, filters);
      toast.success('Search saved!');
    } catch {
      toast.error('Failed to save search.');
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <SearchIcon className="h-6 w-6 text-brand-400" />
          Advanced Search
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Keyword, semantic, and hybrid search across all collected intelligence
        </p>
      </div>

      {/* Search Bar */}
      <SearchBar
        value={query}
        mode={mode}
        onChange={setQuery}
        onModeChange={setMode}
        onSearch={(q, m) => handleSearch(q, m, 1)}
        autoFocus
        showModeSelector
        placeholder="Search across all intelligence, signals, and trends…"
      />

      {/* Saved Searches */}
      {savedSearches && savedSearches.length > 0 && !hasSearched && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">Saved searches:</p>
          <div className="flex flex-wrap gap-2">
            {savedSearches.map((s) => (
              <button
                key={s.id}
                onClick={() => { setQuery(s.query); setMode(s.mode); handleSearch(s.query, s.mode, 1); }}
                className="flex items-center gap-1.5 rounded-full border border-surface-border bg-surface-elevated px-3 py-1 text-xs text-muted-foreground hover:text-foreground hover:border-brand-500/40 transition-colors"
              >
                <BookmarkCheck className="h-3 w-3 text-brand-400" />
                {s.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex gap-6">
        <FilterPanel filters={filters} onFiltersChange={setFilters} />

        <div className="flex-1 space-y-4">
          {/* Results header */}
          {hasSearched && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {isPending ? 'Searching…' : `${total} results for "${query}"`}
              </p>
              <button
                onClick={handleSaveSearch}
                className="flex items-center gap-1.5 rounded border border-surface-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-brand-500/40 transition-colors"
              >
                <Bookmark className="h-3 w-3" />
                Save Search
              </button>
            </div>
          )}

          {/* Loading */}
          {isPending && (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => <div key={i} className="h-28 skeleton rounded-lg" />)}
            </div>
          )}

          {/* Empty state */}
          {!isPending && !hasSearched && (
            <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-surface-border">
              <SearchIcon className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Enter a query above to search intelligence</p>
            </div>
          )}

          {/* No results */}
          {!isPending && hasSearched && results.length === 0 && (
            <div className="flex h-64 items-center justify-center rounded-lg border border-surface-border">
              <p className="text-muted-foreground text-sm">No results found. Try a different query or mode.</p>
            </div>
          )}

          {/* Results */}
          <AnimatePresence mode="wait">
            {!isPending && results.length > 0 && (
              <div className="space-y-3">
                {results.map((r) => <ResultCard key={r.id} result={r} />)}
              </div>
            )}
          </AnimatePresence>

          {/* Pagination */}
          {hasSearched && !isPending && total > 20 && (
            <div className="flex items-center justify-center gap-3">
              <button disabled={page === 1} onClick={() => handleSearch(query, mode, page - 1)}
                className="rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed">
                Previous
              </button>
              <span className="text-xs text-muted-foreground">Page {page} of {Math.ceil(total / 20)}</span>
              <button disabled={page * 20 >= total} onClick={() => handleSearch(query, mode, page + 1)}
                className="rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed">
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
