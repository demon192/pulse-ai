/**
 * Record unavailability.
 *
 * Only operational fields are collected. There is deliberately no field for a
 * medical or family reason.
 */

import { useState } from 'react'

import {
  Button,
  Drawer,
  Field,
  InlineError,
  inputClasses,
} from '@/components/ui/primitives'
import { useSession } from '@/hooks/useSession'
import { api } from '@/services/api'
import type { HandoverView } from '@/types/api'

const CATEGORIES = [
  { value: 'unplanned_leave', label: 'Unplanned absence' },
  { value: 'planned_leave', label: 'Planned leave' },
  { value: 'reassignment', label: 'Reassigned to other work' },
]

function localInputValue(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

export function NewHandoverDrawer({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: (view: HandoverView) => void
}) {
  const { session } = useSession()
  // Lazy initialiser: read the clock once, on mount, not on every render.
  const [startTime, setStartTime] = useState(() => localInputValue(new Date()))
  const [expectedReturn, setExpectedReturn] = useState('')
  const [category, setCategory] = useState('unplanned_leave')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit() {
    setSubmitting(true)
    setError(null)
    try {
      const created = await api.createHandover({
        start_time: new Date(startTime).toISOString(),
        expected_return: expectedReturn ? new Date(expectedReturn).toISOString() : null,
        reason_category: category,
        handover_notes: notes || null,
      })
      setNotes('')
      onCreated(created)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not record the handover.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Record unavailability"
      description={`This records that ${session?.user.name ?? 'you'} will be unavailable and starts the coverage workflow.`}
      footer={
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} loading={submitting}>
            Record and continue
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {error ? <InlineError message={error} /> : null}

        <p className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600">
          TeamPulse records dates and affected work only. It does not ask for, store or show a
          medical or personal reason.
        </p>

        <Field label="Unavailable from" required>
          <input
            type="datetime-local"
            className={inputClasses}
            value={startTime}
            onChange={(event) => setStartTime(event.target.value)}
          />
        </Field>

        <Field label="Expected return" hint="Leave blank if it is not known.">
          <input
            type="datetime-local"
            className={inputClasses}
            value={expectedReturn}
            onChange={(event) => setExpectedReturn(event.target.value)}
          />
        </Field>

        <Field label="Category">
          <select
            className={inputClasses}
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            {CATEGORIES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>

        <Field
          label="Handover notes"
          hint="Optional. A brief is generated from project records whether or not you write these."
        >
          <textarea
            className={inputClasses}
            rows={4}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="e.g. Branch feature/settlement-worker is rebased and green; the refund path is untouched."
          />
        </Field>
      </div>
    </Drawer>
  )
}
