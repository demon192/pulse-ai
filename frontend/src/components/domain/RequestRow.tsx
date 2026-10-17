/** One support request in a list. */

import {
  PriorityBadge,
  REQUEST_CATEGORY_LABEL,
  REQUEST_STATUS_TONE,
} from '@/components/domain/labels'
import { Badge } from '@/components/ui/primitives'
import { relativeDays, titleCase } from '@/lib/format'
import type { SupportRequestView } from '@/types/api'

export function RequestRow({
  view,
  onOpen,
  showEngineer = false,
}: {
  view: SupportRequestView
  onOpen?: (view: SupportRequestView) => void
  showEngineer?: boolean
}) {
  const { request } = view
  const content = (
    <div className="min-w-0 flex-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-navy-900">{request.title}</span>
        <Badge tone={REQUEST_STATUS_TONE[request.status]}>{titleCase(request.status)}</Badge>
        <Badge tone="neutral">{REQUEST_CATEGORY_LABEL[request.category]}</Badge>
        <PriorityBadge priority={request.priority} />
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {showEngineer ? `${view.engineer_name} · ` : ''}
        {view.project_name}
        {view.task_title ? ` · ${view.task_title}` : ''} · raised {relativeDays(request.created_at)}
      </p>
      {request.responses.length > 0 ? (
        <p className="mt-1 line-clamp-2 text-xs text-slate-600">
          Latest response: {request.responses[request.responses.length - 1].body}
        </p>
      ) : null}
      {request.resolution_notes ? (
        <p className="mt-1 text-xs text-ok-700">Outcome: {request.resolution_notes}</p>
      ) : null}
    </div>
  )

  if (onOpen) {
    return (
      <li>
        <button
          onClick={() => onOpen(view)}
          className="flex w-full items-start gap-3 px-5 py-3 text-left transition-colors hover:bg-slate-50"
        >
          {content}
        </button>
      </li>
    )
  }
  return <li className="flex items-start gap-3 px-5 py-3">{content}</li>
}
