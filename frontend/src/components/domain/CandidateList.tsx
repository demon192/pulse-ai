/**
 * Ranked backup candidates.
 *
 * A recommendation is not an assignment: the manager must choose, and an
 * ineligible candidate is shown with its blocking reasons and no score.
 */

import { CheckCircle2, ShieldX } from 'lucide-react'
import { useState } from 'react'

import { Badge, Button, Card, ProgressBar } from '@/components/ui/primitives'
import { titleCase } from '@/lib/format'
import type { CandidateRecommendation } from '@/types/api'

export function CandidateList({
  candidates,
  selectedId,
  onSelect,
  disabled = false,
}: {
  candidates: CandidateRecommendation[]
  selectedId?: string | null
  onSelect?: (userId: string) => void
  disabled?: boolean
}) {
  const eligible = candidates.filter((item) => item.eligible)
  const ineligible = candidates.filter((item) => !item.eligible)

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Eligible candidates ({eligible.length})
        </p>
        {eligible.length === 0 ? (
          <p className="mt-2 rounded-lg border border-warn-200 bg-warn-50 px-3 py-2 text-sm text-warn-700">
            No eligible backup candidate was found. Manual intervention is required.
          </p>
        ) : (
          <div className="mt-2 space-y-2">
            {eligible.map((candidate, index) => (
              <CandidateCard
                key={candidate.user_id}
                candidate={candidate}
                rank={index + 1}
                selected={selectedId === candidate.user_id}
                onSelect={onSelect}
                disabled={disabled}
              />
            ))}
          </div>
        )}
      </div>

      {ineligible.length > 0 ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Not assignable ({ineligible.length})
          </p>
          <div className="mt-2 space-y-2">
            {ineligible.map((candidate) => (
              <Card key={candidate.user_id} className="border-slate-200 bg-slate-50 px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <ShieldX className="size-4 text-slate-400" />
                  <span className="text-sm font-medium text-navy-900">{candidate.user_name}</span>
                  <Badge tone="neutral">Not eligible</Badge>
                </div>
                <ul className="mt-1.5 list-disc space-y-0.5 pl-5 text-xs text-slate-600">
                  {candidate.ineligibility_reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function CandidateCard({
  candidate,
  rank,
  selected,
  onSelect,
  disabled,
}: {
  candidate: CandidateRecommendation
  rank: number
  selected: boolean
  onSelect?: (userId: string) => void
  disabled: boolean
}) {
  const [showBreakdown, setShowBreakdown] = useState(rank === 1)

  return (
    <Card className={selected ? 'border-navy-500 ring-1 ring-navy-200' : undefined}>
      <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-navy-900">{candidate.user_name}</span>
            <Badge tone={rank === 1 ? 'navy' : 'neutral'}>Rank {rank}</Badge>
            <Badge tone="ok">
              <CheckCircle2 className="size-3" />
              Eligible
            </Badge>
          </div>
          <p className="mt-1 text-sm text-slate-600">{candidate.summary}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <div className="w-28">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-slate-500">Score</span>
              <span className="text-sm font-semibold tabular-nums text-navy-900">
                {candidate.total_score.toFixed(0)}
              </span>
            </div>
            <ProgressBar value={candidate.total_score} tone="navy" label="Candidate score" />
          </div>
          {onSelect ? (
            <Button
              size="sm"
              variant={selected ? 'primary' : 'secondary'}
              disabled={disabled}
              onClick={() => onSelect(candidate.user_id)}
            >
              {selected ? 'Selected' : 'Select'}
            </Button>
          ) : null}
        </div>
      </div>

      <div className="border-t border-slate-200 px-4 py-2">
        <button
          className="text-xs font-medium text-navy-600 underline-offset-2 hover:underline"
          onClick={() => setShowBreakdown((value) => !value)}
          aria-expanded={showBreakdown}
        >
          {showBreakdown ? 'Hide' : 'Show'} scoring breakdown
        </button>
        {showBreakdown ? (
          <table className="mt-2 w-full text-left text-xs">
            <thead className="text-slate-500">
              <tr>
                <th className="py-1 font-medium">Factor</th>
                <th className="py-1 font-medium">Weight</th>
                <th className="py-1 font-medium">Points</th>
                <th className="py-1 font-medium">Why</th>
              </tr>
            </thead>
            <tbody className="align-top text-slate-700">
              {candidate.breakdown.map((item) => (
                <tr key={item.factor} className="border-t border-slate-100">
                  <td className="py-1.5 pr-2 font-medium text-navy-900">
                    {titleCase(item.factor)}
                  </td>
                  <td className="py-1.5 pr-2 tabular-nums">{(item.weight * 100).toFixed(0)}%</td>
                  <td className="py-1.5 pr-2 tabular-nums">{item.weighted_score.toFixed(1)}</td>
                  <td className="py-1.5">{item.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
    </Card>
  )
}
