'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { ClipboardCheck, Check, X, MessageSquare, User } from 'lucide-react';
import { useReviewQueue, submitReview, assignReviewer } from '@/lib/api';
import type { ReviewItem, ReviewStatus } from '@/lib/types';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { mutate } from 'swr';

// ─── Config ──────────────────────────────────────────────────

const ITEM_TYPES = [
  { value: 'all' as const,         label: 'All'            },
  { value: 'insight' as const,     label: 'Insights'       },
  { value: 'recommendation' as const, label: 'Recommendations' },
  { value: 'content_idea' as const, label: 'Content Ideas' },
  { value: 'briefing' as const,    label: 'Briefings'      },
];

const STATUS_COLORS: Record<ReviewStatus, string> = {
  pending:          'text-yellow-400',
  approved:         'text-signal-opportunity',
  rejected:         'text-signal-risk',
  changes_requested:'text-signal-threat',
};

const PRIORITY_COLORS = {
  critical: 'bg-signal-risk/20 text-signal-risk',
  high:     'bg-signal-threat/20 text-signal-threat',
  medium:   'bg-yellow-500/20 text-yellow-400',
  low:      'bg-surface-muted text-muted-foreground',
};

// ─── Review Card ──────────────────────────────────────────────

function ReviewCard({ item }: { item: ReviewItem }) {
  const [feedbackText, setFeedbackText] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [isPending, setIsPending]       = useState(false);

  const handleAction = async (action: 'approve' | 'reject' | 'request_changes') => {
    setIsPending(true);
    try {
      await submitReview(item.id, action, feedbackText || undefined);
      await mutate((key: string) => key.includes('/review'));
      toast.success(
        action === 'approve' ? 'Approved!' :
        action === 'reject'  ? 'Rejected.' :
        'Changes requested.'
      );
      setShowFeedback(false);
    } catch {
      toast.error('Action failed. Please try again.');
    } finally {
      setIsPending(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-surface-border bg-surface-elevated p-5 space-y-4"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="rounded border border-surface-border bg-surface-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase text-muted-foreground">
            {item.itemType.replace('_', ' ')}
          </span>
          <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-semibold', PRIORITY_COLORS[item.priority])}>
            {item.priority}
          </span>
        </div>
        <span className={cn('text-[10px] font-semibold capitalize', STATUS_COLORS[item.status])}>
          {item.status.replace('_', ' ')}
        </span>
      </div>

      {/* Title + summary */}
      <div>
        <h3 className="font-semibold text-foreground">{item.title}</h3>
        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{item.summary}</p>
      </div>

      {/* Assignment */}
      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1">
          <User className="h-3 w-3" />
          {item.assignedTo ? `Assigned to ${item.assignedTo}` : 'Unassigned'}
        </div>
        <span>Created {new Date(item.createdAt).toLocaleDateString()}</span>
      </div>

      {/* Feedback (if changes requested) */}
      {item.feedback && (
        <div className="rounded-md border border-yellow-500/30 bg-yellow-500/5 p-3">
          <p className="text-[10px] font-semibold text-yellow-400 mb-1">Feedback</p>
          <p className="text-xs text-foreground">{item.feedback}</p>
        </div>
      )}

      {/* Actions — only for pending items */}
      {item.status === 'pending' && (
        <div className="border-t border-surface-border pt-3 space-y-2">
          <div className="flex gap-2">
            <button
              disabled={isPending}
              onClick={() => handleAction('approve')}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-signal-opportunity/20 text-signal-opportunity text-xs font-semibold py-2 hover:bg-signal-opportunity/30 transition-colors disabled:opacity-40"
            >
              <Check className="h-3 w-3" />
              Approve
            </button>
            <button
              disabled={isPending}
              onClick={() => setShowFeedback(!showFeedback)}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-yellow-500/20 text-yellow-400 text-xs font-semibold py-2 hover:bg-yellow-500/30 transition-colors disabled:opacity-40"
            >
              <MessageSquare className="h-3 w-3" />
              Request Changes
            </button>
            <button
              disabled={isPending}
              onClick={() => handleAction('reject')}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-signal-risk/20 text-signal-risk text-xs font-semibold py-2 hover:bg-signal-risk/30 transition-colors disabled:opacity-40"
            >
              <X className="h-3 w-3" />
              Reject
            </button>
          </div>

          {showFeedback && (
            <div className="space-y-2">
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="Describe the changes needed…"
                rows={3}
                className="w-full rounded-md border border-surface-border bg-surface-muted px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground outline-none resize-none focus:border-brand-500/50"
              />
              <button
                disabled={isPending || !feedbackText.trim()}
                onClick={() => handleAction('request_changes')}
                className="w-full rounded-md bg-yellow-500/20 text-yellow-400 text-xs font-semibold py-2 hover:bg-yellow-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Submit Feedback
              </button>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

// ─── Page ────────────────────────────────────────────────────

export default function ReviewPage() {
  const [typeFilter, setTypeFilter]     = useState<ReviewItem['itemType'] | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | 'all'>('pending');
  const [page, setPage]                 = useState(1);

  const { data, isLoading } = useReviewQueue({
    itemType: typeFilter === 'all' ? undefined : typeFilter,
    status:   statusFilter === 'all' ? undefined : statusFilter,
    page,
    pageSize: 12,
  });

  const items = data?.data ?? [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <ClipboardCheck className="h-6 w-6 text-accent-400" />
            Human Review Queue
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Review AI-generated insights, recommendations, and content
            {data?.total !== undefined && ` · ${data.total} items`}
          </p>
        </div>
      </div>

      {/* Tabs by item type */}
      <div className="flex flex-wrap gap-1 border-b border-surface-border pb-3">
        {ITEM_TYPES.map((t) => (
          <button
            key={t.value}
            onClick={() => { setTypeFilter(t.value); setPage(1); }}
            className={cn(
              'rounded-md px-3 py-1.5 text-xs font-medium transition-all',
              typeFilter === t.value
                ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30'
                : 'text-muted-foreground hover:text-foreground hover:bg-surface-elevated'
            )}
          >
            {t.label}
          </button>
        ))}

        <div className="ml-auto">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value as ReviewStatus | 'all'); setPage(1); }}
            className="rounded-md border border-surface-border bg-surface-elevated px-3 py-1.5 text-xs text-foreground outline-none"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="changes_requested">Changes Requested</option>
          </select>
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...Array(6)].map((_, i) => <div key={i} className="h-56 skeleton rounded-lg" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-lg border border-surface-border">
          <ClipboardCheck className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">No items in review queue.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => <ReviewCard key={item.id} item={item} />)}
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
