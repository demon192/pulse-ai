/** Project list with health, risk headline and next milestone. */

import { FolderKanban } from 'lucide-react'
import { Link } from 'react-router-dom'

import { HealthBadge } from '@/components/domain/labels'
import { PageHeader } from '@/layouts/AppShell'
import {
  Badge,
  Card,
  CardBody,
  EmptyState,
  ErrorState,
  LoadingBlock,
  ProgressBar,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { formatDate, formatDayCount } from '@/lib/format'
import { api } from '@/services/api'

export function Projects() {
  const projects = useAsync(() => api.projects(), [])

  if (projects.initialLoading) {
    return (
      <Card>
        <LoadingBlock label="Loading projects" rows={5} />
      </Card>
    )
  }
  if (projects.error || !projects.data) {
    return <ErrorState message={projects.error ?? 'No data.'} onRetry={projects.reload} />
  }

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Health, milestones and the reason each project needs attention."
      />
      {projects.data.length === 0 ? (
        <Card>
          <EmptyState
            icon={<FolderKanban className="size-8" />}
            title="No projects"
            description="You are not authorised on any project yet."
          />
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {projects.data.map(({ project, manager_name: managerName, health }) => (
            <Link key={project.id} to={`/projects/${project.id}`} className="group">
              <Card className="h-full transition-colors group-hover:border-navy-300">
                <CardBody className="flex h-full flex-col gap-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-navy-900">{project.name}</h3>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {managerName} · target {formatDate(project.target_date)}
                      </p>
                    </div>
                    <HealthBadge health={health.health} score={health.health_score} />
                  </div>

                  <ProgressBar
                    value={health.health_score}
                    tone={
                      health.health === 'at_risk'
                        ? 'risk'
                        : health.health === 'needs_attention'
                          ? 'warn'
                          : 'ok'
                    }
                    label={`${project.name} health`}
                  />

                  <p className="line-clamp-2 text-sm text-slate-600">{project.description}</p>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <Stat label="Tasks" value={`${health.completed_tasks}/${health.total_tasks}`} />
                    <Stat label="Blocked" value={health.blocked_tasks} tone="risk" />
                    <Stat label="Overdue" value={health.overdue_tasks} tone="warn" />
                    <Stat label="Open requests" value={health.open_requests} />
                  </div>

                  {health.next_milestone ? (
                    <div className="mt-auto rounded-lg bg-slate-50 px-3 py-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-xs font-medium text-navy-800">
                          {health.next_milestone.name}
                        </span>
                        <Badge tone={health.next_milestone.at_risk ? 'risk' : 'ok'}>
                          {formatDayCount(health.next_milestone.days_remaining)}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate-600">{health.headline}</p>
                    </div>
                  ) : null}
                </CardBody>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: string | number
  tone?: 'risk' | 'warn'
}) {
  const highlight = typeof value === 'number' && value > 0
  return (
    <div className="flex items-baseline justify-between rounded bg-slate-50 px-2 py-1">
      <span className="text-slate-500">{label}</span>
      <span
        className={
          highlight && tone === 'risk'
            ? 'font-semibold tabular-nums text-risk-600'
            : highlight && tone === 'warn'
              ? 'font-semibold tabular-nums text-warn-600'
              : 'font-semibold tabular-nums text-navy-900'
        }
      >
        {value}
      </span>
    </div>
  )
}
