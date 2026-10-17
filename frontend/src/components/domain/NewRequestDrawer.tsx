/**
 * Raise a support request.
 *
 * After submitting, Gemini's interpretation is shown next to what the engineer
 * actually wrote — and the engineer can correct it, because the model is
 * assisting them, not classifying them.
 */

import { Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'

import { AIProvenance, REQUEST_CATEGORY_LABEL } from '@/components/domain/labels'
import {
  Badge,
  Button,
  Card,
  CardBody,
  Drawer,
  Field,
  InlineError,
  inputClasses,
} from '@/components/ui/primitives'
import { api, ApiError } from '@/services/api'
import type {
  AIEnvelope,
  Priority,
  RequestCategory,
  RequestInterpretationData,
  SupportRequestCreated,
  TaskView,
} from '@/types/api'

const CATEGORIES: RequestCategory[] = [
  'approval',
  'decision',
  'blocker',
  'one_on_one',
  'progress_update',
  'other',
]
const PRIORITIES: Priority[] = ['low', 'medium', 'high', 'critical']

export function NewRequestDrawer({
  open,
  onClose,
  projects,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  projects: { id: string; name: string }[]
  onCreated: () => void
}) {
  const [projectId, setProjectId] = useState('')
  const [taskId, setTaskId] = useState('')
  const [category, setCategory] = useState<RequestCategory>('blocker')
  const [priority, setPriority] = useState<Priority>('medium')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [tasks, setTasks] = useState<TaskView[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [result, setResult] = useState<SupportRequestCreated | null>(null)
  const [contextNote, setContextNote] = useState('')
  const [savingNote, setSavingNote] = useState(false)

  // Derived during render rather than synchronised through an effect: the
  // first project is the default until the engineer picks another.
  const selectedProjectId = projectId || projects[0]?.id || ''

  useEffect(() => {
    if (!selectedProjectId) return
    let cancelled = false
    api
      .project(selectedProjectId)
      .then((detail) => {
        if (!cancelled) setTasks(detail.tasks)
      })
      .catch(() => {
        if (!cancelled) setTasks([])
      })
    return () => {
      cancelled = true
    }
  }, [selectedProjectId])

  function reset() {
    setTitle('')
    setDescription('')
    setTaskId('')
    setResult(null)
    setContextNote('')
    setError(null)
    setFieldErrors({})
  }

  async function submit() {
    setSubmitting(true)
    setError(null)
    setFieldErrors({})
    try {
      const created = await api.createRequest({
        project_id: selectedProjectId,
        category,
        title,
        description,
        task_id: taskId || null,
        priority,
      })
      setResult(created)
      onCreated()
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message)
        setFieldErrors(
          Object.fromEntries(caught.fieldErrors.map((item) => [item.field, item.message])),
        )
      } else {
        setError('Could not submit the request.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function saveCorrection() {
    if (!result) return
    setSavingNote(true)
    try {
      await api.updateRequest(result.request.id, { engineer_context_note: contextNote })
      setContextNote('')
      onCreated()
    } finally {
      setSavingNote(false)
    }
  }

  const interpretation: AIEnvelope<RequestInterpretationData> | null =
    result?.interpretation ?? null

  return (
    <Drawer
      open={open}
      onClose={() => {
        reset()
        onClose()
      }}
      title={result ? 'Request submitted' : 'Ask for support'}
      description={
        result
          ? 'Your manager has been notified. The request stays visible until it is resolved.'
          : 'This becomes a tracked item in your manager’s inbox, not a message that can be missed.'
      }
      footer={
        result ? (
          <div className="flex justify-end gap-2">
            <Button onClick={reset}>Raise another</Button>
            <Button
              variant="primary"
              onClick={() => {
                reset()
                onClose()
              }}
            >
              Done
            </Button>
          </div>
        ) : (
          <div className="flex justify-end gap-2">
            <Button onClick={onClose}>Cancel</Button>
            <Button
              variant="primary"
              onClick={submit}
              loading={submitting}
              disabled={
                !selectedProjectId ||
                title.trim().length < 3 ||
                description.trim().length === 0
              }
            >
              Submit request
            </Button>
          </div>
        )
      }
    >
      {result ? (
        <div className="space-y-4">
          <Card>
            <CardBody>
              <p className="text-sm font-semibold text-navy-900">{result.request.title}</p>
              <p className="mt-1 text-sm whitespace-pre-line text-slate-700">
                {result.request.description}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge tone="warn">Open</Badge>
                <Badge tone="neutral">{REQUEST_CATEGORY_LABEL[result.request.category]}</Badge>
                {result.action_item ? (
                  <Badge tone="navy">Tracked as action {result.action_item.id}</Badge>
                ) : (
                  <Badge tone="neutral">No manager action needed</Badge>
                )}
              </div>
            </CardBody>
          </Card>

          {interpretation ? (
            <Card>
              <CardBody className="space-y-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="size-4 text-navy-500" />
                  <p className="text-sm font-semibold text-navy-900">How TeamPulse read this</p>
                </div>
                <AIProvenance meta={interpretation.meta} />
                <p className="text-sm text-navy-900">{interpretation.data.summary}</p>
                <div className="flex flex-wrap gap-2 text-xs">
                  <Badge tone="neutral">
                    Suggested category: {interpretation.data.suggested_category.replace(/_/g, ' ')}
                  </Badge>
                  <Badge tone="neutral">
                    Suggested priority: {interpretation.data.suggested_priority}
                  </Badge>
                </div>
                {interpretation.data.suggested_next_steps.length > 0 ? (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Suggested next steps
                    </p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                      {interpretation.data.suggested_next_steps.map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {interpretation.data.missing_context.length > 0 ? (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Context that would help
                    </p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                      {interpretation.data.missing_context.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <Field
                  label="Correct or add context"
                  hint="If this reading is wrong, say so. Your note is attached to the request."
                >
                  <textarea
                    className={inputClasses}
                    rows={2}
                    value={contextNote}
                    onChange={(event) => setContextNote(event.target.value)}
                  />
                </Field>
                <Button
                  size="sm"
                  onClick={saveCorrection}
                  loading={savingNote}
                  disabled={contextNote.trim().length === 0}
                >
                  Attach note
                </Button>
              </CardBody>
            </Card>
          ) : null}
        </div>
      ) : (
        <div className="space-y-4">
          {error ? <InlineError message={error} /> : null}

          <Field label="Project" required>
            <select
              className={inputClasses}
              value={selectedProjectId}
              onChange={(event) => setProjectId(event.target.value)}
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Related task" hint="Linking a task lets TeamPulse show the delivery impact.">
            <select
              className={inputClasses}
              value={taskId}
              onChange={(event) => setTaskId(event.target.value)}
            >
              <option value="">Not task-specific</option>
              {tasks.map((view) => (
                <option key={view.task.id} value={view.task.id}>
                  {view.task.title}
                </option>
              ))}
            </select>
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="What do you need?" required>
              <select
                className={inputClasses}
                value={category}
                onChange={(event) => setCategory(event.target.value as RequestCategory)}
              >
                {CATEGORIES.map((value) => (
                  <option key={value} value={value}>
                    {REQUEST_CATEGORY_LABEL[value]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Priority">
              <select
                className={inputClasses}
                value={priority}
                onChange={(event) => setPriority(event.target.value as Priority)}
              >
                {PRIORITIES.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label="Title" required error={fieldErrors.title}>
            <input
              className={inputClasses}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. Approve the settlement API contract"
            />
          </Field>

          <Field
            label="Description"
            required
            error={fieldErrors.description}
            hint="What is blocked, what you need decided, and by when."
          >
            <textarea
              className={inputClasses}
              rows={5}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>
        </div>
      )}
    </Drawer>
  )
}
