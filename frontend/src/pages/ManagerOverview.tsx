/** Manager overview: what needs attention today, and why. */

import {
  AlertTriangle,
  BadgeCheck,
  CalendarClock,
  Inbox,
  LifeBuoy,
  Sparkles,
  UserMinus,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ActionInboxRow } from '@/components/domain/ActionInboxRow'
import { AIProvenance, HealthBadge } from '@/components/domain/labels'
import { RiskCard } from '@/components/domain/RiskCard'
import { PageHeader } from '@/layouts/AppShell'
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  ErrorState,
  InlineError,
  LoadingBlock,
  MetricTile,
  ProgressBar,
  SectionTitle,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { formatDayCount, pluralise } from '@/lib/format'
import { api } from '@/services/api'
import type { AIEnvelope, ProjectBriefingData } from '@/types/api'

export function ManagerOverview() {
  const navigate = useNavigate()
  const dashboard = useAsync(() => api.managerDashboard(), [])
  const [briefing, setBriefing] = useState<AIEnvelope<ProjectBriefingData> | null>(null)
  const [briefingError, setBriefingError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  if (dashboard.initialLoading) {
    return (
      <Card>
        <LoadingBlock label="Loading the manager overview" rows={6} />
      </Card>
    )
  }
  if (dashboard.error || !dashboard.data) {
    return <ErrorState message={dashboard.error ?? 'No data.'} onRetry={dashboard.reload} />
  }

  const data = dashboard.data
  const { summary } = data
  const focusProject = data.project_health[0]
  const activeBriefing = briefing ?? data.daily_briefing

  async function generateBriefing() {
    if (!focusProject) return
    setGenerating(true)
    setBriefingError(null)
    try {
      setBriefing(await api.projectBriefing(focusProject.project_id, true))
    } catch (caught) {
      setBriefingError(
        caught instanceof Error ? caught.message : 'Could not generate the briefing.',
      )
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="What needs your attention today"
        description="Pending decisions, delivery risk and coverage, assembled from project records by deterministic rules."
        actions={
          <Button variant="secondary" size="sm" onClick={dashboard.reload} loading={dashboard.loading}>
            Refresh
          </Button>
        }
      />

      {/* Summary tiles. Each one opens the filtered list behind it. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricTile
          label="Pending approvals"
          value={summary.pending_approvals}
          tone={summary.pending_approvals > 0 ? 'warn' : 'ok'}
          icon={<BadgeCheck className="size-4" />}
          onClick={() => navigate('/inbox?bucket=approvals')}
        />
        <MetricTile
          label="Open support requests"
          value={summary.open_support_requests}
          tone={summary.open_support_requests > 0 ? 'info' : 'ok'}
          icon={<LifeBuoy className="size-4" />}
          onClick={() => navigate('/requests')}
        />
        <MetricTile
          label="Tasks needing attention"
          value={summary.tasks_needing_attention}
          tone={summary.tasks_needing_attention > 0 ? 'risk' : 'ok'}
          hint="blocked or overdue"
          icon={<AlertTriangle className="size-4" />}
          onClick={() => navigate('/projects')}
        />
        <MetricTile
          label="Coverage gaps"
          value={summary.coverage_gaps}
          tone={summary.coverage_gaps > 0 ? 'risk' : 'ok'}
          hint="no approved handover"
          icon={<UserMinus className="size-4" />}
          onClick={() => navigate('/handovers')}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          {/* Action inbox preview */}
          <Card>
            <CardHeader
              icon={<Inbox className="size-4" />}
              title="Action inbox"
              description="Ranked by urgency, deadline, blocked work and milestone proximity."
              actions={
                <Link to="/inbox">
                  <Button size="sm">Open inbox</Button>
                </Link>
              }
            />
            {data.action_inbox.length === 0 ? (
              <EmptyState
                title="Nothing is waiting on you"
                description="No approvals, questions or follow-ups are open."
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.action_inbox.slice(0, 5).map((item) => (
                  <ActionInboxRow key={item.action.id} item={item} compact />
                ))}
              </ul>
            )}
          </Card>

          {/* Risks */}
          <section>
            <SectionTitle hint="Produced by the rules engine, not the model">
              Why delivery is at risk
            </SectionTitle>
            {data.top_risks.length === 0 ? (
              <Card>
                <EmptyState
                  title="No delivery risks detected"
                  description="No blockers, overdue tasks or pending decisions are affecting a milestone."
                />
              </Card>
            ) : (
              <div className="space-y-2">
                {data.top_risks.slice(0, 5).map((finding, index) => (
                  <RiskCard
                    key={finding.id}
                    finding={finding}
                    defaultOpen={index === 0}
                    onOpenTask={(taskId) => navigate(`/projects/${finding.project_id}?task=${taskId}`)}
                  />
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="space-y-6">
          {/* AI briefing */}
          <Card>
            <CardHeader
              icon={<Sparkles className="size-4" />}
              title="Daily briefing"
              description={
                focusProject
                  ? `For ${focusProject.project_name}, the project needing most attention.`
                  : undefined
              }
              actions={
                <Button size="sm" onClick={generateBriefing} loading={generating}>
                  {activeBriefing ? 'Regenerate' : 'Generate'}
                </Button>
              }
            />
            <CardBody>
              {briefingError ? <InlineError message={briefingError} /> : null}
              {activeBriefing ? (
                <div className="space-y-3">
                  <AIProvenance meta={activeBriefing.meta} />
                  <p className="text-sm text-navy-900">{activeBriefing.data.progress_summary}</p>
                  {activeBriefing.data.recommended_actions.length > 0 ? (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Recommended actions
                      </p>
                      <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-slate-700">
                        {activeBriefing.data.recommended_actions.map((action) => (
                          <li key={action}>{action}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {activeBriefing.data.uncertainties.length > 0 ? (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Uncertainties
                      </p>
                      <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-slate-600">
                        {activeBriefing.data.uncertainties.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  No briefing has been generated yet. TeamPulse does not call the model on every
                  page load — generate one when you want it.
                </p>
              )}
            </CardBody>
          </Card>

          {/* Project health */}
          <Card>
            <CardHeader title="Project health" description="Worst first." />
            <ul className="divide-y divide-slate-100">
              {data.project_health.map((report) => (
                <li key={report.project_id}>
                  <Link
                    to={`/projects/${report.project_id}`}
                    className="block px-5 py-3 transition-colors hover:bg-slate-50"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-medium text-navy-900">
                        {report.project_name}
                      </span>
                      <HealthBadge health={report.health} score={report.health_score} />
                    </div>
                    <div className="mt-2">
                      <ProgressBar
                        value={report.health_score}
                        tone={
                          report.health === 'at_risk'
                            ? 'risk'
                            : report.health === 'needs_attention'
                              ? 'warn'
                              : 'ok'
                        }
                        label={`${report.project_name} health`}
                      />
                    </div>
                    <p className="mt-2 text-xs text-slate-600">{report.headline}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {report.completed_tasks}/{report.total_tasks} complete ·{' '}
                      {report.blocked_tasks} blocked · {report.overdue_tasks} overdue
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>

          {/* Milestones */}
          <Card>
            <CardHeader
              icon={<CalendarClock className="size-4" />}
              title="Upcoming milestones"
            />
            {data.upcoming_milestones.length === 0 ? (
              <EmptyState title="No upcoming milestones" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.upcoming_milestones.map((milestone) => (
                  <li key={milestone.milestone_id} className="px-5 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-medium text-navy-900">{milestone.name}</span>
                      <Badge tone={milestone.at_risk ? 'risk' : 'ok'}>
                        {formatDayCount(milestone.days_remaining)}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-600">
                      {milestone.completed_tasks}/{milestone.total_tasks} tasks complete
                    </p>
                    {milestone.at_risk ? (
                      <p className="mt-1 text-xs text-risk-600">{milestone.reasons.join('; ')}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Coverage */}
          <Card>
            <CardHeader
              icon={<UserMinus className="size-4" />}
              title="Handover coverage"
              description="Engineers recorded as unavailable with open work."
            />
            {data.coverage.length === 0 ? (
              <EmptyState
                title="Everyone's work is covered"
                description="No unavailable engineer has uncovered open tasks."
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.coverage.map((gap) => (
                  <li key={gap.user_id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-navy-900">{gap.user_name}</p>
                      <p className="text-xs text-slate-600">
                        {pluralise(gap.open_task_count, 'open task')} · {gap.availability_status}
                      </p>
                    </div>
                    {gap.has_approved_handover ? (
                      <Badge tone="ok">Covered</Badge>
                    ) : (
                      <Link to="/handovers">
                        <Button size="sm" variant="primary">
                          Arrange cover
                        </Button>
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Recent activity */}
          <Card>
            <CardHeader title="Recent activity" />
            {data.recent_activity.length === 0 ? (
              <EmptyState title="No recent activity" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.recent_activity.slice(0, 6).map((notification) => (
                  <li key={notification.id} className="px-5 py-2.5">
                    <p className="text-sm text-navy-900">{notification.title}</p>
                    <p className="text-xs text-slate-500">{notification.reason}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
