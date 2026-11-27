'use client';

import { motion } from 'framer-motion';
import { Users, ExternalLink, AlertCircle } from 'lucide-react';
import { useCompetitors, useCompetitorEvents } from '@/lib/api';
import type { Competitor, CompetitorEvent } from '@/lib/types';
import { cn } from '@/lib/utils';

// ─── Competitor Card ──────────────────────────────────────────

function CompetitorCard({ competitor }: { competitor: Competitor }) {
  const sentimentColor =
    competitor.sentimentTrend === 'positive'
      ? 'text-signal-opportunity'
      : competitor.sentimentTrend === 'negative'
      ? 'text-signal-risk'
      : 'text-yellow-400';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-surface-border bg-surface-elevated p-5 hover:border-brand-500/40 transition-all"
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="font-semibold text-foreground">{competitor.name}</h3>
          <a
            href={competitor.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-brand-400 transition-colors mt-0.5"
          >
            {competitor.website} <ExternalLink className="h-3 w-3" />
          </a>
        </div>
        <span className={cn('text-xs font-semibold capitalize', sentimentColor)}>
          {competitor.sentimentTrend}
        </span>
      </div>

      <p className="text-xs text-muted-foreground line-clamp-2 mb-4">{competitor.description}</p>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <p className="text-[10px] text-muted-foreground uppercase font-semibold mb-1">Strengths</p>
          <ul className="space-y-0.5">
            {competitor.strengthAreas.slice(0, 3).map((s, i) => (
              <li key={i} className="flex items-center gap-1 text-[11px] text-foreground">
                <span className="h-1 w-1 rounded-full bg-signal-opportunity shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground uppercase font-semibold mb-1">Weaknesses</p>
          <ul className="space-y-0.5">
            {competitor.weaknessAreas.slice(0, 3).map((w, i) => (
              <li key={i} className="flex items-center gap-1 text-[11px] text-foreground">
                <span className="h-1 w-1 rounded-full bg-signal-risk shrink-0" />
                {w}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="flex items-center justify-between text-[10px] text-muted-foreground border-t border-surface-border pt-3">
        <span>{competitor.recentArticleCount} recent articles</span>
        <span>Updated {new Date(competitor.lastUpdated).toLocaleDateString()}</span>
      </div>
    </motion.div>
  );
}

// ─── Event Timeline ───────────────────────────────────────────

const EVENT_COLORS: Record<string, string> = {
  product_launch:   'bg-brand-500',
  funding:          'bg-signal-opportunity',
  partnership:      'bg-accent-500',
  executive_change: 'bg-yellow-500',
  marketing:        'bg-purple-500',
  regulatory:       'bg-signal-risk',
};

const SIGNIFICANCE_ICONS = {
  high:   '⚡',
  medium: '•',
  low:    '·',
};

function EventTimeline({ events }: { events: CompetitorEvent[] }) {
  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div key={event.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className={cn('h-2 w-2 rounded-full mt-1.5 shrink-0', EVENT_COLORS[event.eventType] ?? 'bg-muted')} />
            <div className="flex-1 w-px bg-surface-border mt-1" />
          </div>
          <div className="pb-3 flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase">
                    {event.competitorId}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {SIGNIFICANCE_ICONS[event.significance]} {event.eventType.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="text-sm font-medium text-foreground mt-0.5">{event.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{event.description}</p>
              </div>
              <span className="text-[10px] text-muted-foreground shrink-0">
                {new Date(event.date).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Messaging Gap Card ───────────────────────────────────────

function MessagingGapSection({ competitors }: { competitors: Competitor[] }) {
  const gaps = competitors.flatMap((c) =>
    c.messagingGaps.map((g) => ({ ...g, competitorName: c.name }))
  ).sort((a, b) => (a.priority === 'high' ? -1 : 1));

  return (
    <div className="rounded-lg border border-surface-border bg-surface-elevated p-5">
      <h2 className="font-semibold text-foreground flex items-center gap-2 mb-4">
        <AlertCircle className="h-4 w-4 text-accent-400" />
        Messaging Gap Analysis
      </h2>
      {gaps.length === 0 ? (
        <p className="text-xs text-muted-foreground">No gaps analyzed yet.</p>
      ) : (
        <div className="space-y-4">
          {gaps.slice(0, 6).map((gap, i) => (
            <div key={i} className="rounded-md border border-surface-border p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-semibold text-muted-foreground">{gap.competitorName}</span>
                <span className={cn(
                  'rounded px-1.5 py-0.5 text-[10px] font-semibold',
                  gap.priority === 'high' ? 'bg-signal-risk/20 text-signal-risk' :
                  gap.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-surface-muted text-muted-foreground'
                )}>
                  {gap.priority}
                </span>
                <span className="text-xs font-medium text-foreground ml-auto">{gap.topic}</span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="text-[10px] text-muted-foreground mb-0.5">Their Position</p>
                  <p className="text-foreground">{gap.competitorPosition}</p>
                </div>
                <div>
                  <p className="text-[10px] text-accent-400 mb-0.5">TADA Opportunity</p>
                  <p className="text-foreground">{gap.tadaOpportunity}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function CompetitorsPage() {
  const { data: competitors, isLoading }  = useCompetitors();
  const { data: events }                  = useCompetitorEvents({ limit: 20 });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <Users className="h-6 w-6 text-accent-400" />
          Competitive Intelligence
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor competitor activity, messaging gaps, and market positioning
        </p>
      </div>

      {/* Competitor Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...Array(4)].map((_, i) => <div key={i} className="h-64 skeleton rounded-lg" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(competitors ?? []).map((c) => <CompetitorCard key={c.id} competitor={c} />)}
        </div>
      )}

      {/* Timeline + Gap Analysis */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-surface-border bg-surface-elevated p-5">
          <h2 className="font-semibold text-foreground mb-4">Recent Events Timeline</h2>
          <div className="max-h-96 overflow-y-auto scrollbar-thin">
            <EventTimeline events={events ?? []} />
          </div>
        </div>
        <MessagingGapSection competitors={competitors ?? []} />
      </div>
    </div>
  );
}
