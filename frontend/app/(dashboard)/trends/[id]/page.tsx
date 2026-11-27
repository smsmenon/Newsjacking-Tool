'use client';

import { use } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { useTrend } from '@/lib/api';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';

// ─── Tooltip ─────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-surface-border bg-surface-elevated p-3 shadow-elevated text-xs">
      <p className="font-medium text-foreground mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-mono font-medium">{p.value}</span>
        </p>
      ))}
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function TrendDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: trend, isLoading } = useTrend(id);

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div className="h-8 w-48 skeleton rounded" />
        <div className="h-32 skeleton rounded-lg" />
        <div className="h-72 skeleton rounded-lg" />
      </div>
    );
  }

  if (!trend) {
    return <div className="flex h-64 items-center justify-center"><p className="text-muted-foreground">Trend not found.</p></div>;
  }

  const chartData = trend.timelineData.map((d) => ({
    date:      format(new Date(d.date), 'MMM d'),
    Mentions:  d.mentionCount,
    Sentiment: parseFloat((d.sentimentScore * 100).toFixed(1)),
    Relevance: parseFloat((d.relevanceScore * 100).toFixed(1)),
  }));

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 max-w-5xl">
      {/* Back */}
      <Link href="/trends" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" />
        Back to Trends
      </Link>

      {/* Header */}
      <div>
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <span className="rounded border border-surface-border bg-surface-muted px-2 py-0.5 text-[10px] uppercase font-semibold text-muted-foreground">
            {trend.category}
          </span>
          <span className="text-[10px] text-muted-foreground capitalize">{trend.maturityLevel} · {trend.momentum}</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground">{trend.title}</h1>
        <p className="mt-2 text-muted-foreground leading-relaxed">{trend.description}</p>
      </div>

      {/* Score cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: 'Momentum Score', value: trend.momentumScore,   color: 'text-brand-400' },
          { label: 'Relevance',      value: trend.relevanceScore,  color: 'text-accent-400' },
          { label: 'Article Count',  value: trend.articleCount,    color: 'text-signal-opportunity', raw: true },
          { label: 'Related Signals',value: trend.relatedSignalIds.length, color: 'text-signal-trend', raw: true },
        ].map(({ label, value, color, raw }) => (
          <div key={label} className="rounded-lg border border-surface-border bg-surface-elevated p-4 text-center">
            <p className={cn('text-3xl font-bold font-mono', color)}>
              {raw ? value : Math.round((value as number) * 100)}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Timeline Chart */}
      <div className="rounded-lg border border-surface-border bg-surface-elevated p-6">
        <h2 className="font-semibold text-foreground mb-4 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-brand-400" />
          Trend Timeline
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="mentionGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0}   />
              </linearGradient>
              <linearGradient id="relevanceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#06b6d4" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}   />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="date" tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="left"  tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#8b949e' }} />
            <Area yAxisId="left"  type="monotone" dataKey="Mentions"  stroke="#6366f1" fill="url(#mentionGrad)"   strokeWidth={2} />
            <Line  yAxisId="right" type="monotone" dataKey="Relevance" stroke="#06b6d4" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Key Drivers + Implications */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="rounded-lg border border-surface-border bg-surface-elevated p-5">
          <h2 className="font-semibold text-foreground mb-3">Key Drivers</h2>
          <ul className="space-y-2">
            {trend.keyDrivers.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                {d}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-surface-border bg-surface-elevated p-5">
          <h2 className="font-semibold text-foreground mb-3">Implications</h2>
          <ul className="space-y-2">
            {trend.implications.map((impl, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-500" />
                {impl}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-2">
        {trend.tags.map((tag) => (
          <span key={tag} className="rounded border border-surface-border bg-surface-muted px-2 py-1 text-xs text-muted-foreground">
            {tag}
          </span>
        ))}
      </div>
    </motion.div>
  );
}
