/** Shared formatting. One definition per concept, used everywhere. */

const DAY_MS = 86_400_000

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** "in 3 days" / "2 days ago", from an absolute timestamp. */
export function relativeDays(value: string | null | undefined): string {
  if (!value) return '—'
  const days = Math.round((new Date(value).getTime() - Date.now()) / DAY_MS)
  if (days === 0) return 'today'
  if (days === 1) return 'tomorrow'
  if (days === -1) return 'yesterday'
  return days > 0 ? `in ${days} days` : `${Math.abs(days)} days ago`
}

/** "3 days" / "2 days overdue", from a pre-computed day count. */
export function formatDayCount(days: number | null | undefined): string {
  if (days === null || days === undefined) return 'No due date'
  const rounded = Math.round(days)
  if (rounded < 0) return `${Math.abs(rounded)} day${Math.abs(rounded) === 1 ? '' : 's'} overdue`
  if (rounded === 0) return 'Due today'
  return `${rounded} day${rounded === 1 ? '' : 's'} left`
}

export function titleCase(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('')
}

export function pluralise(count: number, singular: string, plural?: string): string {
  return `${count} ${count === 1 ? singular : (plural ?? `${singular}s`)}`
}
