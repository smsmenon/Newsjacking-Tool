'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { TrendingUp, ArrowUpRight, Zap } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import { useTrends } from '@/lib/api';
import type { Trend } from '@/lib/types';
import { cn } from '@/lib/utils';

// ─── Trend Mini Chart ─────────────────────────────────────────

function TrendMiniChart({ data }: { data: Trend['timelineData'] }) {
  const chartData = data.map((d) => ({ value: d.mentionCount, date: d.date }));
  return (
    <ResponsiveContainer width="100%" height={48}>
      <LineChart data={chartData}>
        <Line
          type="monotone"
          dataKey="value"
          stroke="#6366f1"
          strokeWidth={1.5}
          dot={false}
        />
        <Tooltip
          contentStyle={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 6, fontSize: 10 }}
          labelFormatter={() => ''}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ─── Momentum badge ───────────────────────────────────────────

const MOMENTUM_CONFIG = {
  accelerating:  { label: 'Accelerating', color: 'text-signal-opportunity', arrow: '↑↑' },
  steady:        { label: 'Steady',        color: 'text-signal-trend',       arrow: '→'  },
  decelerating:  { label: 'Decelerating',  color: 'text-signal-threat',      arrow: '↓'  },
  emerging:      { label: 'Emerging',      color: 'text-signal-emerging',    arrow: '↗'  },
} as const;

// ─── Trend Card ───────────────────────────────────────────────

function TrendCard({ trend }: { trend: Trend }) {
  const momentum = MOMENTUM_CONFIG[trend.momentum] ?? MOMENTUM_CONFIG.steady;

  return (
    <Link href={`/trends/${trend.id}`}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="group rounded-lg border border-surface-border bg-surface-elevated p-4 hover:border-brand-500/40 hover:shadow-glow-brand transition-all"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <span className="rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 text-[10px] uppercase font-semibold text-muted-foreground">
            {trend.category}
          </span>
          <div className="flex items-center gap-1 text-xs font-semibold shrink-0">
            <span className={momentum.color}>{momentum.arrow}</span>
            <span className={cn('text-[10px]', momentum.color)}>{momentum.label}</span>
          </div>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-foreground leading-snug line-clamp-2 mb-2 group-hover:text-brand-300 transition-colors">
          {trend.title}
        </h3>

        <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{trend.description}</p>

        {/* Mini chart */}
        {trend.timelineData.length > 1 && <TrendMiniChart data={trend.timelineData} />}

        {/* Footer */}
        <div className="flex items-center justify-between mt-3 text-[10px] text-muted-foreground">
          <div className="flex items-center gap-2">
            <span>{trend.articleCount} articles</span>
            <span className="capitalize">{trend.maturityLevel}</span>
          </div>
          <div className="flex items-center gap-1 font-mono font-bold text-brand-400">
            {Math.round(trend.momentumScore * 100)}
            <ArrowUpRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </div>
      </motion.div>
    </Link>
  );
}

// ─── Category Tab ─────────────────────────────────────────────

const CATEGORIES = ['All', 'Technology', 'Market', 'Regulatory', 'Competitive', 'Social', 'Economic'];

// ─── Page ────────────────────────────────────────────────────

export default function TrendsPage() {
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [momentumFilter, setMomentumFilter] = useState<string>('all');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useTrends({
    page,
    pageSize: 12,
    category: categoryFilter === 'All' ? undefined : categoryFilter,
    momentum: momentumFilter === 'all' ? undefined : momentumFilter,
  });

  const trends = data?.data ?? [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-signal-trend" />
            Trends
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Macro and micro trends with momentum indicators
            {data?.total !== undefined && ` · ${data.total} tracked`}
          </p>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-surface-border pb-3">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => { setCategoryFilter(cat); setPage(1); }}
            className={cn(
              'rounded-md px-3 py-1.5 text-xs font-medium transition-all',
              categoryFilter === cat
                ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30'
                : 'text-muted-foreground hover:text-foreground hover:bg-surface-elevated'
            )}
          >
            {cat}
          </button>
        ))}
        <div className="ml-auto">
          <select
            value={momentumFilter}
            onChange={(e) => { setMomentumFilter(e.target.value); setPage(1); }}
            className="rounded-md border border-surface-border bg-surface-elevated px-3 py-1.5 text-xs text-foreground outline-none"
          >
            <option value="all">All Momentum</option>
            <option value="accelerating">Accelerating</option>
            <option value="steady">Steady</option>
            <option value="decelerating">Decelerating</option>
            <option value="emerging">Emerging</option>
          </select>
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...Array(6)].map((_, i) => <div key={i} className="h-56 skeleton rounded-lg" />)}
        </div>
      ) : trends.length === 0 ? (
        <div className="flex h-64 items-center justify-center rounded-lg border border-surface-border">
          <p className="text-muted-foreground text-sm">No trends found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {trends.map((t) => <TrendCard key={t.id} trend={t} />)}
        </div>
      )}

      {/* Pagination */}
      {(data?.hasMore || page > 1) && (
        <div className="flex items-center justify-center gap-3">
          <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}
            className="rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed">
            Previous
          </button>
          <span className="text-xs text-muted-foreground">Page {page}</span>
          <button disabled={!data?.hasMore} onClick={() => setPage((p) => p + 1)}
            className="rounded-md border border-surface-border px-4 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed">
            Next
          </button>
        </div>
      )}
    </div>
  );
}
