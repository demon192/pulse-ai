/** The engineer's full task list. */

import { useState } from 'react'

import { TaskDrawer } from '@/components/domain/TaskDrawer'
import { TaskRow } from '@/components/domain/TaskRow'
import { PageHeader } from '@/layouts/AppShell'
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingBlock,
  Tabs,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { api } from '@/services/api'

type TabId = 'open' | 'blocked' | 'completed'

export function MyWork() {
  const [tab, setTab] = useState<TabId>('open')
  const [openTaskId, setOpenTaskId] = useState<string | null>(null)
  const dashboard = useAsync(() => api.engineerDashboard(), [])

  if (dashboard.initialLoading) {
    return (
      <Card>
        <LoadingBlock label="Loading your tasks" rows={5} />
      </Card>
    )
  }
  if (dashboard.error || !dashboard.data) {
    return <ErrorState message={dashboard.error ?? 'No data.'} onRetry={dashboard.reload} />
  }

  const all = dashboard.data.my_tasks
  const open = all.filter((view) => view.task.status !== 'completed')
  const blocked = all.filter((view) => view.task.status === 'blocked')
  const completed = all.filter((view) => view.task.status === 'completed')
  const visible = tab === 'open' ? open : tab === 'blocked' ? blocked : completed

  return (
    <div>
      <PageHeader
        title="My work"
        description="Update status, record the next step, and report a blocker so it gets tracked."
      />
      <Card className="overflow-hidden">
        <Tabs<TabId>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'open', label: 'Open', count: open.length },
            { id: 'blocked', label: 'Blocked', count: blocked.length },
            { id: 'completed', label: 'Completed', count: completed.length },
          ]}
        />
        {visible.length === 0 ? (
          <EmptyState title="Nothing here" description="No tasks match this view." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {visible.map((view) => (
              <TaskRow key={view.task.id} view={view} onOpen={setOpenTaskId} showProject />
            ))}
          </ul>
        )}
      </Card>

      <TaskDrawer
        taskId={openTaskId}
        onClose={() => setOpenTaskId(null)}
        onUpdated={() => void dashboard.reload()}
      />
    </div>
  )
}
