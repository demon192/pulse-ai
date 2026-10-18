/**
 * HTTP client.
 *
 * One place that knows how a request is authenticated and how an error is
 * surfaced, so every page handles failure the same way.
 */

import type {
  ActionInboxItem,
  AIEnvelope,
  EngineerDashboard,
  HandoverAnalysisResponse,
  HandoverView,
  ManagerDashboard,
  NotificationList,
  Priority,
  ProjectBriefingData,
  ProjectDetail,
  ProjectSummary,
  RequestCategory,
  RequestInterpretationData,
  RequestStatus,
  RiskExplanationData,
  SessionInfo,
  SupportRequestCreated,
  SupportRequestView,
  TaskDetail,
  TaskStatus,
  TeamMemberView,
} from '@/types/api'

const PERSONA_STORAGE_KEY = 'teampulse.persona'

export class ApiError extends Error {
  status: number
  fieldErrors: { field: string; message: string }[]

  constructor(
    status: number,
    message: string,
    fieldErrors: { field: string; message: string }[] = [],
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

/** The development persona is the only thing the client stores locally. */
export function getPersonaId(): string | null {
  try {
    return window.localStorage.getItem(PERSONA_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setPersonaId(userId: string): void {
  try {
    window.localStorage.setItem(PERSONA_STORAGE_KEY, userId)
  } catch {
    /* Storage can be unavailable; the header simply falls back to the default. */
  }
}

/**
 * In Firebase auth mode this is where the ID token is attached. It is a
 * separate hook so that swapping the dev persona switcher for real sign-in does
 * not touch any page.
 */
let bearerTokenProvider: (() => Promise<string | null>) | null = null

export function setBearerTokenProvider(provider: () => Promise<string | null>): void {
  bearerTokenProvider = provider
}

async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {}
  if (bearerTokenProvider) {
    const token = await bearerTokenProvider()
    if (token) headers.Authorization = `Bearer ${token}`
    // Bearer mode is exclusive: a persona left in storage by an earlier
    // development session must not ride along to a deployed instance.
    return headers
  }
  const persona = getPersonaId()
  if (persona) headers['X-Dev-User-Id'] = persona
  return headers
}

async function request<T>(
  path: string,
  init: RequestInit & { query?: Record<string, string | number | boolean | undefined> } = {},
): Promise<T> {
  const { query, ...rest } = init
  const url = new URL(path, window.location.origin)
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }

  let response: Response
  try {
    response = await fetch(url.toString(), {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        ...(await authHeaders()),
        ...rest.headers,
      },
    })
  } catch {
    throw new ApiError(0, 'Could not reach the TeamPulse API. Is the backend running?')
  }

  if (response.status === 204) return undefined as T

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const detail =
      (body && typeof body.detail === 'string' && body.detail) ||
      `Request failed with status ${response.status}.`
    throw new ApiError(response.status, detail, body?.errors ?? [])
  }
  return body as T
}

const post = <T>(path: string, payload?: unknown, query?: Record<string, string>) =>
  request<T>(path, {
    method: 'POST',
    body: payload === undefined ? undefined : JSON.stringify(payload),
    query,
  })

const patch = <T>(path: string, payload: unknown) =>
  request<T>(path, { method: 'PATCH', body: JSON.stringify(payload) })

export const api = {
  // --- session -----------------------------------------------------------
  session: () => request<SessionInfo>('/api/session'),

  // --- dashboards ---------------------------------------------------------
  managerDashboard: () => request<ManagerDashboard>('/api/dashboard/manager'),
  engineerDashboard: () => request<EngineerDashboard>('/api/dashboard/engineer'),

  // --- projects and tasks ---------------------------------------------------
  projects: () => request<ProjectSummary[]>('/api/projects'),
  project: (projectId: string) => request<ProjectDetail>(`/api/projects/${projectId}`),
  task: (taskId: string) => request<TaskDetail>(`/api/tasks/${taskId}`),
  updateTask: (
    taskId: string,
    payload: {
      status?: TaskStatus
      next_step?: string
      remaining_effort?: number
      blocked_reason?: string
      priority?: Priority
      progress_note?: string
    },
  ) => patch<TaskDetail>(`/api/tasks/${taskId}`, payload),

  // --- support requests ------------------------------------------------------
  requests: (query?: {
    status?: RequestStatus
    project_id?: string
    category?: RequestCategory
    include_closed?: boolean
  }) => request<SupportRequestView[]>('/api/requests', { query }),
  requestDetail: (requestId: string) =>
    request<SupportRequestView>(`/api/requests/${requestId}`),
  createRequest: (payload: {
    project_id: string
    category: RequestCategory
    title: string
    description: string
    task_id?: string | null
    priority: Priority
    due_date?: string | null
  }) => post<SupportRequestCreated>('/api/requests', payload),
  respondToRequest: (requestId: string, payload: { body: string; status?: RequestStatus }) =>
    post<SupportRequestView>(`/api/requests/${requestId}/respond`, payload),
  updateRequest: (
    requestId: string,
    payload: {
      status?: RequestStatus
      priority?: Priority
      assigned_owner_id?: string
      resolution_notes?: string
      engineer_context_note?: string
    },
  ) => patch<SupportRequestView>(`/api/requests/${requestId}`, payload),
  interpretRequest: (requestId: string) =>
    post<AIEnvelope<RequestInterpretationData>>(`/api/requests/${requestId}/interpret`),

  // --- action inbox -------------------------------------------------------------
  actions: (query?: { bucket?: string; project_id?: string; priority?: Priority }) =>
    request<ActionInboxItem[]>('/api/actions', { query }),
  updateAction: (
    actionId: string,
    payload: { status?: string; priority?: Priority; owner_id?: string; resolution_notes?: string },
  ) => patch<ActionInboxItem>(`/api/actions/${actionId}`, payload),
  resolveAction: (
    actionId: string,
    payload: { resolution_notes: string; decision?: string; decision_rationale?: string },
  ) => post<ActionInboxItem>(`/api/actions/${actionId}/resolve`, payload),

  // --- handovers ----------------------------------------------------------------
  handovers: () => request<HandoverView[]>('/api/handovers'),
  handover: (handoverId: string) => request<HandoverView>(`/api/handovers/${handoverId}`),
  createHandover: (payload: {
    unavailable_user_id?: string
    start_time: string
    expected_return?: string | null
    reason_category: string
    handover_notes?: string | null
    affected_task_ids?: string[]
  }) => post<HandoverView>('/api/handovers', payload),
  analyzeHandover: (handoverId: string) =>
    post<HandoverAnalysisResponse>(`/api/handovers/${handoverId}/analyze`),
  approveHandover: (handoverId: string, payload: { selected_backup_id: string; notes?: string }) =>
    post<HandoverView>(`/api/handovers/${handoverId}/approve`, payload),
  rejectHandover: (handoverId: string, payload: { reason: string }) =>
    post<HandoverView>(`/api/handovers/${handoverId}/reject`, payload),
  acceptHandover: (handoverId: string) =>
    post<HandoverView>(`/api/handovers/${handoverId}/accept`),
  declineHandover: (handoverId: string, payload: { reason: string }) =>
    post<HandoverView>(`/api/handovers/${handoverId}/decline`, payload),

  // --- notifications -------------------------------------------------------------
  notifications: (query?: { unread_only?: boolean }) =>
    request<NotificationList>('/api/notifications', { query }),
  markNotificationRead: (notificationId: string) =>
    post<NotificationList>(`/api/notifications/${notificationId}/read`),
  resolveNotification: (notificationId: string) =>
    post<NotificationList>(`/api/notifications/${notificationId}/resolve`),

  // --- AI --------------------------------------------------------------------------
  projectBriefing: (projectId: string, forceRefresh = false) =>
    post<AIEnvelope<ProjectBriefingData>>('/api/ai/project-briefing', {
      project_id: projectId,
      force_refresh: forceRefresh,
    }),
  riskExplanation: (projectId: string, findingId: string) =>
    post<AIEnvelope<RiskExplanationData>>('/api/ai/risk-explanation', {
      project_id: projectId,
      finding_id: findingId,
    }),
  handoverBrief: (handoverId: string, taskId?: string) =>
    post<AIEnvelope<Record<string, unknown>>>('/api/ai/handover-brief', {
      handover_id: handoverId,
      task_id: taskId ?? null,
    }),

  // --- reference -----------------------------------------------------------------------
  team: (projectId?: string) =>
    request<TeamMemberView[]>('/api/team', { query: { project_id: projectId } }),
}
