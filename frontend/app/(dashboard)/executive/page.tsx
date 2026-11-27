'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, Download, Clock, TrendingUp, AlertTriangle, Zap, FileDown } from 'lucide-react';
import { useExecutiveBriefings, useLatestBriefing, generateBriefingPDF } from '@/lib/api';
import type { ExecutiveBriefing } from '@/lib/types';
import { SignalCard } from '@/components/signals/SignalCard';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// ─── Briefing Summary Card ────────────────────────────────────

function BriefingHistoryItem({
  briefing,
  isSelected,
  onSelect,
}: {
  briefing: ExecutiveBriefing;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left rounded-lg border p-3 transition-all',
        isSelected
          ? 'border-brand-500/50 bg-brand-500/10'
          : 'border-surface-border bg-surface-elevated hover:border-brand-500/30'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-foreground line-clamp-1">{briefing.title}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">{briefing.period}</p>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground shrink-0">
          <Clock className="h-3 w-3" />
          {new Date(briefing.generatedAt).toLocaleDateString()}
        </div>
      </div>
      <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
        <span>{briefing.articlesCollected} articles</span>
        <span>{briefing.signalsDetected} signals</span>
      </div>
    </button>
  );
}

// ─── Briefing Detail ──────────────────────────────────────────

function BriefingDetail({ briefing }: { briefing: ExecutiveBriefing }) {
  const [isExporting, setIsExporting] = useState(false);

  const handleExportPDF = async () => {
    setIsExporting(true);
    try {
      const result = await generateBriefingPDF(briefing.id);
      window.open(result.url, '_blank');
      toast.success('PDF generated successfully!');
    } catch {
      toast.error('Failed to generate PDF.');
    } finally {
      setIsExporting(false);
    }
  };

  const sentimentLabel =
    briefing.marketSentiment > 0.2 ? 'Positive' :
    briefing.marketSentiment < -0.2 ? 'Negative' : 'Neutral';
  const sentimentColor =
    briefing.marketSentiment > 0.2 ? 'text-signal-opportunity' :
    briefing.marketSentiment < -0.2 ? 'text-signal-risk' : 'text-yellow-400';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold text-foreground">{briefing.title}</h2>
          <p className="text-sm text-muted-foreground mt-1">{briefing.period}</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
            <span>{briefing.articlesCollected.toLocaleString()} articles collected</span>
            <span>{briefing.signalsDetected} signals detected</span>
            <span className={sentimentColor}>Market: {sentimentLabel}</span>
          </div>
        </div>
        <button
          onClick={handleExportPDF}
          disabled={isExporting}
          className="flex items-center gap-2 rounded-md bg-brand-500 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <FileDown className="h-3 w-3" />
          {isExporting ? 'Generating…' : 'Export PDF'}
        </button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Risks',         value: briefing.topRisks.length,           icon: AlertTriangle, color: 'text-signal-risk' },
          { label: 'Opportunities', value: briefing.topOpportunities.length,   icon: TrendingUp,    color: 'text-signal-opportunity' },
          { label: 'Trends',        value: briefing.keyTrends.length,          icon: Zap,           color: 'text-signal-trend' },
          { label: 'Recommendations', value: briefing.strategicRecommendations.length, icon: BookOpen, color: 'text-brand-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded-lg border border-surface-border bg-surface-elevated p-4 text-center">
            <Icon className={cn('h-5 w-5 mx-auto mb-2', color)} />
            <p className="text-2xl font-bold font-mono text-foreground">{value}</p>
            <p className="text-[10px] text-muted-foreground">{label}</p>
          </div>
        ))}
      </div>

      {/* Strategic Recommendations */}
      {briefing.strategicRecommendations.length > 0 && (
        <div className="rounded-lg border border-brand-500/30 bg-brand-500/5 p-5">
          <h3 className="font-semibold text-brand-300 mb-4">Strategic Recommendations</h3>
          <div className="space-y-3">
            {briefing.strategicRecommendations.map((rec, i) => (
              <div key={i} className="flex gap-3">
                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-500/30 text-[10px] font-bold text-brand-400">
                  {i + 1}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase">{rec.team}</span>
                    <span className="text-[10px] font-semibold uppercase text-brand-400">{rec.priority.replace('_', ' ')}</span>
                  </div>
                  <p className="text-sm font-medium text-foreground">{rec.action}</p>
                  <p className="text-xs text-muted-foreground">{rec.rationale}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Risks + Opportunities */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {briefing.topRisks.length > 0 && (
          <div>
            <h3 className="font-semibold text-foreground flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-signal-risk" />
              Top Risks
            </h3>
            <div className="space-y-3">
              {briefing.topRisks.slice(0, 3).map((s) => (
                <SignalCard key={s.id} signal={s} compact />
              ))}
            </div>
          </div>
        )}
        {briefing.topOpportunities.length > 0 && (
          <div>
            <h3 className="font-semibold text-foreground flex items-center gap-2 mb-3">
              <TrendingUp className="h-4 w-4 text-signal-opportunity" />
              Top Opportunities
            </h3>
            <div className="space-y-3">
              {briefing.topOpportunities.slice(0, 3).map((s) => (
                <SignalCard key={s.id} signal={s} compact />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function ExecutivePage() {
  const { data: latest }    = useLatestBriefing();
  const { data: briefings } = useExecutiveBriefings();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedBriefing = selectedId
    ? briefings?.find((b) => b.id === selectedId)
    : latest;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <BookOpen className="h-6 w-6 text-brand-400" />
          Executive Briefings
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          AI-curated intelligence briefings for executive decision-making
        </p>
      </div>

      {/* Layout */}
      <div className="flex gap-6">
        {/* Briefing history sidebar */}
        <aside className="w-64 shrink-0 space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">
            History
          </p>
          {(briefings ?? (latest ? [latest] : [])).map((b) => (
            <BriefingHistoryItem
              key={b.id}
              briefing={b}
              isSelected={selectedBriefing?.id === b.id}
              onSelect={() => setSelectedId(b.id)}
            />
          ))}
        </aside>

        {/* Briefing detail */}
        <div className="flex-1 min-w-0">
          {selectedBriefing ? (
            <motion.div key={selectedBriefing.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <BriefingDetail briefing={selectedBriefing} />
            </motion.div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-lg border border-surface-border">
              <p className="text-muted-foreground text-sm">No briefing selected.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
