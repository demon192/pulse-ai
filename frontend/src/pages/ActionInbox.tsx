/**
 * The manager action inbox.
 *
 * Grouped by the distinctions a manager actually makes: urgent and
 * time-sensitive, blocked work, approvals, support, routine follow-ups.
 */

import { Inbox } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ActionDrawer } from '@/components/domain/ActionDrawer'
import { ActionInboxRow } from '@/components/domain/ActionInboxRow'
import { BUCKET_LABEL, BUCKET_TONE } from '@/components/domain/labels'
import { PageHeader } from '@/layouts/AppShell'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  LoadingBlock,
  inputClasses,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { api } from '@/services/api'
import type { ActionInboxItem, Priority } from '@/types/api'

const BUCKET_ORDER = ['urgent', 'blocked_work', 'approvals', 'support', 'routine'] as const

export function ActionInbox() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selected, setSelected] = useState<ActionInboxItem | null>(null)
  const actions = useAsync(() => api.actions(), [])
  const projects = useAsync(() => api.projects(), [])

  const bucketFilter = searchParams.get('bucket') ?? ''
  const projectFilter = searchParams.get('project') ?? ''
  const priorityFilter = (searchParams.get('priority') ?? '') as Priority | ''

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    setSearchParams(next, { replace: true })
  }

  const grouped = useMemo(() => {
    const items = (actions.data ?? []).filter((item) => {
      if (bucketFilter && item.priority_detail.bucket !== bucketFilter) return false
      if (projectFilter && item.action.project_id !== projectFilter) return false
      if (priorityFilter && item.action.priority !== priorityFilter) return false
      return true
    })
    const map = new Map<string, ActionInboxItem[]>()
    for (const bucket of BUCKET_ORDER) map.set(bucket, [])
    for (const item of items) {
      const bucket = item.priority_detail.bucket
      map.set(bucket, [...(map.get(bucket) ?? []), item])
    }
    return map
  }, [actions.data, bucketFilter, projectFilter, priorityFilter])

  const total = (actions.data ?? []).length

  return (
    <div>
      <PageHeader
        title="Action inbox"
        description="Every pending approval, question, blocker and follow-up in one place, ranked by consequence rather than by arrival time."
        actions={
          <Button size="sm" onClick={actions.reload} loading={actions.loading}>
            Refresh
          </Button>
        }
      />

      <Card className="mb-4">
        <div className="flex flex-wrap items-center gap-2 px-5 py-3">
          <label className="min-w-40 flex-1">
            <span className="sr-only">Filter by group</span>
            <select
              className={inputClasses}
              value={bucketFilter}
              onChange={(event) => setFilter('bucket', event.target.value)}
            >
              <option value="">All groups</option>
              {BUCKET_ORDER.map((bucket) => (
                <option key={bucket} value={bucket}>
                  {BUCKET_LABEL[bucket]}
                </option>
              ))}
            </select>
          </label>
          <label className="min-w-40 flex-1">
            <span className="sr-only">Filter by project</span>
            <select
              className={inputClasses}
              value={projectFilter}
              onChange={(event) => setFilter('project', event.target.value)}
            >
              <option value="">All projects</option>
              {(projects.data ?? []).map((item) => (
                <option key={item.project.id} value={item.project.id}>
                  {item.project.name}
                </option>
              ))}
            </select>
          </label>
          <label className="min-w-32 flex-1">
            <span className="sr-only">Filter by priority</span>
            <select
              className={inputClasses}
              value={priorityFilter}
              onChange={(event) => setFilter('priority', event.target.value)}
            >
              <option value="">All priorities</option>
              {(['critical', 'high', 'medium', 'low'] as Priority[]).map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      {actions.initialLoading ? (
        <Card>
          <LoadingBlock label="Loading the action inbox" rows={6} />
        </Card>
      ) : null}
      {actions.error ? <ErrorState message={actions.error} onRetry={actions.reload} /> : null}

      {actions.data && total === 0 ? (
        <Card>
          <EmptyState
            icon={<Inbox className="size-8" />}
            title="Your inbox is clear"
            description="No approvals, questions or follow-ups are waiting on you."
          />
        </Card>
      ) : null}

      <div className="space-y-4">
        {BUCKET_ORDER.map((bucket) => {
          const items = grouped.get(bucket) ?? []
          if (items.length === 0) return null
          return (
            <Card key={bucket} className="overflow-hidden">
              <CardHeader
                title={BUCKET_LABEL[bucket]}
                actions={<Badge tone={BUCKET_TONE[bucket]}>{items.length}</Badge>}
              />
              <ul className="divide-y divide-slate-100">
                {items.map((item) => (
                  <ActionInboxRow key={item.action.id} item={item} onOpen={setSelected} />
                ))}
              </ul>
            </Card>
          )
        })}
      </div>

      <ActionDrawer
        item={selected}
        onClose={() => setSelected(null)}
        onChanged={() => void actions.reload()}
      />
    </div>
  )
}
