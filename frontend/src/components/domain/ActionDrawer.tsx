/**
 * Act on one inbox item: acknowledge, respond, delegate, record a decision or
 * resolve it. The score breakdown is shown so the ranking is never a black box.
 */

import { useState } from 'react'

import { ACTION_STATUS_TONE, PriorityBadge } from '@/components/domain/labels'
import {
  Badge,
  Button,
  Drawer,
  Field,
  InlineError,
  KeyValue,
  SectionTitle,
  inputClasses,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { formatDateTime, relativeDays, titleCase } from '@/lib/format'
import { api } from '@/services/api'
import type { ActionInboxItem } from '@/types/api'

export function ActionDrawer({
  item,
  onClose,
  onChanged,
}: {
  item: ActionInboxItem | null
  onClose: () => void
  onChanged: () => void
}) {
  const [current, setCurrent] = useState<ActionInboxItem | null>(null)
  const [response, setResponse] = useState('')
  const [resolution, setResolution] = useState('')
  const [decision, setDecision] = useState('')
  const [rationale, setRationale] = useState('')
  const [delegateTo, setDelegateTo] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Scoped to the action's project so only people who can actually be given
  // this work are offered.
  const team = useAsync(() => api.team(item?.action.project_id ?? undefined), [item?.action.project_id], {
    enabled: Boolean(item),
  })

  if (!item) return null
  const active = current?.action.id === item.action.id ? current : item
  const { action, priority_detail: priority } = active
  const isOpen = !['resolved', 'cancelled'].includes(action.status)

  function close() {
    setCurrent(null)
    setResponse('')
    setResolution('')
    setDecision('')
    setRationale('')
    setDelegateTo('')
    setError(null)
    onClose()
  }

  async function run(key: string, work: () => Promise<ActionInboxItem | void>) {
    setBusy(key)
    setError(null)
    try {
      const result = await work()
      if (result) setCurrent(result)
      onChanged()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The change could not be saved.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <Drawer
      open
      width="lg"
      onClose={close}
      title={action.title}
      description={[active.project_name, active.task_title].filter(Boolean).join(' · ')}
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={ACTION_STATUS_TONE[action.status]}>{titleCase(action.status)}</Badge>
          <PriorityBadge priority={action.priority} />
          <Badge tone="neutral">{titleCase(action.type)}</Badge>
          <Badge tone="navy" title="Deterministic priority score">
            Score {priority.score.toFixed(0)}
          </Badge>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-sm whitespace-pre-line text-slate-700">{action.description}</p>
          <p className="mt-2 text-xs text-slate-400">
            Raised {relativeDays(action.created_at)}
            {active.requester_name ? ` by ${active.requester_name}` : ''} ·{' '}
            {formatDateTime(action.created_at)}
          </p>
        </div>

        {priority.consequence ? (
          <div className="rounded-lg border border-warn-200 bg-warn-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-warn-700">
              Downstream consequence
            </p>
            <p className="mt-1 text-sm text-warn-700">{priority.consequence}</p>
          </div>
        ) : null}

        <div>
          <SectionTitle hint="Deterministic. Gemini does not change these numbers.">
            Why this is ranked here
          </SectionTitle>
          <table className="w-full text-left text-xs">
            <thead className="text-slate-500">
              <tr>
                <th className="py-1 font-medium">Factor</th>
                <th className="py-1 font-medium">Points</th>
                <th className="py-1 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody className="align-top text-slate-700">
              {priority.factors.map((factor) => (
                <tr key={factor.factor} className="border-t border-slate-100">
                  <td className="py-1.5 pr-2 font-medium text-navy-900">
                    {titleCase(factor.factor)}
                  </td>
                  <td className="py-1.5 pr-2 tabular-nums">{factor.points.toFixed(1)}</td>
                  <td className="py-1.5">{factor.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {active.source_request ? (
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <SectionTitle>Engineer’s request</SectionTitle>
            <p className="text-sm font-medium text-navy-900">{active.source_request.title}</p>
            <p className="mt-1 text-sm whitespace-pre-line text-slate-700">
              {active.source_request.description}
            </p>
            {active.source_request.engineer_context_note ? (
              <p className="mt-2 rounded bg-info-50 px-2 py-1.5 text-xs text-info-700">
                Added context: {active.source_request.engineer_context_note}
              </p>
            ) : null}
          </div>
        ) : null}

        <dl className="grid grid-cols-2 gap-4 rounded-lg border border-slate-200 bg-white px-4 py-3">
          <KeyValue label="Owner">{active.owner_name}</KeyValue>
          <KeyValue label="Due">
            {action.due_date ? relativeDays(action.due_date) : 'No due date'}
          </KeyValue>
        </dl>

        {action.resolution_notes ? (
          <div className="rounded-lg border border-ok-200 bg-ok-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-ok-700">Outcome</p>
            <p className="mt-1 text-sm text-ok-700">{action.resolution_notes}</p>
          </div>
        ) : null}

        {error ? <InlineError message={error} /> : null}

        {isOpen ? (
          <div className="space-y-4 rounded-lg border border-slate-200 bg-white px-4 py-4">
            {active.source_request ? (
              <>
                <SectionTitle>Respond to the engineer</SectionTitle>
                <Field label="Response">
                  <textarea
                    className={inputClasses}
                    rows={3}
                    value={response}
                    onChange={(event) => setResponse(event.target.value)}
                  />
                </Field>
                <Button
                  loading={busy === 'respond'}
                  disabled={response.trim().length === 0}
                  onClick={() =>
                    run('respond', async () => {
                      await api.respondToRequest(active.source_request!.id, { body: response })
                      setResponse('')
                      return api.actions().then(
                        (items) => items.find((entry) => entry.action.id === action.id) ?? undefined,
                      )
                    })
                  }
                >
                  Send response
                </Button>
              </>
            ) : null}

            <div className="border-t border-slate-200 pt-4">
              <SectionTitle>Delegate</SectionTitle>
              <Field
                label="Reassign to"
                hint="Only someone authorised on this project can be given the action."
              >
                <select
                  className={inputClasses}
                  value={delegateTo}
                  onChange={(event) => setDelegateTo(event.target.value)}
                >
                  <option value="">Keep with me</option>
                  {(team.data ?? [])
                    .filter((member) => member.is_authorized_here && member.user.id !== action.owner_id)
                    .map((member) => (
                      <option key={member.user.id} value={member.user.id}>
                        {member.user.name} — {member.user.title ?? member.user.role}
                      </option>
                    ))}
                </select>
              </Field>
              <Button
                className="mt-2"
                loading={busy === 'delegate'}
                disabled={!delegateTo}
                onClick={() =>
                  run('delegate', () => api.updateAction(action.id, { owner_id: delegateTo }))
                }
              >
                Delegate
              </Button>
            </div>

            <div className="border-t border-slate-200 pt-4">
              <SectionTitle>Resolve</SectionTitle>
              <Field label="Resolution notes" required>
                <textarea
                  className={inputClasses}
                  rows={2}
                  value={resolution}
                  onChange={(event) => setResolution(event.target.value)}
                />
              </Field>
              <div className="mt-3 space-y-3">
                <Field
                  label="Record a decision"
                  hint="Stored as a durable project decision the handover brief can cite."
                >
                  <input
                    className={inputClasses}
                    value={decision}
                    onChange={(event) => setDecision(event.target.value)}
                    placeholder="e.g. Partial refunds are modelled as their own event type"
                  />
                </Field>
                <Field label="Why">
                  <input
                    className={inputClasses}
                    value={rationale}
                    onChange={(event) => setRationale(event.target.value)}
                  />
                </Field>
              </div>
              <Button
                variant="primary"
                className="mt-3"
                loading={busy === 'resolve'}
                disabled={resolution.trim().length === 0}
                onClick={() =>
                  run('resolve', () =>
                    api.resolveAction(action.id, {
                      resolution_notes: resolution,
                      decision: decision || undefined,
                      decision_rationale: rationale || undefined,
                    }),
                  )
                }
              >
                Resolve action
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </Drawer>
  )
}
