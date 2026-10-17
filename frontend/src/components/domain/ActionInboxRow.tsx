/** One action in the manager inbox, with the consequence of leaving it. */

import { Link } from 'react-router-dom'

import {
  ACTION_TYPE_ICON,
  BUCKET_LABEL,
  BUCKET_TONE,
  PriorityBadge,
} from '@/components/domain/labels'
import { Badge } from '@/components/ui/primitives'
import { formatDayCount, pluralise, relativeDays } from '@/lib/format'
import type { ActionInboxItem } from '@/types/api'

export function ActionInboxRow({
  item,
  compact = false,
  onOpen,
}: {
  item: ActionInboxItem
  compact?: boolean
  onOpen?: (item: ActionInboxItem) => void
}) {
  const { action, priority_detail: priority } = item
  // The day count comes from the server so this render stays pure.
  const dueLabel =
    priority.due_in_days === null ? null : formatDayCount(priority.due_in_days)

  const body = (
    <>
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <span className="mt-0.5 text-navy-500">{ACTION_TYPE_ICON[action.type]}</span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-navy-900">{action.title}</span>
            <PriorityBadge priority={action.priority} />
            <Badge tone={BUCKET_TONE[priority.bucket] ?? 'neutral'}>
              {BUCKET_LABEL[priority.bucket] ?? priority.bucket}
            </Badge>
          </div>
          {!compact ? (
            <p className="mt-1 text-sm text-slate-600">{action.description}</p>
          ) : null}
          <p className="mt-1 text-xs text-slate-500">
            {item.project_name ? `${item.project_name} · ` : ''}
            {item.task_title ? `${item.task_title} · ` : ''}
            Raised {relativeDays(action.created_at)}
            {item.requester_name ? ` by ${item.requester_name}` : ''}
          </p>
          {priority.consequence ? (
            <p className="mt-1 text-xs font-medium text-warn-700">
              Consequence: {priority.consequence}
            </p>
          ) : null}
          {!compact && priority.blocks_task_ids.length > 0 ? (
            <p className="mt-1 text-xs text-slate-500">
              Blocks {pluralise(priority.blocks_task_ids.length, 'task')}:{' '}
              {priority.blocks_task_ids.join(', ')}
            </p>
          ) : null}
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="text-xs font-semibold tabular-nums text-navy-700" title="Deterministic priority score">
          {priority.score.toFixed(0)}
        </span>
        {dueLabel ? (
          <span
            className={
              dueLabel.includes('overdue') ? 'text-xs text-risk-600' : 'text-xs text-slate-500'
            }
          >
            {dueLabel}
          </span>
        ) : null}
      </div>
    </>
  )

  if (onOpen) {
    return (
      <li>
        <button
          onClick={() => onOpen(item)}
          className="flex w-full items-start gap-3 px-5 py-3 text-left transition-colors hover:bg-slate-50"
        >
          {body}
        </button>
      </li>
    )
  }

  return (
    <li>
      <Link
        to="/inbox"
        className="flex items-start gap-3 px-5 py-3 transition-colors hover:bg-slate-50"
      >
        {body}
      </Link>
    </li>
  )
}
