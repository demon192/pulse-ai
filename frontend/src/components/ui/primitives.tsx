/**
 * The shared component vocabulary.
 *
 * Deliberately small and hand-written rather than pulled from a component
 * library: every surface in the app composes these, so spacing, radii, borders
 * and type scale stay identical across pages.
 */

import clsx from 'clsx'
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react'

// --------------------------------------------------------------------------
// Surfaces
// --------------------------------------------------------------------------

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        'rounded-xl border border-slate-200 bg-white shadow-sm',
        className,
      )}
      {...props}
    />
  )
}

export function CardHeader({
  title,
  description,
  actions,
  icon,
  className,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  icon?: ReactNode
  className?: string
}) {
  return (
    <div
      className={clsx(
        'flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-5 py-4',
        className,
      )}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon ? <span className="mt-0.5 text-navy-500">{icon}</span> : null}
        <div className="min-w-0">
          <h2 className="text-sm font-semibold tracking-tight text-navy-900">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-sm text-slate-500">{description}</p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx('px-5 py-4', className)} {...props} />
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {children}
      </h3>
      {hint ? <span className="text-xs text-slate-400">{hint}</span> : null}
    </div>
  )
}

// --------------------------------------------------------------------------
// Badges
// --------------------------------------------------------------------------

export type Tone = 'neutral' | 'info' | 'ok' | 'warn' | 'risk' | 'navy'

const TONE_CLASSES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  info: 'bg-info-50 text-info-700 ring-info-200',
  ok: 'bg-ok-50 text-ok-700 ring-ok-200',
  warn: 'bg-warn-50 text-warn-700 ring-warn-200',
  risk: 'bg-risk-50 text-risk-700 ring-risk-200',
  navy: 'bg-navy-100 text-navy-800 ring-navy-200',
}

export function Badge({
  children,
  tone = 'neutral',
  className,
  title,
}: {
  children: ReactNode
  tone?: Tone
  className?: string
  title?: string
}) {
  return (
    <span
      title={title}
      className={clsx(
        'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap',
        TONE_CLASSES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

// --------------------------------------------------------------------------
// Buttons
// --------------------------------------------------------------------------

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const BUTTON_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-navy-700 text-white hover:bg-navy-800 disabled:bg-navy-300 disabled:text-navy-100',
  secondary:
    'bg-white text-navy-800 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:text-slate-400',
  ghost: 'text-navy-700 hover:bg-navy-50 disabled:text-slate-400',
  danger: 'bg-risk-600 text-white hover:bg-risk-700 disabled:bg-risk-200',
}

export function Button({
  variant = 'secondary',
  size = 'md',
  className,
  loading = false,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: 'sm' | 'md'
  loading?: boolean
}) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors',
        'disabled:cursor-not-allowed',
        size === 'sm' ? 'px-2.5 py-1.5 text-xs' : 'px-3.5 py-2 text-sm',
        BUTTON_CLASSES[variant],
        className,
      )}
      disabled={props.disabled || loading}
      {...props}
    >
      {loading ? (
        <span
          aria-hidden
          className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      ) : null}
      {children}
    </button>
  )
}

// --------------------------------------------------------------------------
// States
// --------------------------------------------------------------------------

export function LoadingBlock({ label = 'Loading', rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="space-y-2 px-5 py-4" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="h-4 animate-pulse rounded bg-slate-100"
          style={{ width: `${100 - index * 12}%` }}
        />
      ))}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-5 py-10 text-center">
      {icon ? <span className="text-slate-300">{icon}</span> : null}
      <p className="text-sm font-medium text-navy-800">{title}</p>
      {description ? (
        <p className="max-w-sm text-sm text-slate-500">{description}</p>
      ) : null}
      {action}
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="m-5 rounded-lg border border-risk-200 bg-risk-50 px-4 py-3">
      <p className="text-sm font-medium text-risk-700">Something went wrong</p>
      <p className="mt-1 text-sm text-risk-600">{message}</p>
      {onRetry ? (
        <Button size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  )
}

export function InlineError({ message }: { message: string }) {
  return (
    <p className="rounded-md bg-risk-50 px-3 py-2 text-sm text-risk-700" role="alert">
      {message}
    </p>
  )
}

// --------------------------------------------------------------------------
// Data display
// --------------------------------------------------------------------------

export function MetricTile({
  label,
  value,
  tone = 'neutral',
  hint,
  onClick,
  icon,
}: {
  label: string
  value: number | string
  tone?: Tone
  hint?: string
  onClick?: () => void
  icon?: ReactNode
}) {
  const interactive = Boolean(onClick)
  const Element = interactive ? 'button' : 'div'
  return (
    <Element
      onClick={onClick}
      className={clsx(
        'rounded-xl border border-slate-200 bg-white px-4 py-3 text-left shadow-sm',
        interactive && 'transition-colors hover:border-navy-300 hover:bg-navy-50/40',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {label}
        </span>
        {icon ? <span className="text-slate-300">{icon}</span> : null}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span
          className={clsx(
            'text-2xl font-semibold tabular-nums',
            tone === 'risk' && 'text-risk-600',
            tone === 'warn' && 'text-warn-600',
            tone === 'ok' && 'text-ok-600',
            (tone === 'neutral' || tone === 'info' || tone === 'navy') && 'text-navy-900',
          )}
        >
          {value}
        </span>
        {hint ? <span className="text-xs text-slate-500">{hint}</span> : null}
      </div>
    </Element>
  )
}

export function ProgressBar({
  value,
  tone = 'navy',
  label,
}: {
  value: number
  tone?: Tone
  label?: string
}) {
  const clamped = Math.max(0, Math.min(100, value))
  const fill: Record<Tone, string> = {
    neutral: 'bg-slate-400',
    info: 'bg-info-600',
    ok: 'bg-ok-600',
    warn: 'bg-warn-600',
    risk: 'bg-risk-600',
    navy: 'bg-navy-600',
  }
  return (
    <div
      className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100"
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div className={clsx('h-full rounded-full', fill[tone])} style={{ width: `${clamped}%` }} />
    </div>
  )
}

export function KeyValue({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-navy-900">{children}</dd>
    </div>
  )
}

export function Avatar({ name, size = 'md' }: { name: string; size?: 'sm' | 'md' }) {
  const letters = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('')
  return (
    <span
      className={clsx(
        'inline-flex shrink-0 items-center justify-center rounded-full bg-navy-100 font-semibold text-navy-700',
        size === 'sm' ? 'size-6 text-[10px]' : 'size-8 text-xs',
      )}
      aria-hidden
    >
      {letters}
    </span>
  )
}

// --------------------------------------------------------------------------
// Forms
// --------------------------------------------------------------------------

export function Field({
  label,
  hint,
  error,
  required,
  children,
}: {
  label: string
  hint?: string
  error?: string
  required?: boolean
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-navy-800">
        {label}
        {required ? <span className="ml-0.5 text-risk-600">*</span> : null}
      </span>
      {hint ? <span className="mt-0.5 block text-xs text-slate-500">{hint}</span> : null}
      <div className="mt-1.5">{children}</div>
      {error ? <span className="mt-1 block text-xs text-risk-600">{error}</span> : null}
    </label>
  )
}

export const inputClasses =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-navy-900 ' +
  'placeholder:text-slate-400 focus:border-navy-500 focus:ring-2 focus:ring-navy-100 ' +
  'disabled:bg-slate-50 disabled:text-slate-500'

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: T; label: string; count?: number }[]
  active: T
  onChange: (id: T) => void
}) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-slate-200 px-2 scrollbar-thin">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          aria-current={tab.id === active}
          className={clsx(
            '-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
            tab.id === active
              ? 'border-navy-700 text-navy-800'
              : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-navy-700',
          )}
        >
          {tab.label}
          {tab.count !== undefined ? (
            <span
              className={clsx(
                'ml-1.5 rounded px-1.5 py-0.5 text-xs tabular-nums',
                tab.id === active ? 'bg-navy-100 text-navy-800' : 'bg-slate-100 text-slate-600',
              )}
            >
              {tab.count}
            </span>
          ) : null}
        </button>
      ))}
    </div>
  )
}

export function Drawer({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  width = 'md',
}: {
  open: boolean
  onClose: () => void
  title: ReactNode
  description?: ReactNode
  children: ReactNode
  footer?: ReactNode
  width?: 'md' | 'lg'
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-navy-950/40"
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        className={clsx(
          'relative flex h-full w-full flex-col bg-slate-50 shadow-2xl',
          width === 'lg' ? 'sm:max-w-3xl' : 'sm:max-w-xl',
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-navy-900">{title}</h2>
            {description ? (
              <p className="mt-0.5 text-sm text-slate-500">{description}</p>
            ) : null}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            Close
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 scrollbar-thin">{children}</div>
        {footer ? (
          <div className="border-t border-slate-200 bg-white px-5 py-3">{footer}</div>
        ) : null}
      </div>
    </div>
  )
}
