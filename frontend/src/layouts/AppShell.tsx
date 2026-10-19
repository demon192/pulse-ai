/**
 * Application frame: brand, role-aware navigation, persona switcher and the
 * notification bell. Everything a page needs around it, and nothing a page
 * has to re-implement.
 */

import clsx from 'clsx'
import {
  Activity,
  Bell,
  Briefcase,
  ClipboardCheck,
  FolderKanban,
  Inbox,
  LifeBuoy,
  Menu,
  UserMinus,
  X,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

import { DemoDataBadge } from '@/components/domain/labels'
import { Avatar, Badge } from '@/components/ui/primitives'
import { useAsync } from '@/hooks/useAsync'
import { useSession } from '@/hooks/useSession'
import { api } from '@/services/api'
import type { Role } from '@/types/api'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
  roles: Role[]
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Overview', icon: <Activity className="size-4" />, roles: ['manager', 'engineer'] },
  { to: '/projects', label: 'Projects', icon: <FolderKanban className="size-4" />, roles: ['manager', 'engineer'] },
  { to: '/my-work', label: 'My Work', icon: <Briefcase className="size-4" />, roles: ['engineer'] },
  { to: '/requests', label: 'Support Requests', icon: <LifeBuoy className="size-4" />, roles: ['manager', 'engineer'] },
  { to: '/inbox', label: 'Action Inbox', icon: <Inbox className="size-4" />, roles: ['manager'] },
  { to: '/handovers', label: 'Handovers', icon: <UserMinus className="size-4" />, roles: ['manager', 'engineer'] },
  { to: '/notifications', label: 'Notifications', icon: <Bell className="size-4" />, roles: ['manager', 'engineer'] },
]

/** Notifications are polled; the MVP does not need a socket for this. */
const NOTIFICATION_POLL_MS = 20_000

export function AppShell({ children }: { children: ReactNode }) {
  const { session, switchPersona, signOut } = useSession()
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const unread = useAsync(() => api.notifications({ unread_only: true }), [session?.user.id], {
    pollMs: NOTIFICATION_POLL_MS,
    enabled: Boolean(session),
  })

  if (!session) return null
  const role = session.user.role
  const items = NAV_ITEMS.filter((item) => item.roles.includes(role))
  const unreadCount = unread.data?.unread_count ?? 0

  const navLinks = (
    <nav className="space-y-0.5">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          onClick={() => setMobileNavOpen(false)}
          className={({ isActive }) =>
            clsx(
              'flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-navy-800 text-white'
                : 'text-navy-100/80 hover:bg-navy-800/60 hover:text-white',
            )
          }
        >
          <span className="flex items-center gap-2.5">
            {item.icon}
            {item.label}
          </span>
          {item.to === '/notifications' && unreadCount > 0 ? (
            <span className="rounded-full bg-risk-600 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-white">
              {unreadCount}
            </span>
          ) : null}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      {/* Sidebar */}
      <aside className="hidden h-screen flex-col bg-navy-900 px-4 py-5 lg:sticky lg:top-0 lg:flex">
        <BrandMark />
        <div className="mt-6 flex-1">{navLinks}</div>
        <SessionFooter
          personas={session.dev_personas}
          currentUserId={session.user.id}
          onSwitch={switchPersona}
          authMode={session.auth_mode}
          environment={session.environment}
          userEmail={session.user.email}
          onSignOut={signOut}
        />
      </aside>

      {/* Mobile header */}
      <div className="flex items-center justify-between bg-navy-900 px-4 py-3 lg:hidden">
        <BrandMark compact />
        <div className="flex items-center gap-2">
          <NavLink
            to="/notifications"
            className="relative rounded-lg p-2 text-navy-100 hover:bg-navy-800"
            aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`}
          >
            <Bell className="size-5" />
            {unreadCount > 0 ? (
              <span className="absolute top-1 right-1 size-2 rounded-full bg-risk-600" />
            ) : null}
          </NavLink>
          <button
            className="rounded-lg p-2 text-navy-100 hover:bg-navy-800"
            onClick={() => setMobileNavOpen((open) => !open)}
            aria-label="Toggle navigation"
            aria-expanded={mobileNavOpen}
          >
            {mobileNavOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>
      {mobileNavOpen ? (
        <div className="bg-navy-900 px-4 pb-4 lg:hidden">
          {navLinks}
          <div className="mt-4">
            <SessionFooter
              personas={session.dev_personas}
              currentUserId={session.user.id}
              onSwitch={switchPersona}
              authMode={session.auth_mode}
              environment={session.environment}
              userEmail={session.user.email}
              onSignOut={signOut}
            />
          </div>
        </div>
      ) : null}

      {/* Main */}
      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur sm:px-6">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              {items.find((item) => item.to === location.pathname)?.label ?? 'TeamPulse'}
            </p>
            <h1 className="truncate text-lg font-semibold text-navy-900">
              {session.user.name}
              <span className="ml-2 text-sm font-normal text-slate-500">
                {session.user.title ?? session.user.role}
              </span>
            </h1>
          </div>
          <div className="flex items-center gap-2">
            {session.demo_data_mode ? <DemoDataBadge /> : null}
            <Badge tone={session.ai_configured ? 'navy' : 'warn'}>
              {session.ai_configured ? `Gemini: ${session.ai_model}` : 'Gemini not configured'}
            </Badge>
          </div>
        </header>
        <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6">{children}</main>
      </div>
    </div>
  )
}

function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex size-8 items-center justify-center rounded-lg bg-navy-600 text-white">
        <ClipboardCheck className="size-5" />
      </span>
      <div className="leading-tight">
        <p className="text-sm font-semibold text-white">TeamPulse AI</p>
        {!compact ? (
          <p className="text-[11px] text-navy-300">Never lose track of what your team needs</p>
        ) : null}
      </div>
    </div>
  )
}

function SessionFooter({
  personas,
  currentUserId,
  onSwitch,
  authMode,
  environment,
  userEmail,
  onSignOut,
}: {
  personas: { id: string; name: string; role: Role; title: string | null }[]
  currentUserId: string
  onSwitch: (userId: string) => Promise<void>
  authMode: string
  environment: string
  userEmail: string
  onSignOut: () => Promise<void>
}) {
  const [switching, setSwitching] = useState(false)
  if (personas.length === 0) {
    return (
      <div className="rounded-lg bg-navy-800/60 px-3 py-2">
        <p className="truncate text-xs text-navy-200" title={userEmail}>
          {userEmail}
        </p>
        <p className="mt-0.5 text-[11px] text-navy-300/80">
          Signed in with {authMode} authentication.
        </p>
        {authMode === 'firebase' ? (
          <button
            type="button"
            onClick={() => void onSignOut()}
            className="mt-2 w-full rounded-md border border-navy-700 px-2 py-1.5 text-xs text-navy-100 hover:bg-navy-800"
          >
            Sign out
          </button>
        ) : null}
      </div>
    )
  }
  return (
    <div className="rounded-lg bg-navy-800/60 p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-navy-300">
        {environment === 'production' ? 'Demo personas' : 'Development personas'}
      </p>
      <p className="mt-1 text-[11px] text-navy-300/80">
        {environment === 'production'
          ? 'Persona switching is enabled for this judge demo.'
          : 'Local demo only.'}
      </p>
      <label className="mt-2 block">
        <span className="sr-only">Switch persona</span>
        <select
          value={currentUserId}
          disabled={switching}
          onChange={async (event) => {
            setSwitching(true)
            try {
              await onSwitch(event.target.value)
            } finally {
              setSwitching(false)
            }
          }}
          className="w-full rounded-md border border-navy-700 bg-navy-900 px-2 py-1.5 text-xs text-white"
        >
          {personas.map((persona) => (
            <option key={persona.id} value={persona.id}>
              {persona.name} — {persona.title ?? persona.role}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-xl font-semibold tracking-tight text-navy-900">{title}</h2>
        {description ? <p className="mt-1 max-w-2xl text-sm text-slate-600">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function UserChip({ name, subtitle }: { name: string; subtitle?: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Avatar name={name} size="sm" />
      <span className="min-w-0">
        <span className="block truncate text-sm text-navy-900">{name}</span>
        {subtitle ? <span className="block truncate text-xs text-slate-500">{subtitle}</span> : null}
      </span>
    </span>
  )
}
