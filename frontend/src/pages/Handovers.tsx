/**
 * Handovers.
 *
 * Engineers record unavailability; managers run the impact analysis, read the
 * brief, pick a backup and approve. Recommendations and confirmed assignments
 * are kept visually distinct throughout.
 */

import { AlertCircle, Plus, Sparkles, UserMinus } from 'lucide-react'
import { useState } from 'react'

import { CandidateList } from '@/components/domain/CandidateList'
import { HandoverBriefView } from '@/components/domain/HandoverBriefView'
import { NewHandoverDrawer } from '@/components/domain/NewHandoverDrawer'
import { TaskStatusBadge } from '@/components/domain/labels'
import { PageHeader } from '@/layouts/AppShell'
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
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
import { useSession } from '@/hooks/useSession'
import { formatDate, formatDateTime, formatDayCount, pluralise } from '@/lib/format'
import { api } from '@/services/api'
import type { HandoverAnalysis, HandoverView } from '@/types/api'

const STATUS_TONE: Record<string, 'ok' | 'warn' | 'risk' | 'neutral' | 'navy'> = {
  draft: 'neutral',
  analyzed: 'navy',
  pending_manager_review: 'warn',
  approved: 'navy',
  accepted: 'ok',
  rejected: 'neutral',
  declined: 'warn',
  completed: 'ok',
  cancelled: 'neutral',
}

export function Handovers() {
  const { session } = useSession()
  const handovers = useAsync(() => api.handovers(), [])
  const [showNew, setShowNew] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)

  const isManager = session?.user.role === 'manager'

  return (
    <div>
      <PageHeader
        title="Handovers"
        description="Planned leave and emergency unavailability. TeamPulse records dates and affected work only — never a reason."
        actions={
          <Button variant="primary" size="sm" onClick={() => setShowNew(true)}>
            <Plus className="size-4" />
            Record unavailability
          </Button>
        }
      />

      {handovers.initialLoading ? (
        <Card>
          <LoadingBlock label="Loading handovers" rows={5} />
        </Card>
      ) : null}
      {handovers.error ? (
        <ErrorState message={handovers.error} onRetry={handovers.reload} />
      ) : null}

      {handovers.data && handovers.data.length === 0 ? (
        <Card>
          <EmptyState
            icon={<UserMinus className="size-8" />}
            title="No handovers recorded"
            description="When an engineer becomes unavailable, TeamPulse works out which work is affected and who could cover it."
          />
        </Card>
      ) : null}

      <div className="space-y-4">
        {(handovers.data ?? []).map((view) => (
          <HandoverCard
            key={view.handover.id}
            view={view}
            isManager={Boolean(isManager)}
            expanded={expanded === view.handover.id}
            onToggle={() =>
              setExpanded((current) => (current === view.handover.id ? null : view.handover.id))
            }
            onChanged={() => void handovers.reload()}
          />
        ))}
      </div>

      <NewHandoverDrawer
        open={showNew}
        onClose={() => setShowNew(false)}
        onCreated={(created) => {
          setShowNew(false)
          setExpanded(created.handover.id)
          void handovers.reload()
        }}
      />
    </div>
  )
}

function HandoverCard({
  view,
  isManager,
  expanded,
  onToggle,
  onChanged,
}: {
  view: HandoverView
  isManager: boolean
  expanded: boolean
  onToggle: () => void
  onChanged: () => void
}) {
  const [current, setCurrent] = useState<HandoverView>(view)
  const [analysis, setAnalysis] = useState<HandoverAnalysis | null>(null)
  const [selectedBackup, setSelectedBackup] = useState<string | null>(
    view.handover.selected_backup_id,
  )
  const [rejectReason, setRejectReason] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handover = current.handover
  const analysed = handover.affected_task_ids.length > 0 || handover.generated_brief.length > 0

  async function run(key: string, work: () => Promise<void>) {
    setBusy(key)
    setError(null)
    try {
      await work()
      onChanged()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The action could not be completed.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader
        icon={<UserMinus className="size-4" />}
        title={`${current.unavailable_user_name} — unavailable from ${formatDate(handover.start_time)}`}
        description={
          handover.expected_return
            ? `Expected back ${formatDate(handover.expected_return)}`
            : 'No expected return date recorded'
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={STATUS_TONE[handover.handover_status] ?? 'neutral'}>
              {handover.handover_status.replace(/_/g, ' ')}
            </Badge>
            <Badge tone={handover.manager_approval_status === 'approved' ? 'ok' : 'warn'}>
              Approval: {handover.manager_approval_status}
            </Badge>
            <Button size="sm" onClick={onToggle}>
              {expanded ? 'Hide' : 'Open'}
            </Button>
          </div>
        }
      />

      <CardBody className="border-b border-slate-100 bg-slate-50/60">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <KeyValue label="Affected tasks">{handover.affected_task_ids.length}</KeyValue>
          <KeyValue label="Downstream tasks">{handover.downstream_task_ids.length}</KeyValue>
          <KeyValue label="Eligible candidates">
            {current.eligible_candidate_count}
          </KeyValue>
          <KeyValue label="Selected backup">
            {current.selected_backup_name ?? 'Not selected'}
          </KeyValue>
        </dl>
      </CardBody>

      {expanded ? (
        <CardBody className="space-y-6">
          {error ? <InlineError message={error} /> : null}

          {!analysed ? (
            <div className="rounded-lg border border-navy-200 bg-navy-50 px-4 py-4">
              <p className="text-sm font-medium text-navy-900">Impact has not been analysed yet</p>
              <p className="mt-1 text-sm text-slate-600">
                TeamPulse will find the active tasks, walk the dependency graph, collect the
                documentation and pending approvals, rank eligible backups and generate a brief.
              </p>
              <Button
                variant="primary"
                className="mt-3"
                loading={busy === 'analyze'}
                onClick={() =>
                  run('analyze', async () => {
                    const result = await api.analyzeHandover(handover.id)
                    setCurrent(result.handover)
                    setAnalysis(result.analysis)
                  })
                }
              >
                <Sparkles className="size-4" />
                Analyse impact and generate brief
              </Button>
            </div>
          ) : null}

          {/* Impact */}
          {analysed ? (
            <section>
              <SectionTitle hint="Deterministic dependency traversal">
                Affected work
              </SectionTitle>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-xs font-medium text-slate-500">
                    Active tasks ({current.affected_tasks.length})
                  </p>
                  <ul className="mt-1.5 space-y-1.5">
                    {current.affected_tasks.map((task) => (
                      <li key={task.id} className="flex items-start gap-2 text-sm">
                        <TaskStatusBadge status={task.status} />
                        <span className="min-w-0">
                          <span className="block text-navy-900">{task.title}</span>
                          <span className="block text-xs text-slate-500">
                            {task.due_date ? formatDate(task.due_date) : 'No due date'} ·{' '}
                            {task.priority}
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500">
                    Downstream dependencies ({current.downstream_tasks.length})
                  </p>
                  <ul className="mt-1.5 space-y-1.5">
                    {current.downstream_tasks.map((task) => (
                      <li key={task.id} className="flex items-start gap-2 text-sm">
                        <TaskStatusBadge status={task.status} />
                        <span className="truncate text-navy-900">{task.title}</span>
                      </li>
                    ))}
                    {current.downstream_tasks.length === 0 ? (
                      <li className="text-sm text-slate-500">None.</li>
                    ) : null}
                  </ul>
                </div>
              </div>

              {current.affected_milestones.length > 0 ? (
                <div className="mt-4">
                  <p className="text-xs font-medium text-slate-500">Milestones that could slip</p>
                  <ul className="mt-1.5 space-y-1">
                    {current.affected_milestones.map((milestone) => (
                      <li key={milestone.milestone_id} className="flex flex-wrap items-center gap-2 text-sm">
                        <span className="text-navy-900">{milestone.name}</span>
                        <Badge tone={milestone.at_risk ? 'risk' : 'ok'}>
                          {formatDayCount(milestone.days_remaining)}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {current.pending_actions.length > 0 ? (
                <div className="mt-4">
                  <p className="text-xs font-medium text-slate-500">
                    Pending approvals in the way ({current.pending_actions.length})
                  </p>
                  <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-slate-700">
                    {current.pending_actions.map((action) => (
                      <li key={action.id}>
                        {action.title} — {action.type.replace(/_/g, ' ')}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {current.documents.length > 0 ? (
                <div className="mt-4">
                  <p className="text-xs font-medium text-slate-500">
                    Relevant documents ({current.documents.length})
                  </p>
                  <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-slate-700">
                    {current.documents.map((document) => (
                      <li key={document.id}>{document.title}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>
          ) : null}

          {/* Candidates */}
          {handover.candidate_recommendations.length > 0 ? (
            <section>
              <SectionTitle
                hint={
                  isManager
                    ? 'A recommendation, not an assignment'
                    : 'You only see your own score'
                }
              >
                Backup candidates
              </SectionTitle>
              <CandidateList
                candidates={handover.candidate_recommendations}
                selectedId={selectedBackup}
                onSelect={
                  isManager && current.can_approve && handover.manager_approval_status !== 'approved'
                    ? setSelectedBackup
                    : undefined
                }
                disabled={busy !== null}
              />
            </section>
          ) : null}

          {/* Brief */}
          {handover.generated_brief.length > 0 ? (
            <section className="space-y-3">
              <SectionTitle hint="Synthesised from authorised project records">
                Handover brief
              </SectionTitle>
              {handover.generated_brief.map((brief) => (
                <HandoverBriefView key={brief.task_id} brief={brief} />
              ))}
              {handover.missing_information.length > 0 ? (
                <div className="rounded-lg border border-warn-200 bg-warn-50 p-3">
                  <p className="flex items-center gap-1.5 text-sm font-semibold text-warn-700">
                    <AlertCircle className="size-4" />
                    Missing information to confirm with a human
                  </p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-warn-700">
                    {handover.missing_information.map((entry) => (
                      <li key={entry}>{entry}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>
          ) : null}

          {/* Manager decision */}
          {isManager && current.can_approve && handover.manager_approval_status !== 'approved' ? (
            <section className="rounded-lg border border-slate-200 bg-white px-4 py-4">
              <SectionTitle>Manager decision</SectionTitle>
              <p className="text-sm text-slate-600">
                Approving nominates the selected backup. Ownership only transfers once they accept.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  loading={busy === 'approve'}
                  disabled={!selectedBackup}
                  onClick={() =>
                    run('approve', async () => {
                      setCurrent(
                        await api.approveHandover(handover.id, {
                          selected_backup_id: selectedBackup as string,
                        }),
                      )
                    })
                  }
                >
                  Approve handover
                </Button>
              </div>
              <div className="mt-4 border-t border-slate-200 pt-4">
                <Field label="Reject instead" hint="Say why, so the engineer knows where it stands.">
                  <input
                    className={inputClasses}
                    value={rejectReason}
                    onChange={(event) => setRejectReason(event.target.value)}
                  />
                </Field>
                <Button
                  variant="danger"
                  className="mt-2"
                  loading={busy === 'reject'}
                  disabled={rejectReason.trim().length === 0}
                  onClick={() =>
                    run('reject', async () => {
                      setCurrent(
                        await api.rejectHandover(handover.id, { reason: rejectReason }),
                      )
                    })
                  }
                >
                  Reject
                </Button>
              </div>
            </section>
          ) : null}

          {/* Backup decision */}
          {current.can_accept ? (
            <section className="rounded-lg border border-ok-200 bg-ok-50 px-4 py-4">
              <p className="text-sm font-semibold text-ok-700">You have been nominated as backup</p>
              <p className="mt-1 text-sm text-ok-700">
                Accepting transfers ownership of {pluralise(handover.affected_task_ids.length, 'task')} to you.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  loading={busy === 'accept'}
                  onClick={() =>
                    run('accept', async () => {
                      setCurrent(await api.acceptHandover(handover.id))
                    })
                  }
                >
                  Accept the assignment
                </Button>
                <Button
                  loading={busy === 'decline'}
                  onClick={() =>
                    run('decline', async () => {
                      setCurrent(
                        await api.declineHandover(handover.id, {
                          reason: 'Declined by the nominated backup.',
                        }),
                      )
                    })
                  }
                >
                  Decline
                </Button>
              </div>
            </section>
          ) : null}

          {/* Confirmation and audit */}
          {handover.backup_accepted_at ? (
            <div className="rounded-lg border border-ok-200 bg-ok-50 px-4 py-3">
              <p className="text-sm font-semibold text-ok-700">Assignment confirmed</p>
              <p className="mt-1 text-sm text-ok-700">
                {current.selected_backup_name} accepted on{' '}
                {formatDateTime(handover.backup_accepted_at)}. Approved by{' '}
                {current.approved_by_name ?? 'a manager'}.
              </p>
            </div>
          ) : null}

          {current.audit_trail.length > 0 ? (
            <section>
              <SectionTitle>Audit trail</SectionTitle>
              <ul className="space-y-1 text-xs text-slate-600">
                {current.audit_trail.map((event) => (
                  <li key={event.id}>
                    {formatDateTime(event.created_at)} — {event.action} by {event.actor_id}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {analysis?.upstream_blocking_task_ids.length ? (
            <p className="text-xs text-slate-500">
              Upstream work this depends on: {analysis.upstream_blocking_task_ids.join(', ')}
            </p>
          ) : null}
        </CardBody>
      ) : null}
    </Card>
  )
}
