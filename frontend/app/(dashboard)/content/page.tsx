'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Calendar, Check, Clock, Edit3, X } from 'lucide-react';
import { useContentIdeas, updateContentStatus } from '@/lib/api';
import type { ContentIdea, ContentType, ContentStatus } from '@/lib/types';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { format, startOfWeek, addDays } from 'date-fns';
import { mutate } from 'swr';

// ─── Config ──────────────────────────────────────────────────

const CONTENT_TYPES: { value: ContentType | 'all'; label: string }[] = [
  { value: 'all',               label: 'All Types'        },
  { value: 'linkedin_post',     label: 'LinkedIn'         },
  { value: 'article',           label: 'Article'          },
  { value: 'newsletter',        label: 'Newsletter'       },
  { value: 'executive_briefing',label: 'Briefing'         },
  { value: 'video_script',      label: 'Video Script'     },
  { value: 'podcast_outline',   label: 'Podcast'          },
  { value: 'webinar_outline',   label: 'Webinar'          },
  { value: 'case_study',        label: 'Case Study'       },
];

const STATUS_CONFIG: Record<ContentStatus, { label: string; color: string; icon: React.ElementType }> = {
  draft:     { label: 'Draft',     color: 'text-muted-foreground',    icon: Edit3  },
  approved:  { label: 'Approved',  color: 'text-signal-opportunity',  icon: Check  },
  scheduled: { label: 'Scheduled', color: 'text-signal-trend',        icon: Clock  },
  published: { label: 'Published', color: 'text-brand-400',           icon: FileText },
  rejected:  { label: 'Rejected',  color: 'text-signal-risk',         icon: X      },
};

// ─── Content Card ─────────────────────────────────────────────

function ContentCard({ idea }: { idea: ContentIdea }) {
  const statusConf = STATUS_CONFIG[idea.status];
  const Icon = statusConf.icon;

  const handleStatusChange = async (newStatus: ContentStatus) => {
    try {
      await updateContentStatus(idea.id, newStatus);
      await mutate((key: string) => key.includes('/content'));
      toast.success(`Status updated to ${newStatus}`);
    } catch {
      toast.error('Failed to update status');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-surface-border bg-surface-elevated p-4 hover:border-brand-500/40 transition-all"
    >
      {/* Type + status */}
      <div className="flex items-center justify-between mb-2">
        <span className="rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase text-muted-foreground">
          {idea.type.replace(/_/g, ' ')}
        </span>
        <span className={cn('flex items-center gap-1 text-[10px] font-semibold', statusConf.color)}>
          <Icon className="h-3 w-3" />
          {statusConf.label}
        </span>
      </div>

      {/* Title */}
      <h3 className="font-medium text-foreground text-sm leading-snug mb-2">{idea.title}</h3>
      <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{idea.summary}</p>

      {/* Target audience */}
      <p className="text-[10px] text-muted-foreground mb-3">
        <span className="text-accent-400">Audience:</span> {idea.targetAudience}
      </p>

      {/* Tags */}
      <div className="flex flex-wrap gap-1 mb-3">
        {idea.tags.slice(0, 3).map((t) => (
          <span key={t} className="rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
            {t}
          </span>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 border-t border-surface-border pt-3">
        {idea.status === 'draft' && (
          <>
            <button onClick={() => handleStatusChange('approved')}
              className="flex-1 rounded bg-signal-opportunity/20 text-signal-opportunity text-[10px] font-semibold py-1.5 hover:bg-signal-opportunity/30 transition-colors">
              Approve
            </button>
            <button onClick={() => handleStatusChange('rejected')}
              className="flex-1 rounded bg-signal-risk/20 text-signal-risk text-[10px] font-semibold py-1.5 hover:bg-signal-risk/30 transition-colors">
              Reject
            </button>
          </>
        )}
        {idea.status === 'approved' && (
          <button onClick={() => handleStatusChange('scheduled')}
            className="flex-1 rounded bg-signal-trend/20 text-signal-trend text-[10px] font-semibold py-1.5 hover:bg-signal-trend/30 transition-colors">
            Schedule
          </button>
        )}
        {idea.scheduledFor && (
          <span className="text-[10px] text-muted-foreground ml-auto">
            📅 {new Date(idea.scheduledFor).toLocaleDateString()}
          </span>
        )}
      </div>
    </motion.div>
  );
}

// ─── Weekly Content Calendar ──────────────────────────────────

function ContentCalendar({ ideas }: { ideas: ContentIdea[] }) {
  const today = new Date();
  const weekStart = startOfWeek(today, { weekStartsOn: 1 });
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const byDay = (day: Date) =>
    ideas.filter((idea) => {
      if (!idea.scheduledFor) return false;
      const d = new Date(idea.scheduledFor);
      return (
        d.getFullYear() === day.getFullYear() &&
        d.getMonth()    === day.getMonth()    &&
        d.getDate()     === day.getDate()
      );
    });

  return (
    <div className="rounded-lg border border-surface-border bg-surface-elevated overflow-hidden">
      <div className="grid grid-cols-7 border-b border-surface-border">
        {days.map((day) => (
          <div
            key={day.toISOString()}
            className={cn(
              'p-2 text-center border-r border-surface-border last:border-r-0',
              format(day, 'yyyy-MM-dd') === format(today, 'yyyy-MM-dd') && 'bg-brand-500/10'
            )}
          >
            <p className="text-[10px] font-semibold uppercase text-muted-foreground">{format(day, 'EEE')}</p>
            <p className={cn(
              'text-sm font-bold',
              format(day, 'yyyy-MM-dd') === format(today, 'yyyy-MM-dd') ? 'text-brand-400' : 'text-foreground'
            )}>
              {format(day, 'd')}
            </p>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 min-h-[120px]">
        {days.map((day) => {
          const dayIdeas = byDay(day);
          return (
            <div
              key={day.toISOString()}
              className={cn(
                'p-2 border-r border-surface-border last:border-r-0 space-y-1 min-h-[120px]',
                format(day, 'yyyy-MM-dd') === format(today, 'yyyy-MM-dd') && 'bg-brand-500/5'
              )}
            >
              {dayIdeas.map((idea) => (
                <div
                  key={idea.id}
                  className="rounded p-1 text-[9px] font-medium leading-tight bg-brand-500/20 text-brand-300 line-clamp-2 cursor-default"
                  title={idea.title}
                >
                  {idea.title}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function ContentPage() {
  const [typeFilter, setTypeFilter]     = useState<ContentType | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<ContentStatus | 'all'>('all');
  const [view, setView]                 = useState<'grid' | 'calendar'>('grid');

  const { data, isLoading } = useContentIdeas({
    type:   typeFilter === 'all'   ? undefined : typeFilter,
    status: statusFilter === 'all' ? undefined : statusFilter,
    pageSize: 30,
  });

  const ideas = data?.data ?? [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <FileText className="h-6 w-6 text-yellow-400" />
            Content Strategy
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI-generated content ideas ready for your GTM team
            {data?.total !== undefined && ` · ${data.total} ideas`}
          </p>
        </div>
        {/* View toggle */}
        <div className="flex rounded-md border border-surface-border bg-surface-elevated p-0.5 gap-0.5">
          <button onClick={() => setView('grid')}
            className={cn('rounded px-3 py-1.5 text-xs font-medium transition-all',
              view === 'grid' ? 'bg-brand-500 text-white' : 'text-muted-foreground hover:text-foreground')}>
            Grid
          </button>
          <button onClick={() => setView('calendar')}
            className={cn('rounded px-3 py-1.5 text-xs font-medium flex items-center gap-1 transition-all',
              view === 'calendar' ? 'bg-brand-500 text-white' : 'text-muted-foreground hover:text-foreground')}>
            <Calendar className="h-3 w-3" />
            Calendar
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        {/* Type filter */}
        <div className="flex rounded-lg border border-surface-border bg-surface-elevated p-1 gap-0.5 flex-wrap">
          {CONTENT_TYPES.map((t) => (
            <button key={t.value} onClick={() => setTypeFilter(t.value)}
              className={cn('rounded px-2.5 py-1 text-xs font-medium transition-all',
                typeFilter === t.value ? 'bg-brand-500 text-white' : 'text-muted-foreground hover:text-foreground hover:bg-surface-muted')}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Status filter */}
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as ContentStatus | 'all')}
          className="rounded-md border border-surface-border bg-surface-elevated px-3 py-1.5 text-xs text-foreground outline-none">
          <option value="all">All Status</option>
          {Object.entries(STATUS_CONFIG).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
      </div>

      {/* Calendar View */}
      {view === 'calendar' && (
        <div>
          <h2 className="font-semibold text-foreground mb-3 flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            This Week's Content Calendar
          </h2>
          <ContentCalendar ideas={ideas} />
        </div>
      )}

      {/* Grid View */}
      {view === 'grid' && (
        <>
          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[...Array(9)].map((_, i) => <div key={i} className="h-56 skeleton rounded-lg" />)}
            </div>
          ) : ideas.length === 0 ? (
            <div className="flex h-64 items-center justify-center rounded-lg border border-surface-border">
              <p className="text-muted-foreground text-sm">No content ideas found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {ideas.map((idea) => <ContentCard key={idea.id} idea={idea} />)}
            </div>
          )}
        </>
      )}
    </div>
  );
}
