'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Zap, TrendingUp, Shield, AlertTriangle, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Signal } from '@/lib/types';

// ─── Helpers ─────────────────────────────────────────────────

const TYPE_CONFIG = {
  risk:        { icon: AlertTriangle, color: 'text-signal-risk',        bg: 'bg-signal-risk/10',        border: 'border-signal-risk/30',        badge: 'badge-risk'        },
  opportunity: { icon: TrendingUp,    color: 'text-signal-opportunity', bg: 'bg-signal-opportunity/10', border: 'border-signal-opportunity/30', badge: 'badge-opportunity' },
  trend:       { icon: Zap,           color: 'text-signal-trend',       bg: 'bg-signal-trend/10',       border: 'border-signal-trend/30',       badge: 'badge-trend'       },
  threat:      { icon: Shield,        color: 'text-signal-threat',      bg: 'bg-signal-threat/10',      border: 'border-signal-threat/30',      badge: 'badge-threat'      },
  emerging:    { icon: Sparkles,      color: 'text-signal-emerging',    bg: 'bg-signal-emerging/10',    border: 'border-signal-emerging/30',    badge: 'badge-emerging'    },
} as const;

const URGENCY_CONFIG = {
  critical: { label: 'Critical', class: 'urgency-critical' },
  high:     { label: 'High',     class: 'urgency-high'     },
  medium:   { label: 'Medium',   class: 'urgency-medium'   },
  low:      { label: 'Low',      class: 'urgency-low'      },
} as const;

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="score-bar w-full">
      <motion.div
        className={cn('score-fill', color)}
        initial={{ width: 0 }}
        animate={{ width: `${value * 100}%` }}
        transition={{ duration: 0.7, ease: 'easeOut', delay: 0.1 }}
      />
    </div>
  );
}

function ScoreRow({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>{label}</span>
        <span className="font-mono font-medium text-foreground">{Math.round(value * 100)}</span>
      </div>
      <ScoreBar value={value} color={color} />
    </div>
  );
}

// ─── Props ───────────────────────────────────────────────────

export interface SignalCardProps {
  signal: Signal;
  compact?: boolean;
  className?: string;
}

// ─── Component ───────────────────────────────────────────────

export function SignalCard({ signal, compact = false, className }: SignalCardProps) {
  const typeConfig = TYPE_CONFIG[signal.type] ?? TYPE_CONFIG.trend;
  const urgencyConfig = URGENCY_CONFIG[signal.urgency] ?? URGENCY_CONFIG.medium;
  const Icon = typeConfig.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Link href={`/signals/${signal.id}`}>
        <div
          className={cn(
            'group relative flex flex-col gap-4 rounded-lg border bg-surface-elevated p-4 transition-all duration-200',
            'hover:border-brand-500/50 hover:shadow-glow-brand hover:bg-surface-subtle',
            typeConfig.border,
            className
          )}
        >
          {/* Top row: icon + type badge + urgency */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className={cn('flex h-8 w-8 items-center justify-center rounded-md', typeConfig.bg)}>
                <Icon className={cn('h-4 w-4', typeConfig.color)} />
              </div>
              <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide', typeConfig.badge)}>
                {signal.type}
              </span>
            </div>
            <span className={cn('text-xs font-semibold', urgencyConfig.class)}>
              {urgencyConfig.label}
            </span>
          </div>

          {/* Title */}
          <div>
            <h3 className="font-semibold text-foreground leading-snug line-clamp-2 group-hover:text-brand-300 transition-colors">
              {signal.title}
            </h3>
            {!compact && (
              <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                {signal.summary}
              </p>
            )}
          </div>

          {/* Score bars */}
          {!compact && (
            <div className="space-y-2">
              <ScoreRow label="Confidence" value={signal.confidenceScore} color="bg-brand-500" />
              <ScoreRow label="Strength"   value={signal.strengthScore}   color="bg-accent-500" />
              <ScoreRow label="Momentum"   value={signal.momentumScore}   color="bg-signal-opportunity" />
            </div>
          )}

          {/* Tags + meta */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex flex-wrap gap-1">
              {signal.tags.slice(0, compact ? 2 : 3).map((tag) => (
                <span
                  key={tag}
                  className="rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
              <span className="font-mono font-bold text-brand-400">
                {Math.round(signal.overallScore * 100)}
              </span>
              <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </div>

          {/* Source count */}
          <p className="text-[10px] text-muted-foreground">
            {signal.sourceCount} source{signal.sourceCount !== 1 ? 's' : ''} · {new Date(signal.detectedAt).toLocaleDateString()}
          </p>
        </div>
      </Link>
    </motion.div>
  );
}
