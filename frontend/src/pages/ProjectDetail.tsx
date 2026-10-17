/** One project: tasks, dependencies, milestones, risks, documents, decisions. */

import { ArrowLeft, FileText, Gavel, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { TaskRow } from '@/components/domain/TaskRow'
import { TaskDrawer } from '@/components/domain/TaskDrawer'
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
  KeyValue,
  LoadingBlock,
  Tabs,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { formatDate, formatDayCount } from '@/lib/format'
import { api } from '@/services/api'
import type { AIEnvelope, ProjectBriefingData } from '@/types/api'

type TabId = 'tasks' | 'risks' | 'milestones' | 'knowledge'

export function ProjectDetail() {
  const { projectId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState<TabId>('tasks')
  const [briefing, setBriefing] = useState<AIEnvelope<ProjectBriefingData> | null>(null)
  const [briefingError, setBriefingError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const project = useAsync(() => api.project(projectId), [projectId])

  const openTaskId = searchParams.get('task')

  if (project.initialLoading) {
    return (
      <Card>
        <LoadingBlock label="Loading the project" rows={6} />
      </Card>
    )
  }
  if (project.error || !project.data) {
    return <ErrorState message={project.error ?? 'No data.'} onRetry={project.reload} />
  }

  const data = project.data
  const activeBriefing = briefing ?? data.cached_briefing

  async function generateBriefing() {
    setGenerating(true)
    setBriefingError(null)
    try {
      setBriefing(await api.projectBriefing(projectId, true))
    } catch (caught) {
      setBriefingError(caught instanceof Error ? caught.message : 'Could not generate a briefing.')
    } finally {
      setGenerating(false)
    }
  }

  function openTask(taskId: string | null) {
    const next = new URLSearchParams(searchParams)
    if (taskId) next.set('task', taskId)
    else next.delete('task')
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="space-y-5">
      <Link
        to="/projects"
        className="inline-flex items-center gap-1 text-sm text-navy-600 hover:underline"
      >
        <ArrowLeft className="size-4" />
        All projects
      </Link>

      <PageHeader
        title={data.project.name}
        description={data.project.description}
        actions={
          <>
            <HealthBadge health={data.health.health} score={data.health.health_score} />
            <Button size="sm" onClick={generateBriefing} loading={generating}>
              <Sparkles className="size-4" />
              {activeBriefing ? 'Regenerate briefing' : 'Generate briefing'}
            </Button>
          </>
        }
      />

      <Card>
        <CardBody>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <KeyValue label="Manager">{data.manager_name}</KeyValue>
            <KeyValue label="Target date">{formatDate(data.project.target_date)}</KeyValue>
            <KeyValue label="Tasks">
              {data.health.completed_tasks}/{data.health.total_tasks} complete
            </KeyValue>
            <KeyValue label="Team">{data.team.length} people</KeyValue>
          </dl>
        </CardBody>
      </Card>

      {briefingError ? <InlineError message={briefingError} /> : null}
      {activeBriefing ? (
        <Card>
          <CardHeader
            icon={<Sparkles className="size-4" />}
            title="AI project briefing"
            description="Written by Gemini from the project records and the rules-engine findings."
          />
          <CardBody className="space-y-3">
            <AIProvenance meta={activeBriefing.meta} />
            <p className="text-sm text-navy-900">{activeBriefing.data.progress_summary}</p>
            {activeBriefing.data.key_risks.length > 0 ? (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Key risks
                </p>
                <ul className="mt-1.5 space-y-1.5">
                  {activeBriefing.data.key_risks.map((risk) => (
                    <li key={risk.title} className="text-sm">
                      <span className="font-medium text-navy-900">{risk.title}</span>
                      <span className="text-slate-600"> — {risk.explanation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
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
          </CardBody>
        </Card>
      ) : null}

      <Card className="overflow-hidden">
        <Tabs<TabId>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'tasks', label: 'Tasks', count: data.tasks.length },
            { id: 'risks', label: 'Risks', count: data.health.risks.length },
            { id: 'milestones', label: 'Milestones', count: data.milestones.length },
            {
              id: 'knowledge',
              label: 'Documents & decisions',
              count: data.documents.length + data.decisions.length,
            },
          ]}
        />

        {tab === 'tasks' ? (
          <ul className="divide-y divide-slate-100">
            {data.tasks.map((view) => (
              <TaskRow key={view.task.id} view={view} onOpen={openTask} />
            ))}
          </ul>
        ) : null}

        {tab === 'risks' ? (
          <CardBody className="space-y-2 bg-slate-50/60">
            {data.health.risks.length === 0 ? (
              <EmptyState
                title="No risks detected"
                description="No blockers, overdue tasks or pending decisions affect this project."
              />
            ) : (
              data.health.risks.map((finding) => (
                <RiskCard key={finding.id} finding={finding} onOpenTask={openTask} />
              ))
            )}
          </CardBody>
        ) : null}

        {tab === 'milestones' ? (
          <ul className="divide-y divide-slate-100">
            {data.health.milestones.map((milestone) => (
              <li key={milestone.milestone_id} className="px-5 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium text-navy-900">{milestone.name}</span>
                  <div className="flex items-center gap-2">
                    <Badge tone={milestone.at_risk ? 'risk' : 'ok'}>
                      {milestone.at_risk ? 'At risk' : 'On track'}
                    </Badge>
                    <span className="text-xs text-slate-500">
                      {formatDate(milestone.target_date)} ·{' '}
                      {formatDayCount(milestone.days_remaining)}
                    </span>
                  </div>
                </div>
                <p className="mt-1 text-xs text-slate-600">
                  {milestone.completed_tasks}/{milestone.total_tasks} complete ·{' '}
                  {milestone.blocked_tasks} blocked · {milestone.overdue_tasks} overdue
                </p>
                <ul className="mt-1 list-disc pl-5 text-xs text-slate-600">
                  {milestone.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        ) : null}

        {tab === 'knowledge' ? (
          <CardBody className="grid gap-5 md:grid-cols-2">
            <div>
              <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <FileText className="size-3.5" />
                Documents
              </p>
              <ul className="mt-2 space-y-2">
                {data.documents.map((document) => (
                  <li key={document.id} className="rounded-lg border border-slate-200 px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-navy-900">{document.title}</span>
                      <Badge tone="neutral">{document.doc_type}</Badge>
                    </div>
                    {document.summary ? (
                      <p className="mt-1 text-xs text-slate-600">{document.summary}</p>
                    ) : null}
                    {document.url ? (
                      <span className="mt-1 block truncate text-xs text-slate-400">
                        {document.url}
                      </span>
                    ) : null}
                  </li>
                ))}
                {data.documents.length === 0 ? (
                  <li className="text-sm text-slate-500">No documents recorded.</li>
                ) : null}
              </ul>
            </div>
            <div>
              <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <Gavel className="size-3.5" />
                Decisions
              </p>
              <ul className="mt-2 space-y-2">
                {data.decisions.map((decision) => (
                  <li key={decision.id} className="rounded-lg border border-slate-200 px-3 py-2">
                    <p className="text-sm font-medium text-navy-900">{decision.title}</p>
                    <p className="mt-1 text-xs text-slate-700">{decision.decision}</p>
                    {decision.rationale ? (
                      <p className="mt-1 text-xs text-slate-500">Why: {decision.rationale}</p>
                    ) : null}
                    <p className="mt-1 text-xs text-slate-400">
                      Recorded {formatDate(decision.decided_at)}
                    </p>
                  </li>
                ))}
                {data.decisions.length === 0 ? (
                  <li className="text-sm text-slate-500">No decisions recorded.</li>
                ) : null}
              </ul>
            </div>
          </CardBody>
        ) : null}
      </Card>

      <TaskDrawer
        taskId={openTaskId}
        onClose={() => openTask(null)}
        onUpdated={() => void project.reload()}
      />
    </div>
  )
}
