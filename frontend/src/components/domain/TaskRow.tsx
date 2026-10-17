/** One task, with the dependency and deadline context a manager reads first. */

import { Link } from 'react-router-dom'

import { PriorityBadge, TaskStatusBadge } from '@/components/domain/labels'
import { Badge } from '@/components/ui/primitives'
import { formatDayCount, pluralise } from '@/lib/format'
import type { TaskView } from '@/types/api'

export function TaskRow({
  view,
  onOpen,
  showProject = false,
}: {
  view: TaskView
  onOpen?: (taskId: string) => void
  showProject?: boolean
}) {
  const { task } = view
  const content = (
    <>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-navy-900">{task.title}</span>
          <TaskStatusBadge status={task.status} />
          <PriorityBadge priority={task.priority} />
          {view.is_overdue ? <Badge tone="risk">Overdue</Badge> : null}
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {showProject ? `${view.project_name} · ` : ''}
          {view.owner_name}
          {task.due_date ? ` · ${formatDayCount(view.days_until_due)}` : ' · No due date'}
        </p>
        {task.blocked_reason ? (
          <p className="mt-1 text-xs text-risk-600">Blocker: {task.blocked_reason}</p>
        ) : null}
        {view.blocking_dependencies.length > 0 ? (
          <p className="mt-1 text-xs text-warn-700">
            Waiting on: {view.blocking_dependencies.join(', ')}
          </p>
        ) : null}
        {view.downstream_task_ids.length > 0 ? (
          <p className="mt-1 text-xs text-slate-500">
            {pluralise(view.downstream_task_ids.length, 'task')} depend on this
          </p>
        ) : null}
        {task.next_step ? (
          <p className="mt-1 text-xs text-slate-600">Next step: {task.next_step}</p>
        ) : null}
      </div>
    </>
  )

  if (onOpen) {
    return (
      <li>
        <button
          onClick={() => onOpen(task.id)}
          className="flex w-full items-start gap-3 px-5 py-3 text-left transition-colors hover:bg-slate-50"
        >
          {content}
        </button>
      </li>
    )
  }
  return (
    <li>
      <Link
        to={`/projects/${task.project_id}?task=${task.id}`}
        className="flex items-start gap-3 px-5 py-3 transition-colors hover:bg-slate-50"
      >
        {content}
      </Link>
    </li>
  )
}
