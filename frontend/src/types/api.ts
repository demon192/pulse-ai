/**
 * Types mirroring the backend Pydantic schemas.
 *
 * Kept hand-written and narrow on purpose: these are the shapes the UI
 * actually reads, so a backend change that matters shows up as a type error.
 */

export type Role = 'manager' | 'engineer'
export type AvailabilityStatus = 'available' | 'limited' | 'on_leave' | 'unavailable'
export type ProjectStatus = 'planning' | 'active' | 'paused' | 'completed'
export type ProjectHealth = 'on_track' | 'needs_attention' | 'at_risk'
export type TaskStatus = 'not_started' | 'in_progress' | 'blocked' | 'in_review' | 'completed'
export type Priority = 'low' | 'medium' | 'high' | 'critical'
export type RequestCategory =
  | 'blocker'
  | 'decision'
  | 'approval'
  | 'one_on_one'
  | 'progress_update'
  | 'other'
export type RequestStatus = 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'cancelled'
export type ActionType =
  | 'approval'
  | 'question'
  | 'support_request'
  | 'follow_up'
  | 'deadline'
  | 'overdue_task'
  | 'blocker'
  | 'handover_approval'
  | 'one_on_one'
export type ActionStatus = 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'cancelled'
export type ApprovalStatus = 'pending' | 'approved' | 'rejected'
export type HandoverStatus =
  | 'draft'
  | 'analyzed'
  | 'pending_manager_review'
  | 'approved'
  | 'rejected'
  | 'accepted'
  | 'declined'
  | 'completed'
  | 'cancelled'
export type EvidenceKind = 'verified_fact' | 'rule_derived' | 'hypothesis' | 'recommendation'
export type RiskKind =
  | 'overdue_task'
  | 'blocked_task'
  | 'blocked_dependency_chain'
  | 'pending_approval_blocking_work'
  | 'milestone_at_risk'
  | 'unassigned_critical_work'
  | 'coverage_gap'

export interface SessionUser {
  id: string
  name: string
  email: string
  role: Role
  title: string | null
  team_id: string
  availability_status: AvailabilityStatus
  authorized_project_ids: string[]
  skills: string[]
}

export interface DevPersona {
  id: string
  name: string
  role: Role
  title: string | null
}

/** GET /api/auth-config — how this instance expects callers to authenticate. */
export interface AuthConfig {
  auth_mode: string
  environment: string
  sign_in_configured: boolean
  dev_personas_enabled: boolean
  firebase_api_key: string | null
  firebase_auth_domain: string | null
  firebase_project_id: string | null
}

export interface SessionInfo {
  user: SessionUser
  auth_mode: string
  environment: string
  demo_data_mode: boolean
  ai_configured: boolean
  ai_model: string | null
  dev_personas: DevPersona[]
}

export interface AIMeta {
  source: 'gemini' | 'cache' | 'deterministic_fallback'
  model: string | null
  generated_at: string | null
  degraded: boolean
  notes: string[]
}

export interface AIEnvelope<T = Record<string, unknown>> {
  meta: AIMeta
  data: T
}

export interface AIRiskNote {
  title: string
  explanation: string
  evidence_kind: EvidenceKind
  source_ids: string[]
}

export interface ProjectBriefingData {
  progress_summary: string
  key_risks: AIRiskNote[]
  blockers: AIRiskNote[]
  recommended_actions: string[]
  uncertainties: string[]
}

export interface RequestInterpretationData {
  summary: string
  suggested_category: RequestCategory
  suggested_priority: Priority
  suggested_task_id: string
  suggested_next_steps: string[]
  missing_context: string[]
}

export interface RiskExplanationData {
  explanation: string
  statements: { text: string; evidence_kind: EvidenceKind; source_ids: string[] }[]
}

export interface Evidence {
  label: string
  detail: string
  entity_type: string | null
  entity_id: string | null
}

export interface RiskFinding {
  id: string
  kind: RiskKind
  severity: number
  title: string
  summary: string
  project_id: string
  task_ids: string[]
  downstream_task_ids: string[]
  milestone_ids: string[]
  action_ids: string[]
  request_ids: string[]
  evidence: Evidence[]
  suggested_actions: string[]
  explanation: string | null
  explanation_source: string | null
}

export interface MilestoneStatus {
  milestone_id: string
  name: string
  target_date: string
  days_remaining: number
  total_tasks: number
  completed_tasks: number
  blocked_tasks: number
  overdue_tasks: number
  at_risk: boolean
  reasons: string[]
}

export interface ProjectHealthReport {
  project_id: string
  project_name: string
  health: ProjectHealth
  health_score: number
  total_tasks: number
  completed_tasks: number
  in_progress_tasks: number
  blocked_tasks: number
  overdue_tasks: number
  open_requests: number
  open_actions: number
  next_milestone: MilestoneStatus | null
  milestones: MilestoneStatus[]
  risks: RiskFinding[]
  headline: string
}

export interface Project {
  id: string
  name: string
  description: string
  manager_id: string
  status: ProjectStatus
  start_date: string
  target_date: string
  milestone_ids: string[]
  team_member_ids: string[]
  is_demo_data: boolean
}

export interface Milestone {
  id: string
  project_id: string
  name: string
  description: string | null
  target_date: string
  task_ids: string[]
  completed: boolean
}

export interface Task {
  id: string
  project_id: string
  title: string
  description: string
  owner_id: string | null
  status: TaskStatus
  priority: Priority
  created_at: string
  updated_at: string
  due_date: string | null
  dependency_ids: string[]
  related_request_ids: string[]
  related_document_ids: string[]
  next_step: string | null
  required_skills: string[]
  required_permission: string | null
  estimated_effort: number | null
  remaining_effort: number | null
  blocked_reason: string | null
  is_demo_data: boolean
}

export interface TaskView {
  task: Task
  owner_name: string
  project_name: string
  blocking_dependencies: string[]
  downstream_task_ids: string[]
  is_overdue: boolean
  days_until_due: number | null
}

export interface TaskUpdate {
  id: string
  task_id: string
  author_id: string
  body: string
  created_at: string
  is_demo_data: boolean
}

export interface ProjectDocument {
  id: string
  project_id: string
  task_ids: string[]
  title: string
  doc_type: string
  url: string | null
  summary: string | null
  updated_at: string
  is_demo_data: boolean
}

export interface DecisionRecord {
  id: string
  project_id: string
  task_id: string | null
  title: string
  decision: string
  rationale: string | null
  decided_by: string
  decided_at: string
  is_demo_data: boolean
}

export interface UserPublic {
  id: string
  name: string
  role: Role
  title: string | null
  availability_status: AvailabilityStatus
}

export interface ProjectSummary {
  project: Project
  manager_name: string
  health: ProjectHealthReport
}

export interface ProjectDetail {
  project: Project
  manager_name: string
  health: ProjectHealthReport
  milestones: Milestone[]
  tasks: TaskView[]
  team: UserPublic[]
  documents: ProjectDocument[]
  decisions: DecisionRecord[]
  cached_briefing: AIEnvelope<ProjectBriefingData> | null
}

export interface TaskDetail {
  task: TaskView
  updates: TaskUpdate[]
  requests: SupportRequest[]
  documents: ProjectDocument[]
  dependencies: Task[]
  dependents: Task[]
}

export interface RequestResponse {
  author_id: string
  body: string
  created_at: string
}

export interface SupportRequest {
  id: string
  engineer_id: string
  project_id: string
  task_id: string | null
  category: RequestCategory
  title: string
  description: string
  priority: Priority
  status: RequestStatus
  assigned_owner_id: string | null
  created_at: string
  updated_at: string
  due_date: string | null
  responses: RequestResponse[]
  resolution_notes: string | null
  engineer_context_note: string | null
  is_demo_data: boolean
}

export interface SupportRequestView {
  request: SupportRequest
  engineer_name: string
  project_name: string
  task_title: string | null
  owner_name: string | null
  action_item_id: string | null
}

export interface ActionItem {
  id: string
  project_id: string | null
  task_id: string | null
  source_request_id: string | null
  source_handover_id: string | null
  type: ActionType
  title: string
  description: string
  owner_id: string
  created_by: string
  created_at: string
  updated_at: string
  due_date: string | null
  status: ActionStatus
  priority: Priority
  resolution_notes: string | null
  decision_record_id: string | null
  is_demo_data: boolean
}

export interface PriorityFactor {
  factor: string
  points: number
  detail: string
}

export interface ActionPriority {
  action_id: string
  score: number
  bucket: 'urgent' | 'blocked_work' | 'approvals' | 'support' | 'routine'
  due_in_days: number | null
  factors: PriorityFactor[]
  blocks_task_ids: string[]
  affected_milestone_ids: string[]
  consequence: string | null
}

export interface ActionInboxItem {
  action: ActionItem
  priority_detail: ActionPriority
  owner_name: string
  project_name: string | null
  task_title: string | null
  requester_name: string | null
  source_request: SupportRequest | null
  source_handover_id: string | null
}

export interface CandidateScoreBreakdown {
  factor: string
  weight: number
  raw_score: number
  weighted_score: number
  explanation: string
}

export interface CandidateRecommendation {
  user_id: string
  user_name: string
  eligible: boolean
  ineligibility_reasons: string[]
  total_score: number
  breakdown: CandidateScoreBreakdown[]
  summary: string
}

export interface HandoverBriefSection {
  key: string
  heading: string
  content: string
  evidence_kind: EvidenceKind
  source_ids: string[]
}

export interface HandoverBrief {
  task_id: string
  task_title: string
  sections: HandoverBriefSection[]
  generated_at: string
  generated_by: string
}

export interface HandoverRecord {
  id: string
  unavailable_user_id: string
  requested_by: string
  reason_category: string
  start_time: string
  expected_return: string | null
  affected_task_ids: string[]
  affected_project_ids: string[]
  downstream_task_ids: string[]
  pending_approval_action_ids: string[]
  relevant_document_ids: string[]
  affected_milestone_ids: string[]
  candidate_recommendations: CandidateRecommendation[]
  generated_brief: HandoverBrief[]
  missing_information: string[]
  handover_notes: string | null
  manager_approval_status: ApprovalStatus
  approved_by: string | null
  approved_at: string | null
  selected_backup_id: string | null
  backup_accepted_at: string | null
  handover_status: HandoverStatus
  rejection_reason: string | null
  created_at: string
  updated_at: string
  is_demo_data: boolean
}

export interface AuditEvent {
  id: string
  actor_id: string
  action: string
  entity_type: string
  entity_id: string
  created_at: string
  details: Record<string, string>
}

export interface HandoverView {
  handover: HandoverRecord
  unavailable_user_name: string
  total_candidate_count: number
  eligible_candidate_count: number
  selected_backup_name: string | null
  approved_by_name: string | null
  affected_tasks: Task[]
  downstream_tasks: Task[]
  affected_milestones: MilestoneStatus[]
  pending_actions: ActionItem[]
  documents: ProjectDocument[]
  audit_trail: AuditEvent[]
  can_approve: boolean
  can_accept: boolean
}

export interface HandoverAnalysis {
  handover_id: string
  unavailable_user_id: string
  unavailable_user_name: string
  active_task_ids: string[]
  downstream_task_ids: string[]
  affected_project_ids: string[]
  affected_milestone_ids: string[]
  upstream_blocking_task_ids: string[]
  pending_approval_action_ids: string[]
  relevant_document_ids: string[]
  open_request_ids: string[]
  candidates: CandidateRecommendation[]
  missing_information: string[]
  evidence: Evidence[]
}

export interface HandoverAnalysisResponse {
  handover: HandoverView
  analysis: HandoverAnalysis
}

export interface CoverageGap {
  user_id: string
  user_name: string
  availability_status: string
  open_task_count: number
  has_approved_handover: boolean
  handover_id: string | null
  priority: Priority
}

export interface Notification {
  id: string
  recipient_id: string
  type: string
  title: string
  message: string
  reason: string
  suggested_action: string | null
  priority: Priority
  related_entity_type: string | null
  related_entity_id: string | null
  created_at: string
  read_at: string | null
  resolved_at: string | null
  deduplication_key: string
  escalation_count: number
  last_escalated_at: string | null
  is_demo_data: boolean
}

export interface NotificationList {
  notifications: Notification[]
  unread_count: number
}

export interface ManagerSummary {
  projects_total: number
  projects_at_risk: number
  tasks_needing_attention: number
  pending_approvals: number
  open_support_requests: number
  overdue_actions: number
  upcoming_milestones: number
  coverage_gaps: number
  unread_notifications: number
}

export interface ManagerDashboard {
  generated_at: string
  summary: ManagerSummary
  project_health: ProjectHealthReport[]
  action_inbox: ActionInboxItem[]
  open_requests: SupportRequestView[]
  upcoming_milestones: MilestoneStatus[]
  top_risks: RiskFinding[]
  coverage: CoverageGap[]
  handovers_awaiting_review: HandoverView[]
  recent_activity: Notification[]
  daily_briefing: AIEnvelope<ProjectBriefingData> | null
}

export interface EngineerSummary {
  open_tasks: number
  blocked_tasks: number
  overdue_tasks: number
  open_requests: number
  awaiting_response: number
  unread_notifications: number
}

export interface EngineerDashboard {
  generated_at: string
  summary: EngineerSummary
  my_tasks: TaskView[]
  my_blockers: TaskView[]
  my_requests: SupportRequestView[]
  awaiting_response: SupportRequestView[]
  upcoming_deadlines: TaskView[]
  availability_status: AvailabilityStatus
  my_handovers: HandoverView[]
  assigned_to_me: HandoverView[]
  recent_notifications: Notification[]
}

export interface TeamMemberView {
  user: UserPublic
  open_task_count: number
  is_authorized_here: boolean
}

export interface SupportRequestCreated {
  request: SupportRequest
  action_item: ActionItem | null
  interpretation: AIEnvelope<RequestInterpretationData> | null
}
