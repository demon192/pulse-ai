/**
 * Support requests.
 *
 * Engineers raise them here and watch their status; managers respond, delegate
 * and resolve. A request stays listed until it is resolved or cancelled.
 */

import { LifeBuoy, Plus } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { NewRequestDrawer } from '@/components/domain/NewRequestDrawer'
import { RequestDrawer } from '@/components/domain/RequestDrawer'
import { RequestRow } from '@/components/domain/RequestRow'
import { PageHeader } from '@/layouts/AppShell'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingBlock,
  Tabs,
  inputClasses,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { useSession } from '@/hooks/useSession'
import { api } from '@/services/api'
import type { RequestCategory, SupportRequestView } from '@/types/api'

type TabId = 'open' | 'resolved' | 'all'

const CATEGORIES: (RequestCategory | '')[] = [
  '',
  'approval',
  'decision',
  'blocker',
  'one_on_one',
  'progress_update',
  'other',
]

export function Requests() {
  const { session } = useSession()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState<TabId>('open')
  const [category, setCategory] = useState<RequestCategory | ''>('')
  const [projectId, setProjectId] = useState('')
  const [selected, setSelected] = useState<SupportRequestView | null>(null)

  const requests = useAsync(() => api.requests({ include_closed: true }), [])
  const projects = useAsync(() => api.projects(), [])

  const showNew = searchParams.get('new') === '1'
  const isManager = session?.user.role === 'manager'

  const filtered = useMemo(() => {
    const items = requests.data ?? []
    return items.filter((view) => {
      const { request } = view
      const isOpen = !['resolved', 'cancelled'].includes(request.status)
      if (tab === 'open' && !isOpen) return false
      if (tab === 'resolved' && isOpen) return false
      if (category && request.category !== category) return false
      if (projectId && request.project_id !== projectId) return false
      return true
    })
  }, [requests.data, tab, category, projectId])

  const counts = useMemo(() => {
    const items = requests.data ?? []
    const open = items.filter(
      (view) => !['resolved', 'cancelled'].includes(view.request.status),
    ).length
    return { open, resolved: items.length - open, all: items.length }
  }, [requests.data])

  function setNewOpen(open: boolean) {
    const next = new URLSearchParams(searchParams)
    if (open) next.set('new', '1')
    else next.delete('new')
    setSearchParams(next, { replace: true })
  }

  return (
    <div>
      <PageHeader
        title="Support requests"
        description={
          isManager
            ? 'Everything your engineers have asked for, with the work it affects.'
            : 'Ask for an approval, a decision, help with a blocker, or time with your manager.'
        }
        actions={
          <Button variant="primary" size="sm" onClick={() => setNewOpen(true)}>
            <Plus className="size-4" />
            New request
          </Button>
        }
      />

      <Card className="overflow-hidden">
        <Tabs<TabId>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'open', label: 'Open', count: counts.open },
            { id: 'resolved', label: 'Closed', count: counts.resolved },
            { id: 'all', label: 'All', count: counts.all },
          ]}
        />

        <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-slate-50 px-5 py-3">
          <label className="min-w-40 flex-1">
            <span className="sr-only">Filter by category</span>
            <select
              className={inputClasses}
              value={category}
              onChange={(event) => setCategory(event.target.value as RequestCategory | '')}
            >
              {CATEGORIES.map((value) => (
                <option key={value || 'all'} value={value}>
                  {value ? value.replace(/_/g, ' ') : 'All categories'}
                </option>
              ))}
            </select>
          </label>
          <label className="min-w-40 flex-1">
            <span className="sr-only">Filter by project</span>
            <select
              className={inputClasses}
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
            >
              <option value="">All projects</option>
              {(projects.data ?? []).map((item) => (
                <option key={item.project.id} value={item.project.id}>
                  {item.project.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        {requests.initialLoading ? <LoadingBlock label="Loading requests" rows={5} /> : null}
        {requests.error ? <ErrorState message={requests.error} onRetry={requests.reload} /> : null}

        {requests.data && filtered.length === 0 ? (
          <EmptyState
            icon={<LifeBuoy className="size-8" />}
            title="No requests match this view"
            description={
              tab === 'open'
                ? 'Nothing is waiting. Raise a request as soon as something blocks you.'
                : undefined
            }
          />
        ) : null}

        {filtered.length > 0 ? (
          <ul className="divide-y divide-slate-100">
            {filtered.map((view) => (
              <RequestRow
                key={view.request.id}
                view={view}
                onOpen={setSelected}
                showEngineer={isManager}
              />
            ))}
          </ul>
        ) : null}
      </Card>

      <NewRequestDrawer
        open={showNew}
        onClose={() => setNewOpen(false)}
        projects={(projects.data ?? []).map((item) => ({
          id: item.project.id,
          name: item.project.name,
        }))}
        onCreated={() => {
          setNewOpen(false)
          void requests.reload()
        }}
      />

      <RequestDrawer
        view={selected}
        onClose={() => setSelected(null)}
        onChanged={() => void requests.reload()}
      />
    </div>
  )
}
