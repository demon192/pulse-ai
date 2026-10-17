/**
 * Task detail with the update form.
 *
 * The form is the engineer's way to record progress, a next step and a blocker
 * reason — the same fields the handover brief later reads.
 */

import { useState } from 'react'

import { PriorityBadge, TaskStatusBadge } from '@/components/domain/labels'
import {
  Badge,
  Button,
  Drawer,
  EmptyState,
  ErrorState,
  Field,
  InlineError,
  KeyValue,
  LoadingBlock,
  SectionTitle,
  inputClasses,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { formatDate, formatDateTime, formatDayCount } from '@/lib/format'
import { api } from '@/services/api'
import type { TaskStatus } from '@/types/api'

const STATUS_OPTIONS: TaskStatus[] = [
  'not_started',
  'in_progress',
  'blocked',
  'in_review',
  'completed',
]

export function TaskDrawer({
  taskId,
  onClose,
  onUpdated,
}: {
  taskId: string | null
  onClose: () => void
  onUpdated?: () => void
}) {
  const detail = useAsync(() => api.task(taskId as string), [taskId], {
    enabled: Boolean(taskId),
  })

  const [status, setStatus] = useState<TaskStatus | ''>('')
  const [nextStep, setNextStep] = useState('')
  const [blockedReason, setBlockedReason] = useState('')
  const [progressNote, setProgressNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  if (!taskId) return null

  async function save() {
    setSaving(true)
    setSaveError(null)
    setSaved(false)
    try {
      await api.updateTask(taskId as string, {
        status: status || undefined,
        next_step: nextStep || undefined,
        blocked_reason: blockedReason || undefined,
        progress_note: progressNote || undefined,
      })
      setStatus('')
      setNextStep('')
      setBlockedReason('')
      setProgressNote('')
      setSaved(true)
      await detail.reload()
      onUpdated?.()
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : 'Could not save the update.')
    } finally {
      setSaving(false)
    }
  }

  const data = detail.data
  const task = data?.task.task

  return (
    <Drawer
      open
      onClose={onClose}
      width="lg"
      title={task?.title ?? 'Task'}
      description={data ? `${data.task.project_name} · ${data.task.owner_name}` : undefined}
    >
      {detail.initialLoading ? <LoadingBlock label="Loading the task" rows={6} /> : null}
      {detail.error ? <ErrorState message={detail.error} onRetry={detail.reload} /> : null}

      {data && task ? (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <TaskStatusBadge status={task.status} />
            <PriorityBadge priority={task.priority} />
            {data.task.is_overdue ? <Badge tone="risk">Overdue</Badge> : null}
          </div>

          <p className="text-sm text-slate-700">{task.description}</p>

          <dl className="grid grid-cols-2 gap-4 rounded-lg border border-slate-200 bg-white px-4 py-3">
            <KeyValue label="Due">
              {task.due_date ? `${formatDate(task.due_date)} · ${formatDayCount(data.task.days_until_due)}` : 'No due date'}
            </KeyValue>
            <KeyValue label="Remaining effort">
              {task.remaining_effort !== null ? `${task.remaining_effort}h` : 'Not estimated'}
            </KeyValue>
            <KeyValue label="Next step">{task.next_step ?? 'Not recorded'}</KeyValue>
            <KeyValue label="Required skills">
              {task.required_skills.length > 0 ? task.required_skills.join(', ') : 'None recorded'}
            </KeyValue>
          </dl>

          {task.blocked_reason ? (
            <div className="rounded-lg border border-risk-200 bg-risk-50 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-risk-700">
                Recorded blocker
              </p>
              <p className="mt-1 text-sm text-risk-700">{task.blocked_reason}</p>
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <SectionTitle>Depends on</SectionTitle>
              {data.dependencies.length === 0 ? (
                <p className="text-sm text-slate-500">Nothing.</p>
              ) : (
                <ul className="space-y-1.5">
                  {data.dependencies.map((dependency) => (
                    <li key={dependency.id} className="flex items-center gap-2 text-sm">
                      <TaskStatusBadge status={dependency.status} />
                      <span className="truncate text-navy-900">{dependency.title}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <SectionTitle>Waiting on this</SectionTitle>
              {data.dependents.length === 0 ? (
                <p className="text-sm text-slate-500">Nothing.</p>
              ) : (
                <ul className="space-y-1.5">
                  {data.dependents.map((dependent) => (
                    <li key={dependent.id} className="flex items-center gap-2 text-sm">
                      <TaskStatusBadge status={dependent.status} />
                      <span className="truncate text-navy-900">{dependent.title}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div>
            <SectionTitle hint="Treated as untrusted input by the AI layer">
              Progress updates
            </SectionTitle>
            {data.updates.length === 0 ? (
              <EmptyState
                title="No progress updates"
                description="Without updates, a handover brief can only restate the task record."
              />
            ) : (
              <ul className="space-y-2">
                {data.updates.map((update) => (
                  <li key={update.id} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                    <p className="text-sm text-slate-700">{update.body}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {formatDateTime(update.created_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white px-4 py-4">
            <SectionTitle>Record an update</SectionTitle>
            <div className="space-y-3">
              <Field label="Status">
                <select
                  className={inputClasses}
                  value={status}
                  onChange={(event) => setStatus(event.target.value as TaskStatus | '')}
                >
                  <option value="">Leave unchanged</option>
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Next step" hint="What happens next, in one line.">
                <input
                  className={inputClasses}
                  value={nextStep}
                  onChange={(event) => setNextStep(event.target.value)}
                  placeholder={task.next_step ?? 'e.g. Rebase and run the integration suite'}
                />
              </Field>
              {(status || task.status) === 'blocked' ? (
                <Field label="Blocker reason" hint="Why the work cannot continue.">
                  <input
                    className={inputClasses}
                    value={blockedReason}
                    onChange={(event) => setBlockedReason(event.target.value)}
                    placeholder={task.blocked_reason ?? 'e.g. Waiting on the API contract decision'}
                  />
                </Field>
              ) : null}
              <Field label="Progress note" hint="Free text. Appears in the handover brief.">
                <textarea
                  className={inputClasses}
                  rows={3}
                  value={progressNote}
                  onChange={(event) => setProgressNote(event.target.value)}
                />
              </Field>
              {saveError ? <InlineError message={saveError} /> : null}
              {saved ? <p className="text-sm text-ok-700">Update saved.</p> : null}
              <Button
                variant="primary"
                onClick={save}
                loading={saving}
                disabled={!status && !nextStep && !blockedReason && !progressNote}
              >
                Save update
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </Drawer>
  )
}
