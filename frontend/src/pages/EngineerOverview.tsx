/** Engineer workspace: my work, my blockers, my requests and their status. */

import { AlertTriangle, Ban, CalendarClock, LifeBuoy, UserMinus } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { RequestRow } from '@/components/domain/RequestRow'
import { TaskRow } from '@/components/domain/TaskRow'
import { AvailabilityBadge } from '@/components/domain/labels'
import { PageHeader } from '@/layouts/AppShell'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  LoadingBlock,
  MetricTile,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { pluralise } from '@/lib/format'
import { api } from '@/services/api'

export function EngineerOverview() {
  const navigate = useNavigate()
  const dashboard = useAsync(() => api.engineerDashboard(), [])

  if (dashboard.initialLoading) {
    return (
      <Card>
        <LoadingBlock label="Loading your workspace" rows={6} />
      </Card>
    )
  }
  if (dashboard.error || !dashboard.data) {
    return <ErrorState message={dashboard.error ?? 'No data.'} onRetry={dashboard.reload} />
  }

  const data = dashboard.data
  const { summary } = data

  return (
    <div className="space-y-6">
      <PageHeader
        title="Your workspace"
        description="Your tasks, the blockers you have reported, and the status of everything you have asked for."
        actions={
          <>
            <AvailabilityBadge status={data.availability_status} />
            <Link to="/requests?new=1">
              <Button variant="primary" size="sm">
                <LifeBuoy className="size-4" />
                Ask for support
              </Button>
            </Link>
          </>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricTile label="Open tasks" value={summary.open_tasks} onClick={() => navigate('/my-work')} />
        <MetricTile
          label="Blocked"
          value={summary.blocked_tasks}
          tone={summary.blocked_tasks > 0 ? 'risk' : 'ok'}
          icon={<Ban className="size-4" />}
          onClick={() => navigate('/my-work')}
        />
        <MetricTile
          label="Overdue"
          value={summary.overdue_tasks}
          tone={summary.overdue_tasks > 0 ? 'warn' : 'ok'}
          icon={<AlertTriangle className="size-4" />}
          onClick={() => navigate('/my-work')}
        />
        <MetricTile
          label="Awaiting a response"
          value={summary.awaiting_response}
          tone={summary.awaiting_response > 0 ? 'info' : 'ok'}
          onClick={() => navigate('/requests')}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader
              icon={<Ban className="size-4" />}
              title="My blockers"
              description="Tasks you have recorded as blocked."
              actions={
                <Link to="/requests?new=1">
                  <Button size="sm">Report a blocker</Button>
                </Link>
              }
            />
            {data.my_blockers.length === 0 ? (
              <EmptyState
                title="Nothing is blocked"
                description="Report a blocker as soon as you hit one — it is tracked until it is resolved."
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.my_blockers.map((view) => (
                  <TaskRow key={view.task.id} view={view} />
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader
              icon={<CalendarClock className="size-4" />}
              title="Upcoming deadlines"
              description="Your open tasks due within a week."
            />
            {data.upcoming_deadlines.length === 0 ? (
              <EmptyState title="No deadlines in the next 7 days" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.upcoming_deadlines.map((view) => (
                  <TaskRow key={view.task.id} view={view} />
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader
              title="My requests"
              description="Visible until resolved or cancelled, regardless of who has read what."
              actions={
                <Link to="/requests">
                  <Button size="sm">See all</Button>
                </Link>
              }
            />
            {data.my_requests.length === 0 ? (
              <EmptyState
                title="You have not raised any requests"
                description="Approvals, decisions, blockers and one-on-ones all go here."
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.my_requests.slice(0, 6).map((view) => (
                  <RequestRow key={view.request.id} view={view} />
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader
              icon={<UserMinus className="size-4" />}
              title="Availability and handover"
              description="Record planned or emergency unavailability so your work can be covered."
              actions={
                <Link to="/handovers">
                  <Button size="sm" variant="primary">
                    Open handovers
                  </Button>
                </Link>
              }
            />
            {data.my_handovers.length === 0 && data.assigned_to_me.length === 0 ? (
              <EmptyState
                title="No handovers"
                description="TeamPulse only records dates and affected work — never a reason."
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.my_handovers.map((view) => (
                  <li key={view.handover.id} className="px-5 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-medium text-navy-900">Your handover</span>
                      <Badge tone={view.handover.manager_approval_status === 'approved' ? 'ok' : 'warn'}>
                        {view.handover.handover_status.replace(/_/g, ' ')}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-600">
                      {pluralise(view.handover.affected_task_ids.length, 'affected task')}
                      {view.selected_backup_name ? ` · cover: ${view.selected_backup_name}` : ''}
                    </p>
                  </li>
                ))}
                {data.assigned_to_me.map((view) => (
                  <li key={view.handover.id} className="px-5 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-medium text-navy-900">
                        Cover for {view.unavailable_user_name}
                      </span>
                      <Badge tone={view.can_accept ? 'warn' : 'ok'}>
                        {view.can_accept ? 'Needs your acceptance' : view.handover.handover_status}
                      </Badge>
                    </div>
                    <Link
                      to="/handovers"
                      className="mt-1 inline-block text-xs font-medium text-navy-600 hover:underline"
                    >
                      Read the brief
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader title="Recent notifications" />
            {data.recent_notifications.length === 0 ? (
              <EmptyState title="Nothing new" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.recent_notifications.slice(0, 6).map((notification) => (
                  <li key={notification.id} className="px-5 py-2.5">
                    <p className="text-sm text-navy-900">{notification.title}</p>
                    <p className="text-xs text-slate-500">{notification.message}</p>
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
