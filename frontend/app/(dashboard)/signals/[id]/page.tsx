'use client';

import { use } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, ExternalLink, Lightbulb, Users, Target, BookOpen } from 'lucide-react';
import Link from 'next/link';
import { useSignal } from '@/lib/api';
import { SignalCard } from '@/components/signals/SignalCard';
import { cn } from '@/lib/utils';

// ─── TADA Perspective Panel ───────────────────────────────────

function TADAPerspectiveSection({ perspective }: { perspective: NonNullable<ReturnType<typeof useSignal>['data']>['perspective'] }) {
  const rows = [
    { label: 'What is happening?',      content: perspective.what              },
    { label: 'Why does it matter?',     content: perspective.why               },
    { label: 'Impact',                  content: perspective.impact            },
    { label: 'Traditional Approach',    content: perspective.traditionalApproach },
    { label: 'TADA Approach',           content: perspective.tadaApproach      },
  ];

  return (
    <div className="rounded-lg border border-brand-500/30 bg-brand-500/5 p-5 space-y-4">
      <h2 className="font-semibold text-brand-300 flex items-center gap-2">
        <Lightbulb className="h-4 w-4" />
        TADA Perspective
      </h2>
      <div className="space-y-4">
        {rows.map((row) => (
          <div key={row.label}>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{row.label}</p>
            <p className="text-sm text-foreground leading-relaxed">{row.content}</p>
          </div>
        ))}
      </div>
      {perspective.dataPoints.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Data Points</p>
          <ul className="space-y-1">
            {perspective.dataPoints.map((dp, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
                {dp}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Recommendations ──────────────────────────────────────────

const PRIORITY_COLORS = {
  immediate:   'text-signal-risk',
  short_term:  'text-signal-threat',
  long_term:   'text-signal-opportunity',
};

function RecommendationsSection({ recommendations }: { recommendations: NonNullable<ReturnType<typeof useSignal>['data']>['recommendations'] }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-elevated p-5 space-y-4">
      <h2 className="font-semibold text-foreground flex items-center gap-2">
        <Target className="h-4 w-4 text-accent-400" />
        Recommendations by Team
      </h2>
      <div className="space-y-4">
        {recommendations.map((rec, i) => (
          <div key={i} className="border-l-2 border-accent-500/30 pl-4">
            <div className="flex items-center gap-2 mb-1">
              <span className="rounded bg-accent-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-accent-300">
                {rec.team}
              </span>
              <span className={cn('text-[10px] font-medium uppercase', PRIORITY_COLORS[rec.priority])}>
                {rec.priority.replace('_', ' ')}
              </span>
            </div>
            <p className="text-sm font-medium text-foreground">{rec.action}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{rec.rationale}</p>
            <p className="text-xs text-accent-400 mt-0.5">Impact: {rec.estimatedImpact}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Source Articles ──────────────────────────────────────────

function SourceArticles({ articles }: { articles: NonNullable<ReturnType<typeof useSignal>['data']>['sourceArticles'] }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-elevated p-5 space-y-4">
      <h2 className="font-semibold text-foreground flex items-center gap-2">
        <BookOpen className="h-4 w-4 text-muted-foreground" />
        Source Articles ({articles.length})
      </h2>
      <div className="space-y-3">
        {articles.map((article) => (
          <a
            key={article.id}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-3 rounded-md p-2 hover:bg-surface-muted transition-colors"
          >
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-foreground group-hover:text-brand-300 line-clamp-1 transition-colors">
                {article.title}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {article.source} · {new Date(article.publishedAt).toLocaleDateString()}
              </p>
            </div>
            <ExternalLink className="h-3 w-3 shrink-0 mt-0.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </a>
        ))}
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function SignalDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: signal, isLoading } = useSignal(id);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 skeleton rounded" />
        <div className="h-48 skeleton rounded-lg" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-64 skeleton rounded-lg" />
          <div className="h-64 skeleton rounded-lg" />
        </div>
      </div>
    );
  }

  if (!signal) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Signal not found.</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6 max-w-5xl"
    >
      {/* Back */}
      <Link
        href="/signals"
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Signals
      </Link>

      {/* Title block */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase', `badge-${signal.type}`)}>
            {signal.type}
          </span>
          <span className="text-xs text-muted-foreground">{new Date(signal.detectedAt).toLocaleDateString()}</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground">{signal.title}</h1>
        <p className="mt-2 text-muted-foreground leading-relaxed">{signal.summary}</p>
      </div>

      {/* Scores */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Overall Score', value: signal.overallScore,    color: 'text-brand-400' },
          { label: 'Confidence',    value: signal.confidenceScore, color: 'text-accent-400' },
          { label: 'Strength',      value: signal.strengthScore,   color: 'text-signal-opportunity' },
          { label: 'Momentum',      value: signal.momentumScore,   color: 'text-signal-trend' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-lg border border-surface-border bg-surface-elevated p-4 text-center">
            <p className={cn('text-3xl font-bold font-mono', color)}>{Math.round(value * 100)}</p>
            <p className="text-[10px] text-muted-foreground mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* TADA Perspective */}
      <TADAPerspectiveSection perspective={signal.perspective} />

      {/* 2-col: Recommendations + Sources */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecommendationsSection recommendations={signal.recommendations} />
        <SourceArticles articles={signal.sourceArticles} />
      </div>

      {/* Content Ideas */}
      {signal.contentIdeas.length > 0 && (
        <div className="rounded-lg border border-surface-border bg-surface-elevated p-5">
          <h2 className="font-semibold text-foreground flex items-center gap-2 mb-4">
            <Lightbulb className="h-4 w-4 text-yellow-400" />
            Generated Content Ideas ({signal.contentIdeas.length})
          </h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {signal.contentIdeas.map((idea) => (
              <div key={idea.id} className="rounded-md border border-surface-border p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-semibold uppercase text-muted-foreground">
                    {idea.type.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-sm font-medium text-foreground">{idea.title}</p>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{idea.summary}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Signals */}
      {signal.relatedSignalIds.length > 0 && (
        <div>
          <h2 className="font-semibold text-foreground mb-4">Related Signals</h2>
          <p className="text-xs text-muted-foreground">
            {signal.relatedSignalIds.length} related signals.{' '}
            <Link href="/signals" className="text-brand-400 hover:text-brand-300">
              Browse all signals →
            </Link>
          </p>
        </div>
      )}
    </motion.div>
  );
}
