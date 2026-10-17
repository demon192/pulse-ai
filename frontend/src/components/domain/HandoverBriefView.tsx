/**
 * The generated handover brief.
 *
 * Every section states how it was derived, and missing information is shown as
 * prominently as the content — an incoming engineer needs to know what the
 * records could not tell them.
 */

import { AlertCircle, FileText } from 'lucide-react'

import { EvidenceKindBadge } from '@/components/domain/labels'
import { Badge, Card, CardBody, CardHeader } from '@/components/ui/primitives'
import { formatDateTime } from '@/lib/format'
import type { HandoverBrief } from '@/types/api'

export function HandoverBriefView({
  brief,
  missingInformation,
}: {
  brief: HandoverBrief
  missingInformation?: string[]
}) {
  return (
    <Card>
      <CardHeader
        icon={<FileText className="size-4" />}
        title={`Handover brief — ${brief.task_title}`}
        description={`Generated ${formatDateTime(brief.generated_at)}`}
        actions={
          <Badge tone={brief.generated_by === 'gemini' ? 'navy' : 'warn'}>
            {brief.generated_by === 'gemini'
              ? 'Synthesised by Gemini'
              : brief.generated_by === 'cache'
                ? 'Cached'
                : 'Assembled from records'}
          </Badge>
        }
      />
      <CardBody className="space-y-4">
        {brief.sections.map((section) => (
          <div key={section.key}>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-semibold text-navy-900">{section.heading}</h4>
              <EvidenceKindBadge kind={section.evidence_kind} />
            </div>
            <p className="mt-1 text-sm whitespace-pre-line text-slate-700">{section.content}</p>
            {section.source_ids.length > 0 ? (
              <p className="mt-1 text-xs text-slate-400">
                Sources: {section.source_ids.join(', ')}
              </p>
            ) : null}
          </div>
        ))}

        {missingInformation && missingInformation.length > 0 ? (
          <div className="rounded-lg border border-warn-200 bg-warn-50 p-3">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-warn-700">
              <AlertCircle className="size-4" />
              Missing information to confirm with a human
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-warn-700">
              {missingInformation.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardBody>
    </Card>
  )
}
