'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, Filter } from 'lucide-react';
import { useSignals } from '@/lib/api';
import { SignalCard } from '@/components/signals/SignalCard';
import type { SignalType, SignalUrgency } from '@/lib/types';
import { cn } from '@/lib/utils';

// ─── Filter Bar ───────────────────────────────────────────────

const TYPES: { value: SignalType | 'all'; label: string }[] = [
  { value: 'all',         label: 'All' },
  { value: 'risk',        label: 'Risks' },
  { value: 'opportunity', label: 'Opportunities' },
  { value: 'trend',       label: 'Trends' },
  { value: 'threat',      label: 'Threats' },
  { value: 'emerging',    label: 'Emerging' },
];

const URGENCIES: { value: SignalUrgency | 'all'; label: string }[] = [
  { value: 'all',      label: 'All Urgency' },
  { value: 'critical', label: 'Critical' },
  { value: 'high',     label: 'High' },
  { value: 'medium',   label: 'Medium' },
  { value: 'low',      label: 'Low' },
];

const SORT_OPTIONS = [
  { value: 'score', label: 'Score' },
  { value: 'date',  label: 'Date'  },
  { value: 'urgency', label: 'Urgency' },
] as const;

// ─── Page ────────────────────────────────────────────────────

export default function SignalsPage() {
  const [typeFilter, setTypeFilter]       = useState<SignalType | 'all'>('all');
  const [urgencyFilter, setUrgencyFilter] = useState<SignalUrgency | 'all'>('all');
  const [sortBy, setSortBy]               = useState<'score' | 'date' | 'urgency'>('score');
  const [page, setPage]                   = useState(1);

  const { data, isLoading } = useSignals({
    page,
    pageSize: 15,
    type:    typeFilter === 'all'    ? undefined : typeFilter,
    urgency: urgencyFilter === 'all' ? undefined : urgencyFilter,
    sortBy,
  });

  const signals = data?.data ?? [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Zap className="h-6 w-6 text-brand-400" />
            Signals
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI-detected market signals with TADA perspective
            {data?.total !== undefined && ` · ${data.total} signals`}
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Type Tabs */}
        <div className="flex rounded-lg border border-surface-border bg-surface-elevated p-1 gap-1">
          {TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => { setTypeFilter(t.value); setPage(1); }}
              className={cn(
                'rounded px-3 py-1.5 text-xs font-medium transition-all',
                typeFilter === t.value
                  ? 'bg-brand-500 text-white'
                  : 'text-muted-foreground hover:text-foreground hover:bg-surface-muted'
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Urgency select */}
        <select
          value={urgencyFilter}
          onChange={(e) => { setUrgencyFilter(e.target.value as SignalUrgency | 'all'); setPage(1); }}
          className="rounded-md border border-surface-border bg-surface-elevated px-3 py-1.5 text-xs text-foreground outline-none hover:border-brand-500/40 transition-colors"
        >
          {URGENCIES.map((u) => (
            <option key={u.value} value={u.value}>{u.label}</option>
          ))}
        </select>

        {/* Sort */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-muted-foreground">Sort:</span>
          <div className="flex rounded-md border border-surface-border bg-surface-elevated p-0.5 gap-0.5">
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setSortBy(opt.value)}
                className={cn(
                  'rounded px-2.5 py-1 text-xs transition-all',
                  sortBy === opt.value
                    ? 'bg-brand-500/30 text-brand-300'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="h-64 skeleton rounded-lg" />
          ))}
        </div>
      ) : signals.length === 0 ? (
        <div className="flex h-64 items-center justify-center rounded-lg border border-surface-border">
          <p className="text-muted-foreground text-sm">No signals match your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {signals.map((signal) => (
            <SignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {(data?.hasMore || page > 1) && (
        <div className="flex items-center justify-center gap-3">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-xs text-muted-foreground">Page {page} of {Math.ceil((data?.total ?? 0) / 15)}</span>
          <button
            disabled={!data?.hasMore}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
