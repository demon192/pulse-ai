/** Read a request, respond to it, and record its outcome. */

import { useState } from 'react'

import {
  PriorityBadge,
  REQUEST_CATEGORY_LABEL,
  REQUEST_STATUS_TONE,
} from '@/components/domain/labels'
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
import { formatDateTime, relativeDays, titleCase } from '@/lib/format'
import { useSession } from '@/hooks/useSession'
import { api } from '@/services/api'
import type { SupportRequestView } from '@/types/api'

export function RequestDrawer({
  view,
  onClose,
  onChanged,
}: {
  view: SupportRequestView | null
  onClose: () => void
  onChanged: () => void
}) {
  const { session } = useSession()
  const [current, setCurrent] = useState<SupportRequestView | null>(null)
  const [response, setResponse] = useState('')
  const [resolution, setResolution] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (!view) return null
  const active = current?.request.id === view.request.id ? current : view
  const { request } = active
  const isManager = session?.user.role === 'manager'
  const isAuthor = session?.user.id === request.engineer_id
  const isOpen = !['resolved', 'cancelled'].includes(request.status)

  async function run(key: string, work: () => Promise<SupportRequestView>) {
    setBusy(key)
    setError(null)
    try {
      setCurrent(await work())
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
      onClose={() => {
        setCurrent(null)
        setResponse('')
        setResolution('')
        setNote('')
        setError(null)
        onClose()
      }}
      title={request.title}
      description={`${active.engineer_name} · ${active.project_name}${
        active.task_title ? ` · ${active.task_title}` : ''
      }`}
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={REQUEST_STATUS_TONE[request.status]}>{titleCase(request.status)}</Badge>
          <Badge tone="neutral">{REQUEST_CATEGORY_LABEL[request.category]}</Badge>
          <PriorityBadge priority={request.priority} />
          {active.action_item_id ? (
            <Badge tone="navy">Tracked as {active.action_item_id}</Badge>
          ) : null}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-sm whitespace-pre-line text-slate-700">{request.description}</p>
          <p className="mt-2 text-xs text-slate-400">
            Raised {relativeDays(request.created_at)} · {formatDateTime(request.created_at)}
          </p>
        </div>

        {request.engineer_context_note ? (
          <div className="rounded-lg border border-info-200 bg-info-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-info-700">
              Engineer’s added context
            </p>
            <p className="mt-1 text-sm text-info-700">{request.engineer_context_note}</p>
          </div>
        ) : null}

        <dl className="grid grid-cols-2 gap-4 rounded-lg border border-slate-200 bg-white px-4 py-3">
          <KeyValue label="Assigned to">{active.owner_name ?? 'Unassigned'}</KeyValue>
          <KeyValue label="Due">{request.due_date ? relativeDays(request.due_date) : 'No due date'}</KeyValue>
        </dl>

        <div>
          <SectionTitle>Responses</SectionTitle>
          {request.responses.length === 0 ? (
            <p className="text-sm text-slate-500">No response yet.</p>
          ) : (
            <ul className="space-y-2">
              {request.responses.map((item, index) => (
                <li key={index} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                  <p className="text-sm text-slate-700">{item.body}</p>
                  <p className="mt-1 text-xs text-slate-400">{formatDateTime(item.created_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        {request.resolution_notes ? (
          <div className="rounded-lg border border-ok-200 bg-ok-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-ok-700">Outcome</p>
            <p className="mt-1 text-sm text-ok-700">{request.resolution_notes}</p>
          </div>
        ) : null}

        {error ? <InlineError message={error} /> : null}

        {isManager && isOpen ? (
          <div className="space-y-4 rounded-lg border border-slate-200 bg-white px-4 py-4">
            <SectionTitle>Respond</SectionTitle>
            <Field label="Response to the engineer">
              <textarea
                className={inputClasses}
                rows={3}
                value={response}
                onChange={(event) => setResponse(event.target.value)}
                placeholder="What you have decided, or what you need from them."
              />
            </Field>
            <Button
              variant="primary"
              loading={busy === 'respond'}
              disabled={response.trim().length === 0}
              onClick={() =>
                run('respond', async () => {
                  const updated = await api.respondToRequest(request.id, { body: response })
                  setResponse('')
                  return updated
                })
              }
            >
              Send response
            </Button>

            <div className="border-t border-slate-200 pt-4">
              <SectionTitle>Resolve</SectionTitle>
              <Field label="Resolution notes" hint="The engineer sees this on their request.">
                <textarea
                  className={inputClasses}
                  rows={2}
                  value={resolution}
                  onChange={(event) => setResolution(event.target.value)}
                />
              </Field>
              <Button
                className="mt-2"
                loading={busy === 'resolve'}
                disabled={resolution.trim().length === 0}
                onClick={() =>
                  run('resolve', () =>
                    api.updateRequest(request.id, {
                      status: 'resolved',
                      resolution_notes: resolution,
                    }),
                  )
                }
              >
                Mark resolved
              </Button>
            </div>
          </div>
        ) : null}

        {isAuthor && isOpen ? (
          <div className="space-y-3 rounded-lg border border-slate-200 bg-white px-4 py-4">
            <SectionTitle>Add context</SectionTitle>
            <Field label="Anything that would help" hint="Also use this to correct an inaccurate AI summary.">
              <textarea
                className={inputClasses}
                rows={2}
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </Field>
            <div className="flex flex-wrap gap-2">
              <Button
                loading={busy === 'note'}
                disabled={note.trim().length === 0}
                onClick={() =>
                  run('note', async () => {
                    const updated = await api.updateRequest(request.id, {
                      engineer_context_note: note,
                    })
                    setNote('')
                    return updated
                  })
                }
              >
                Attach note
              </Button>
              <Button
                variant="ghost"
                loading={busy === 'cancel'}
                onClick={() => run('cancel', () => api.updateRequest(request.id, { status: 'cancelled' }))}
              >
                Cancel this request
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </Drawer>
  )
}
