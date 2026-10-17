/**
 * Notifications.
 *
 * Reading one never changes the underlying request, task or action — that is
 * the whole point of the separation, and the page says so.
 */

import { Bell, CheckCheck } from 'lucide-react'
import { useState } from 'react'

import { PriorityBadge } from '@/components/domain/labels'
import { PageHeader } from '@/layouts/AppShell'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingBlock,
  Tabs,
} from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { formatDateTime, relativeDays, titleCase } from '@/lib/format'
import { api } from '@/services/api'

type TabId = 'unread' | 'all'

const POLL_MS = 20_000

export function Notifications() {
  const [tab, setTab] = useState<TabId>('unread')
  const [busy, setBusy] = useState<string | null>(null)
  const notifications = useAsync(() => api.notifications(), [], { pollMs: POLL_MS })

  const items = notifications.data?.notifications ?? []
  const visible = tab === 'unread' ? items.filter((item) => item.read_at === null) : items

  async function act(id: string, action: 'read' | 'resolve') {
    setBusy(id)
    try {
      const updated =
        action === 'read'
          ? await api.markNotificationRead(id)
          : await api.resolveNotification(id)
      notifications.setData(updated)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Notifications"
        description="One notification per concern. A still-unresolved item is escalated rather than repeated, and marking it read does not close the work behind it."
        actions={
          <Button size="sm" onClick={notifications.reload} loading={notifications.loading}>
            Refresh
          </Button>
        }
      />

      <Card className="overflow-hidden">
        <Tabs<TabId>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'unread', label: 'Unread', count: notifications.data?.unread_count ?? 0 },
            { id: 'all', label: 'All', count: items.length },
          ]}
        />

        {notifications.initialLoading ? <LoadingBlock label="Loading notifications" rows={5} /> : null}
        {notifications.error ? (
          <ErrorState message={notifications.error} onRetry={notifications.reload} />
        ) : null}

        {notifications.data && visible.length === 0 ? (
          <EmptyState
            icon={<Bell className="size-8" />}
            title={tab === 'unread' ? 'Nothing unread' : 'No notifications'}
          />
        ) : null}

        <ul className="divide-y divide-slate-100">
          {visible.map((notification) => (
            <li
              key={notification.id}
              className={
                notification.read_at === null ? 'bg-navy-50/40 px-5 py-3' : 'px-5 py-3'
              }
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-navy-900">{notification.title}</span>
                    <PriorityBadge priority={notification.priority} />
                    <Badge tone="neutral">{titleCase(notification.type)}</Badge>
                    {notification.escalation_count > 0 ? (
                      <Badge tone="warn">Escalated ×{notification.escalation_count}</Badge>
                    ) : null}
                  </div>
                  <p className="mt-1 text-sm text-slate-700">{notification.message}</p>
                  <p className="mt-1 text-xs text-slate-500">Why: {notification.reason}</p>
                  {notification.suggested_action ? (
                    <p className="mt-1 text-xs text-navy-600">
                      Suggested: {notification.suggested_action}
                    </p>
                  ) : null}
                  <p className="mt-1 text-xs text-slate-400">
                    {relativeDays(notification.created_at)} · {formatDateTime(notification.created_at)}
                    {notification.related_entity_id
                      ? ` · ${notification.related_entity_type} ${notification.related_entity_id}`
                      : ''}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-1.5">
                  {notification.read_at === null ? (
                    <Button
                      size="sm"
                      loading={busy === notification.id}
                      onClick={() => act(notification.id, 'read')}
                    >
                      Mark read
                    </Button>
                  ) : (
                    <span className="text-xs text-slate-400">Read</span>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    loading={busy === notification.id}
                    onClick={() => act(notification.id, 'resolve')}
                  >
                    <CheckCheck className="size-3.5" />
                    Dismiss
                  </Button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
