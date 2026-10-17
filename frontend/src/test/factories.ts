/**
 * Builders for the API shapes the components read.
 *
 * Defaults mirror the seeded demo organisation, so a test only has to state
 * the field it is actually about.
 */

import type {
  ActionInboxItem,
  CandidateRecommendation,
  HandoverBrief,
  RiskFinding,
  SupportRequestView,
  TaskView,
} from '@/types/api'

export function riskFinding(overrides: Partial<RiskFinding> = {}): RiskFinding {
  return {
    id: 'risk-blocked-pay-02',
    kind: 'blocked_dependency_chain',
    severity: 78,
    title: 'Blocked: Implement settlement worker',
    summary: 'Implement settlement worker is blocked and 1 task(s) depend on it.',
    project_id: 'proj-payments',
    task_ids: ['pay-02'],
    downstream_task_ids: ['pay-03'],
    milestone_ids: ['ms-pay-1'],
    action_ids: [],
    request_ids: [],
    evidence: [
      {
        label: 'Implement settlement worker',
        detail: 'Partial-refund field semantics are still undecided.',
        entity_type: 'task',
        entity_id: 'pay-02',
      },
      {
        label: 'Settlement reconciliation UI',
        detail: 'Downstream work waiting on this blocker.',
        entity_type: 'task',
        entity_id: 'pay-03',
      },
    ],
    suggested_actions: [
      'Unblock the upstream dependency: Define settlement API contract',
      'Re-sequence or re-scope 1 dependent task(s) if the blocker persists.',
    ],
    explanation: null,
    explanation_source: null,
    ...overrides,
  }
}

export function candidate(
  overrides: Partial<CandidateRecommendation> = {},
): CandidateRecommendation {
  return {
    user_id: 'eng-001',
    user_name: 'Arjun Mehta',
    eligible: true,
    ineligibility_reasons: [],
    total_score: 84,
    breakdown: [
      {
        factor: 'relevant_skills',
        weight: 0.3,
        raw_score: 1,
        weighted_score: 30,
        explanation: 'Matches 3/3 required skill(s): backend, payments, python.',
      },
      {
        factor: 'current_workload',
        weight: 0.15,
        raw_score: 0.1,
        weighted_score: 1.5,
        explanation: 'Assigned 36h of 40h weekly capacity (90% used).',
      },
    ],
    summary: 'Score 84/100. Strongest factors: relevant_skills (30 pts).',
    ...overrides,
  }
}

export function actionInboxItem(
  overrides: Partial<ActionInboxItem> = {},
): ActionInboxItem {
  return {
    action: {
      id: 'act-001',
      project_id: 'proj-payments',
      task_id: 'pay-01',
      source_request_id: 'req-001',
      source_handover_id: null,
      type: 'approval',
      title: 'Approve settlement API contract v3',
      description: 'Arjun Mehta needs a decision on partial-refund modelling.',
      owner_id: 'mgr-001',
      created_by: 'eng-001',
      created_at: '2026-06-12T09:00:00Z',
      updated_at: '2026-06-12T09:00:00Z',
      due_date: '2026-06-14T09:00:00Z',
      status: 'open',
      priority: 'critical',
      resolution_notes: null,
      decision_record_id: null,
      is_demo_data: true,
    },
    priority_detail: {
      action_id: 'act-001',
      score: 92,
      bucket: 'urgent',
      due_in_days: -1,
      factors: [
        {
          factor: 'explicit_urgency',
          points: 30,
          detail: "Recorded priority is 'critical'.",
        },
      ],
      blocks_task_ids: ['pay-02', 'pay-03'],
      affected_milestone_ids: ['ms-pay-1'],
      consequence:
        "2 dependent task(s) cannot proceed; 'Settlement API GA' is 3.0 day(s) away.",
    },
    owner_name: 'Priya Raman',
    project_name: 'Payments Platform v2',
    task_title: 'Define settlement API contract',
    requester_name: 'Arjun Mehta',
    source_request: null,
    source_handover_id: null,
    ...overrides,
  }
}

export function handoverBrief(overrides: Partial<HandoverBrief> = {}): HandoverBrief {
  const keys = [
    ['objective', 'Task and project objective'],
    ['current_status', 'Current status'],
    ['work_completed', 'Work completed'],
    ['files_and_links', 'Relevant files, links and documents'],
    ['decisions_made', 'Decisions already made'],
    ['open_questions', 'Unresolved questions'],
    ['dependencies', 'Dependencies and affected tasks'],
    ['known_blockers', 'Known blockers'],
    ['next_steps', 'Suggested next steps'],
    ['contacts', 'Relevant contacts and reviewers'],
    ['missing_information', 'Missing information to confirm'],
  ] as const
  return {
    task_id: 'pay-02',
    task_title: 'Implement settlement worker',
    sections: keys.map(([key, heading]) => ({
      key,
      heading,
      content: `Content for ${heading}.`,
      evidence_kind: key === 'next_steps' ? 'recommendation' : 'verified_fact',
      source_ids: ['pay-02'],
    })),
    generated_at: '2026-06-15T09:00:00Z',
    generated_by: 'deterministic_fallback',
    ...overrides,
  }
}

export function taskView(overrides: Partial<TaskView> = {}): TaskView {
  return {
    task: {
      id: 'pay-02',
      project_id: 'proj-payments',
      title: 'Implement settlement worker',
      description: 'Consume settlement events and write ledger entries.',
      owner_id: 'eng-008',
      status: 'blocked',
      priority: 'critical',
      created_at: '2026-05-28T09:00:00Z',
      updated_at: '2026-06-13T09:00:00Z',
      due_date: '2026-06-17T09:00:00Z',
      dependency_ids: ['pay-01'],
      related_request_ids: [],
      related_document_ids: ['doc-001'],
      next_step: 'Resume once contract v3 is approved.',
      required_skills: ['backend', 'python', 'payments'],
      required_permission: null,
      estimated_effort: 40,
      remaining_effort: 18,
      blocked_reason: 'Partial-refund field semantics are still undecided.',
      is_demo_data: true,
    },
    owner_name: 'Rhea Kapoor',
    project_name: 'Payments Platform v2',
    blocking_dependencies: ['Define settlement API contract'],
    downstream_task_ids: ['pay-03'],
    is_overdue: false,
    days_until_due: 2,
    ...overrides,
  }
}

export function requestView(
  overrides: Partial<SupportRequestView> = {},
): SupportRequestView {
  return {
    request: {
      id: 'req-001',
      engineer_id: 'eng-001',
      project_id: 'proj-payments',
      task_id: 'pay-01',
      category: 'approval',
      title: 'Approve settlement API contract v3',
      description: 'Contract v3 is ready to freeze.',
      priority: 'critical',
      status: 'open',
      assigned_owner_id: 'mgr-001',
      created_at: '2026-06-12T09:00:00Z',
      updated_at: '2026-06-12T09:00:00Z',
      due_date: null,
      responses: [],
      resolution_notes: null,
      engineer_context_note: null,
      is_demo_data: true,
    },
    engineer_name: 'Arjun Mehta',
    project_name: 'Payments Platform v2',
    task_title: 'Define settlement API contract',
    owner_name: 'Priya Raman',
    action_item_id: 'act-001',
    ...overrides,
  }
}
