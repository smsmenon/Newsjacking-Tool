'use client';

import { motion } from 'framer-motion';
import {
  AlertTriangle,
  TrendingUp,
  Zap,
  ArrowUpRight,
  Activity,
  Target,
  FileText,
  Users,
  RefreshCw,
} from 'lucide-react';
import {
  useDashboardStats,
  useSignals,
  useCompetitorEvents,
  useLatestBriefing,
} from '@/lib/api';
import { SignalCard } from '@/components/signals/SignalCard';
import Link from 'next/link';

// ─── Quick Stats Bar ─────────────────────────────────────────

function QuickStat({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  href: string;
}) {
  return (
    <Link href={href}>
      <div className="flex items-center gap-3 rounded-lg border border-surface-border bg-surface-elevated p-4 hover:border-brand-500/40 transition-colors">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-500/10">
          <Icon className="h-4 w-4 text-brand-400" />
        </div>
        <div>
          <p className="text-lg font-bold text-foreground">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </div>
    </Link>
  );
}

// ─── Sentiment Indicator ──────────────────────────────────────

function SentimentIndicator({ score }: { score: number }) {
  const pct = ((score + 1) / 2) * 100;
  const label = score > 0.2 ? 'Positive' : score < -0.2 ? 'Negative' : 'Neutral';
  const color = score > 0.2 ? 'bg-signal-opportunity' : score < -0.2 ? 'bg-signal-risk' : 'bg-yellow-500';

  return (
    <div className="rounded-lg border border-surface-border bg-surface-elevated p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Market Sentiment</h3>
        <span className={`text-xs font-medium ${score > 0.2 ? 'text-signal-opportunity' : score < -0.2 ? 'text-signal-risk' : 'text-yellow-400'}`}>
          {label}
        </span>
      </div>
      <div className="h-3 w-full rounded-full bg-surface-muted overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-[10px] text-muted-foreground">Bearish</span>
        <span className="text-[10px] text-muted-foreground">Bullish</span>
      </div>
    </div>
  );
}

// ─── Competitor Activity Feed ─────────────────────────────────

function CompetitorFeed() {
  const { data: events, isLoading } = useCompetitorEvents({ limit: 5 });

  const typeColors: Record<string, string> = {
    product_launch:   'bg-brand-500',
    funding:          'bg-signal-opportunity',
    partnership:      'bg-accent-500',
    executive_change: 'bg-yellow-500',
    marketing:        'bg-purple-500',
    regulatory:       'bg-signal-risk',
  };

  return (
    <div className="rounded-lg border border-surface-border bg-surface-elevated p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Competitor Activity</h3>
        <Link href="/competitors" className="text-xs text-brand-400 hover:text-brand-300">
          View all →
        </Link>
      </div>
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-12 skeleton rounded-md" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {(events ?? []).map((event) => (
            <div key={event.id} className="flex gap-3">
              <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${typeColors[event.eventType] ?? 'bg-muted'}`} />
              <div>
                <p className="text-xs font-medium text-foreground line-clamp-1">{event.title}</p>
                <p className="text-[10px] text-muted-foreground">
                  {event.competitorId} · {new Date(event.date).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Recommended Actions ──────────────────────────────────────

function RecommendedActions() {
  const { data } = useLatestBriefing();
  const recs = data?.strategicRecommendations?.slice(0, 4) ?? [];

  return (
    <div className="rounded-lg border border-surface-border bg-surface-elevated p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Recommended Actions</h3>
        <Link href="/executive" className="text-xs text-brand-400 hover:text-brand-300">
          Full briefing →
        </Link>
      </div>
      {recs.length === 0 ? (
        <p className="text-xs text-muted-foreground">No recommendations yet.</p>
      ) : (
        <ul className="space-y-3">
          {recs.map((rec, i) => (
            <li key={i} className="flex gap-3">
              <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-500/20 text-[10px] font-bold text-brand-400">
                {i + 1}
              </div>
              <div>
                <p className="text-xs font-medium text-foreground">{rec.action}</p>
                <p className="text-[10px] text-muted-foreground">{rec.team} · {rec.priority}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function ExecutivePortalPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: risksData }   = useSignals({ type: 'risk',        sortBy: 'score', pageSize: 3 });
  const { data: oppsData }    = useSignals({ type: 'opportunity', sortBy: 'score', pageSize: 3 });
  const { data: trendsData }  = useSignals({ type: 'trend',       sortBy: 'score', pageSize: 3 });

  const risks  = risksData?.data  ?? [];
  const opps   = oppsData?.data   ?? [];
  const trends = trendsData?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Executive Portal</h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI-curated market intelligence · {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <button className="flex items-center gap-2 rounded-md border border-surface-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-brand-500/40 transition-colors">
          <RefreshCw className="h-3 w-3" />
          Refresh
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <QuickStat icon={FileText}    label="Articles Today"     value={stats?.articlesCollectedToday ?? '—'} href="/repository"  />
        <QuickStat icon={Zap}         label="Signals This Week"  value={stats?.signalsDetectedThisWeek ?? '—'} href="/signals"     />
        <QuickStat icon={TrendingUp}  label="Trends Tracked"     value={stats?.trendsTracked ?? '—'}         href="/trends"      />
        <QuickStat icon={FileText}    label="Content Ideas"      value={stats?.contentIdeasPending ?? '—'}   href="/content"     />
        <QuickStat icon={Target}      label="Reviews Pending"    value={stats?.reviewItemsPending ?? '—'}    href="/review"      />
        <QuickStat icon={Activity}    label="Sources Active"     value={stats?.sourcesActive ?? '—'}        href="/intelligence" />
      </div>

      {/* Sentiment + Competitor + Actions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <SentimentIndicator score={stats?.marketSentiment ?? 0} />
        <CompetitorFeed />
        <RecommendedActions />
      </div>

      {/* Signal Strips: Risks / Opportunities / Trends */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Top Risks */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-signal-risk" />
              <h2 className="text-sm font-semibold text-foreground">Top Risks</h2>
            </div>
            <Link href="/signals?type=risk" className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300">
              All <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {risks.map((s) => <SignalCard key={s.id} signal={s} compact />)}
          </div>
        </section>

        {/* Top Opportunities */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-signal-opportunity" />
              <h2 className="text-sm font-semibold text-foreground">Top Opportunities</h2>
            </div>
            <Link href="/signals?type=opportunity" className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300">
              All <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {opps.map((s) => <SignalCard key={s.id} signal={s} compact />)}
          </div>
        </section>

        {/* Key Trends */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-signal-trend" />
              <h2 className="text-sm font-semibold text-foreground">Key Trends</h2>
            </div>
            <Link href="/trends" className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300">
              All <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {trends.map((s) => <SignalCard key={s.id} signal={s} compact />)}
          </div>
        </section>
      </div>
    </div>
  );
}
