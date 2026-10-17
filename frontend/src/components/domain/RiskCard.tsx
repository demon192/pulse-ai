/**
 * A delivery-risk finding.
 *
 * The finding, its severity and its evidence all come from the deterministic
 * rules engine. The plain-language explanation is the only part Gemini writes,
 * and it is labelled as such.
 */

import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react'
import { useState } from 'react'

import { AIProvenance, RISK_KIND_ICON, RISK_KIND_LABEL, SeverityBadge } from '@/components/domain/labels'
import { Badge, Button, Card, InlineError } from '@/components/ui/primitives'
import { pluralise } from '@/lib/format'
import { api } from '@/services/api'
import type { AIEnvelope, RiskExplanationData, RiskFinding } from '@/types/api'

export function RiskCard({
  finding,
  defaultOpen = false,
  onOpenTask,
}: {
  finding: RiskFinding
  defaultOpen?: boolean
  onOpenTask?: (taskId: string) => void
}) {
  const [open, setOpen] = useState(defaultOpen)
  const [explanation, setExplanation] = useState<AIEnvelope<RiskExplanationData> | null>(null)
  const [explaining, setExplaining] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function explain() {
    setExplaining(true)
    setError(null)
    try {
      setExplanation(await api.riskExplanation(finding.project_id, finding.id))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not generate an explanation.')
    } finally {
      setExplaining(false)
    }
  }

  return (
    <Card className="overflow-hidden">
      <button
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="mt-0.5 text-navy-500">{RISK_KIND_ICON[finding.kind]}</span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-navy-900">{finding.title}</span>
            <SeverityBadge severity={finding.severity} />
            <Badge tone="neutral">{RISK_KIND_LABEL[finding.kind]}</Badge>
          </span>
          <span className="mt-1 block text-sm text-slate-600">{finding.summary}</span>
          {finding.downstream_task_ids.length > 0 ? (
            <span className="mt-1 block text-xs text-warn-700">
              Blocks {pluralise(finding.downstream_task_ids.length, 'downstream task')}
            </span>
          ) : null}
        </span>
        <span className="mt-0.5 text-slate-400">
          {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
        </span>
      </button>

      {open ? (
        <div className="space-y-4 border-t border-slate-200 bg-slate-50/60 px-4 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Evidence
            </p>
            <ul className="mt-2 space-y-2">
              {finding.evidence.map((item, index) => (
                <li key={`${item.entity_id ?? item.label}-${index}`} className="text-sm">
                  <span className="font-medium text-navy-900">{item.label}</span>
                  <span className="text-slate-600"> — {item.detail}</span>
                  {item.entity_type === 'task' && item.entity_id && onOpenTask ? (
                    <button
                      className="ml-1.5 text-xs font-medium text-navy-600 underline-offset-2 hover:underline"
                      onClick={() => onOpenTask(item.entity_id as string)}
                    >
                      Open task
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>

          {finding.suggested_actions.length > 0 ? (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Suggested actions
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {finding.suggested_actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div>
            {explanation ? (
              <div className="rounded-lg border border-navy-200 bg-white p-3">
                <AIProvenance meta={explanation.meta} className="mb-2" />
                <p className="text-sm text-navy-900">{explanation.data.explanation}</p>
                {explanation.data.statements.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-xs text-slate-600">
                    {explanation.data.statements.map((statement, index) => (
                      <li key={index}>
                        <span className="font-medium">{statement.evidence_kind}:</span>{' '}
                        {statement.text}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : (
              <Button size="sm" onClick={explain} loading={explaining}>
                <Sparkles className="size-3.5" />
                Explain this risk
              </Button>
            )}
            {error ? <div className="mt-2"><InlineError message={error} /></div> : null}
          </div>
        </div>
      ) : null}
    </Card>
  )
}
