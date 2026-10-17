/**
 * Domain-specific labels.
 *
 * One mapping per concept so a priority, a status or a health rating looks the
 * same wherever it appears.
 */

import {
  AlertTriangle,
  BadgeCheck,
  Ban,
  CalendarClock,
  CheckCircle2,
  CircleDashed,
  CircleDot,
  Clock,
  Eye,
  HelpCircle,
  Link2,
  Lock,
  ShieldAlert,
  Sparkles,
  UserMinus,
  UserX,
} from 'lucide-react'
import type { ReactNode } from 'react'

import { Badge, type Tone } from '@/components/ui/primitives'
import { titleCase } from '@/lib/format'
import type {
  ActionStatus,
  ActionType,
  AIMeta,
  AvailabilityStatus,
  EvidenceKind,
  Priority,
  ProjectHealth,
  RequestCategory,
  RequestStatus,
  RiskKind,
  TaskStatus,
} from '@/types/api'

export const PRIORITY_TONE: Record<Priority, Tone> = {
  low: 'neutral',
  medium: 'info',
  high: 'warn',
  critical: 'risk',
}

export const TASK_STATUS_TONE: Record<TaskStatus, Tone> = {
  not_started: 'neutral',
  in_progress: 'info',
  blocked: 'risk',
  in_review: 'navy',
  completed: 'ok',
}

const TASK_STATUS_ICON: Record<TaskStatus, ReactNode> = {
  not_started: <CircleDashed className="size-3" />,
  in_progress: <CircleDot className="size-3" />,
  blocked: <Ban className="size-3" />,
  in_review: <Eye className="size-3" />,
  completed: <CheckCircle2 className="size-3" />,
}

export const HEALTH_TONE: Record<ProjectHealth, Tone> = {
  on_track: 'ok',
  needs_attention: 'warn',
  at_risk: 'risk',
}

export const REQUEST_STATUS_TONE: Record<RequestStatus, Tone> = {
  open: 'warn',
  acknowledged: 'info',
  in_progress: 'info',
  resolved: 'ok',
  cancelled: 'neutral',
}

export const ACTION_STATUS_TONE: Record<ActionStatus, Tone> = {
  open: 'warn',
  acknowledged: 'info',
  in_progress: 'info',
  resolved: 'ok',
  cancelled: 'neutral',
}

export const AVAILABILITY_TONE: Record<AvailabilityStatus, Tone> = {
  available: 'ok',
  limited: 'warn',
  on_leave: 'neutral',
  unavailable: 'risk',
}

export const REQUEST_CATEGORY_LABEL: Record<RequestCategory, string> = {
  blocker: 'Blocker',
  decision: 'Decision needed',
  approval: 'Approval',
  one_on_one: 'One-on-one',
  progress_update: 'Progress update',
  other: 'Other',
}

export const ACTION_TYPE_ICON: Record<ActionType, ReactNode> = {
  approval: <BadgeCheck className="size-4" />,
  question: <HelpCircle className="size-4" />,
  support_request: <HelpCircle className="size-4" />,
  follow_up: <Clock className="size-4" />,
  deadline: <CalendarClock className="size-4" />,
  overdue_task: <AlertTriangle className="size-4" />,
  blocker: <Ban className="size-4" />,
  handover_approval: <UserMinus className="size-4" />,
  one_on_one: <Clock className="size-4" />,
}

export const RISK_KIND_LABEL: Record<RiskKind, string> = {
  overdue_task: 'Overdue task',
  blocked_task: 'Blocked task',
  blocked_dependency_chain: 'Blocked dependency chain',
  pending_approval_blocking_work: 'Pending decision blocking work',
  milestone_at_risk: 'Milestone at risk',
  unassigned_critical_work: 'Unassigned critical work',
  coverage_gap: 'Coverage gap',
}

export const RISK_KIND_ICON: Record<RiskKind, ReactNode> = {
  overdue_task: <CalendarClock className="size-4" />,
  blocked_task: <Ban className="size-4" />,
  blocked_dependency_chain: <Link2 className="size-4" />,
  pending_approval_blocking_work: <BadgeCheck className="size-4" />,
  milestone_at_risk: <ShieldAlert className="size-4" />,
  unassigned_critical_work: <UserX className="size-4" />,
  coverage_gap: <UserMinus className="size-4" />,
}

export const BUCKET_LABEL: Record<string, string> = {
  urgent: 'Urgent and time-sensitive',
  blocked_work: 'Blocked work',
  approvals: 'Approvals',
  support: 'Support requests',
  routine: 'Routine follow-ups',
}

export const BUCKET_TONE: Record<string, Tone> = {
  urgent: 'risk',
  blocked_work: 'warn',
  approvals: 'navy',
  support: 'info',
  routine: 'neutral',
}

// --------------------------------------------------------------------------
// Components
// --------------------------------------------------------------------------

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <Badge tone={PRIORITY_TONE[priority]} title={`Recorded priority: ${priority}`}>
      {titleCase(priority)}
    </Badge>
  )
}

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return (
    <Badge tone={TASK_STATUS_TONE[status]}>
      {TASK_STATUS_ICON[status]}
      {titleCase(status)}
    </Badge>
  )
}

export function HealthBadge({ health, score }: { health: ProjectHealth; score?: number }) {
  return (
    <Badge tone={HEALTH_TONE[health]} title={score !== undefined ? `Health score ${score}/100` : undefined}>
      {titleCase(health)}
      {score !== undefined ? <span className="tabular-nums opacity-70">{score}</span> : null}
    </Badge>
  )
}

export function AvailabilityBadge({ status }: { status: AvailabilityStatus }) {
  return <Badge tone={AVAILABILITY_TONE[status]}>{titleCase(status)}</Badge>
}

export function SeverityBadge({ severity }: { severity: number }) {
  const tone: Tone = severity >= 70 ? 'risk' : severity >= 45 ? 'warn' : 'neutral'
  return (
    <Badge tone={tone} title="Severity is computed by deterministic rules, not by the model.">
      Severity {severity}
    </Badge>
  )
}

/**
 * Shows where an AI answer came from, so a manager can tell a model-generated
 * summary from a deterministic restatement of stored records.
 */
export function AIProvenance({ meta, className }: { meta: AIMeta; className?: string }) {
  const label =
    meta.source === 'gemini'
      ? `Generated by ${meta.model ?? 'Gemini'}`
      : meta.source === 'cache'
        ? 'Cached summary'
        : 'Generated without the model'
  return (
    <div className={className}>
      <Badge tone={meta.degraded ? 'warn' : 'navy'}>
        <Sparkles className="size-3" />
        {label}
      </Badge>
      {meta.notes.length > 0 ? (
        <ul className="mt-2 space-y-1 text-xs text-slate-500">
          {meta.notes.map((note) => (
            <li key={note} className="flex gap-1.5">
              <Lock className="mt-0.5 size-3 shrink-0 text-slate-400" aria-hidden />
              <span>{note}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

const EVIDENCE_LABEL: Record<EvidenceKind, string> = {
  verified_fact: 'Verified fact',
  rule_derived: 'Rule-derived',
  hypothesis: 'Hypothesis',
  recommendation: 'Recommendation',
}

const EVIDENCE_TONE: Record<EvidenceKind, Tone> = {
  verified_fact: 'ok',
  rule_derived: 'navy',
  hypothesis: 'warn',
  recommendation: 'info',
}

export function EvidenceKindBadge({ kind }: { kind: EvidenceKind }) {
  return (
    <Badge
      tone={EVIDENCE_TONE[kind]}
      title="How this statement was derived: a stored fact, a rules-engine finding, an inference, or a suggested action."
    >
      {EVIDENCE_LABEL[kind]}
    </Badge>
  )
}

export function DemoDataBadge() {
  return (
    <Badge tone="neutral" title="This workspace contains synthetic data for demonstration.">
      Demo data
    </Badge>
  )
}
