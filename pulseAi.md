
# TeamPulse AI — Complete Product Brief & Implementation Instructions

## 1. Your Role

Act as a senior full-stack engineer, AI engineer, product designer, and technical architect. Build a complete, polished, working MVP called **TeamPulse AI** for the Google AI Builder Cup challenge.

Do not stop at architecture, pseudocode, or a UI mockup. Inspect the existing repository, create the application, implement its backend and frontend, run tests, fix errors, and document how to launch and deploy it.

If a repository already contains code, inspect it first and preserve useful existing work. If it is empty, initialize the project from scratch.

When information is missing, make sensible engineering decisions, document assumptions, and continue without unnecessarily asking questions.

---

# 2. Product Vision

**Product name:** TeamPulse AI

**Tagline:** Never lose track of what your team needs.

**Challenge theme:** Future of Work & Enterprise Productivity.

### The problem

Engineering managers often supervise multiple projects and many engineers simultaneously. Important information is spread across tickets, pull requests, messages, meetings, and documents.

As a result:

- An engineer requests approval, but the request gets lost in chat.
- An engineer is blocked but cannot get time with their manager.
- A manager forgets a promised follow-up or a pending decision.
- A dependency silently puts a delivery milestone at risk.
- An engineer takes emergency leave, and nobody knows which work needs to be handed over.
- A replacement engineer receives incomplete context and spends hours understanding the work.
- Managers have to manually assemble progress reports from several sources.

This is not primarily an employee-monitoring problem. It is a **team coordination, project visibility, and engineering support problem**.

### The solution

TeamPulse AI is an AI-powered engineering operations dashboard that connects project progress, blockers, manager commitments, notifications, and intelligent handovers.

It helps managers answer:

1. What needs my attention today?
2. Which projects or deliveries are at risk, and why?
3. Which engineers have requested support?
4. Which approvals, decisions, and follow-ups are pending?
5. What work will be affected if an engineer becomes unavailable?
6. Who is a suitable backup, and what information do they need?

Engineers should also be able to communicate blockers, ask for support, submit work updates, and track their requests without repeatedly chasing their managers.

### Core product principle

**TeamPulse AI helps managers support engineers and protect delivery continuity. It must not become a hidden employee-surveillance or productivity-scoring tool.**

---

# 3. Product Scope

Build four integrated capabilities.

## Module A: Project Intelligence

Provide a consolidated view of projects, milestones, tasks, dependencies, and delivery risks.

Features:

- Project overview cards.
- Task status: Not Started, In Progress, Blocked, In Review, Completed.
- Task owner, priority, deadline, and next action.
- Dependencies between tasks.
- Detection of overdue work and potentially affected downstream tasks.
- Project health indicators.
- AI-generated project summaries.
- Clear explanations of why a project or milestone requires attention.

Example:

A shared API task is delayed. Two downstream tasks depend on it, and a release milestone is approaching.

TeamPulse should display:

- The delayed API task.
- The two dependent tasks.
- The milestone potentially affected.
- The evidence supporting the warning.
- Suggested actions for the manager.

Do not automatically assume that a long-running task indicates poor performance. Distinguish task age from explicit blockers, deadlines, dependencies, and delivery impact.

## Module B: Engineer Support

Create an engineer workspace where team members can report issues and request help.

Engineers should be able to:

- Submit a blocker.
- Ask for a technical or product decision.
- Request approval.
- Request a one-on-one with their manager.
- Update task progress.
- Record the next step.
- View the status of their requests.
- Add context or correct an inaccurate AI summary.

Each request should include:

- Request ID.
- Engineer.
- Project and optional task.
- Request category.
- Description.
- Date created.
- Priority.
- Assigned owner.
- Status.
- Due date, if applicable.
- Resolution notes.

Request statuses:

- Open.
- Acknowledged.
- In Progress.
- Resolved.
- Cancelled.

Requests should remain visible until resolved or cancelled. They should not disappear when the manager marks a notification as read.

## Module C: Manager Action Inbox

This is one of the most important features.

Managers receive one consolidated view of:

- Pending approvals.
- Unanswered questions.
- Engineer support requests.
- Promised follow-ups.
- Upcoming deadlines.
- Overdue actions.
- Unresolved blockers.
- Handover approvals.

Every action item must have an owner, status, context, and optional deadline.

The system should identify when a pending item has a meaningful downstream consequence.

Example:

**API design approval — Payment Service**

- Waiting for two days.
- One dependent task is blocked.
- Release milestone is three days away.
- Suggested action: review the design or delegate it to an authorized technical approver.

This is illustrative demo data, not a hardcoded dashboard message.

The manager should be able to:

- Open the underlying request.
- Acknowledge it.
- Add a response.
- Assign or delegate it where permitted.
- Change its status.
- Record a decision.
- Mark it resolved.

Engineers must see the appropriate status changes and responses.

### Follow-up intelligence

Create deterministic rules for prioritizing action items using:

- Explicit urgency.
- Time remaining before a deadline.
- Whether the item blocks another task.
- Number and importance of affected downstream tasks.
- Project milestone proximity.
- Time waiting for a response.

Use Gemini to explain context and suggest actions, not to invent deadlines or silently alter priority data.

Do not send repeated alerts for every old item. Implement notification deduplication and sensible escalation rules.

## Module D: Intelligent Handover

Support planned leave and emergency unavailability.

The engineer should be able to submit an availability or handover request with:

- Start date and time.
- Expected return, if known.
- Affected projects or tasks.
- Optional handover notes.

Do not request private medical or family details. Leave approval and personnel policies are outside this MVP.

When an engineer becomes unavailable, TeamPulse should:

1. Identify their active tasks.
2. Find tasks linked by dependencies.
3. Identify approaching deadlines and affected milestones.
4. Retrieve relevant documentation, decisions, task updates, and pending approvals.
5. Find eligible backup candidates.
6. Rank candidates using transparent criteria.
7. Generate a handover brief using Gemini.
8. Notify the manager for review.
9. Allow the manager to approve a handover.
10. Notify the selected backup and track acceptance.

### Backup candidate ranking

Use a deterministic scoring system based on available, authorized work-related data.

Suggested factors:

- Relevant skills: 30%.
- Familiarity with the project or codebase: 25%.
- Availability: 20%.
- Current workload: 15%.
- Access permissions and eligibility: 10%.

These are initial tunable weights, not validated industry standards.

Important rules:

- Access permissions and hard eligibility requirements must be enforced before ranking.
- An ineligible candidate must never be recommended as assignable.
- Candidate scores must be explainable.
- A manager must approve assignments.
- If no suitable candidate exists, explain why and recommend manual intervention.
- Do not use protected personal characteristics, inferred personality, private leave reasons, or employee performance scores.

### Handover brief

Generate a structured brief containing:

1. Task and project objective.
2. Current status.
3. Work completed.
4. Relevant files, links, and documents.
5. Decisions already made.
6. Unresolved questions.
7. Dependencies and affected tasks.
8. Known blockers.
9. Suggested next steps.
10. Relevant contacts or reviewers.
11. Missing information that requires confirmation.

Generate a preliminary brief even if the unavailable engineer has not written handover notes. Use only existing authorized project records, clearly label missing information, and never fabricate completed work or technical facts.

---

# 4. Required Demonstration Scenario

The entire product must work together in one coherent scenario.

Create a fictional software engineering organization with:

- 10 engineers.
- 3 projects.
- 1 manager.
- Interdependent tasks.
- Pending approvals.
- Support requests.
- Different skills and workloads.
- At least one approaching release deadline.

Use realistic seeded data.

### Scenario 1: The lost approval

An engineer requests approval for an API design.

The manager does not respond immediately.

The request remains in the action inbox. As the deadline approaches, TeamPulse identifies that another task is blocked by the pending decision and highlights the delivery impact.

The manager responds, and the engineer sees the status change.

### Scenario 2: An engineer needs help

An engineer reports that a feature is blocked by an unclear requirement.

TeamPulse links the request to the relevant task and project. Gemini summarizes the problem and proposes possible next actions.

The manager sees the request, responds, and resolves or delegates it.

### Scenario 3: Emergency leave

An engineer becomes unavailable while working on a critical release.

TeamPulse identifies:

- Their active tasks.
- Dependencies and downstream tasks.
- Pending approvals.
- Relevant documentation.
- Deadlines that could be affected.

The system recommends suitable backup candidates and explains their rankings.

Gemini generates a handover brief.

The manager reviews the brief, selects a candidate, and confirms the handover. The backup receives an in-app notification and can acknowledge the assignment.

All of these steps must be functional in the demo.

---

# 5. Technology Stack

Use a Google Cloud-compatible stack that is achievable for a solo developer.

## Frontend

- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- A consistent component library such as shadcn/ui, if compatible with the project.
- Recharts for useful charts, if required.
- Lucide icons.

Create a responsive, professional enterprise dashboard. Avoid a generic chatbot-centered interface.

## Backend

- Python.
- FastAPI.
- Pydantic models.
- Clear separation between API routes, business logic, AI services, and data access.
- Automated tests using pytest.

## AI

Use a supported Gemini model through Google's official SDK or Vertex AI.

- Read model configuration from environment variables.
- Use structured outputs for summaries, risk explanations, and handover briefs.
- Validate model responses before using them.
- Handle rate limits, timeouts, and malformed output.
- Provide a deterministic fallback for nonessential AI features when the model is unavailable.
- Never hardcode API keys.

Before choosing a specific Gemini model or SDK interface, verify current supported APIs and use the appropriate official documentation available in the development environment.

## Database

Use Cloud Firestore for the deployed application.

Define a repository/data-access layer so that the application can be tested locally without requiring production credentials. Provide a simple local development adapter or documented emulator setup.

Seed data must be reproducible and must not overwrite real user data.

## Authentication

Use Firebase Authentication if feasible within the implementation timeline.

Enforce role-based authorization in the backend, not just by hiding UI elements.

For local demos, provide a clearly labeled development-only authentication mode with predefined manager and engineer personas. It must be disabled in production.

## Deployment

Deploy the backend and built frontend together as a containerized application on Google Cloud Run for the first MVP.

Use:

- Docker.
- Cloud Run.
- Firestore.
- Gemini through the supported Google AI integration.
- Environment-based configuration.
- Google Secret Manager or an appropriate secure secret-injection mechanism for production credentials.

Firebase Hosting or Firebase App Hosting can be considered later if a separate frontend deployment becomes useful.

---

# 6. Architecture

Implement this logical architecture:

Browser
→ React application
→ FastAPI endpoints
→ Authentication and authorization
→ Business logic and rules engine
→ Firestore repository
→ Gemini service when AI reasoning is required
→ In-app notification creation

### Core architectural rules

1. Use deterministic code for deadlines, permissions, dependency traversal, eligibility checks, assignment approval, and notification deduplication.
2. Use Gemini for summarization, interpreting unstructured work updates, synthesizing handovers, explaining risks, and suggesting actions.
3. Link important AI findings to the underlying tasks, requests, or documents.
4. Store actionable items and notification state in the database.
5. Avoid making an LLM call on every dashboard render.
6. Cache or persist generated summaries where appropriate and refresh them when relevant data changes.
7. Do not let AI output execute arbitrary operations or modify assignments without authorization.
8. Keep API responses structured, typed, and validated.
9. Implement clear error states and logging without leaking secrets or sensitive data.
10. Use a modular design, but avoid unnecessary microservices and multi-agent orchestration.

---

# 7. Data Model

Create appropriate Pydantic schemas and Firestore collections or equivalent local persistence structures.

## Users

Fields:

- id
- name
- email
- role
- team_id
- skills
- project_familiarity
- weekly_capacity
- assigned_workload
- availability_status
- authorized_project_ids

Roles: manager and engineer.

The availability information should be limited to operational requirements.

## Projects

Fields:

- id
- name
- description
- manager_id
- status
- start_date
- target_date
- milestone_ids
- team_member_ids

## Tasks

Fields:

- id
- project_id
- title
- description
- owner_id
- status
- priority
- created_at
- updated_at
- due_date
- dependency_ids
- related_request_ids
- related_document_ids
- next_step
- estimated_effort
- remaining_effort

Use consistent timestamps and explicit timezone handling.

## Support Requests

Fields:

- id
- engineer_id
- project_id
- task_id
- category
- title
- description
- priority
- status
- assigned_owner_id
- created_at
- updated_at
- due_date
- response
- resolution_notes

## Action Items

Fields:

- id
- project_id
- task_id
- source_request_id
- type
- title
- description
- owner_id
- created_by
- created_at
- due_date
- status
- priority
- resolution_notes

## Handover Records

Fields:

- id
- unavailable_user_id
- start_time
- expected_return
- affected_task_ids
- affected_project_ids
- candidate_recommendations
- generated_brief
- missing_information
- manager_approval_status
- selected_backup_id
- handover_status
- created_at
- updated_at

## Notifications

Fields:

- id
- recipient_id
- type
- title
- message
- priority
- related_entity_type
- related_entity_id
- created_at
- read_at
- resolved_at
- deduplication_key

Add indexes, validation, and appropriate database security rules where required.

The exact schema can be refined during implementation, but keep relationships consistent across the frontend, backend, and database.

---

# 8. API Design

Implement REST endpoints with appropriate validation and authorization.

Suggested endpoints:

## Dashboard and Projects

- GET /api/dashboard/manager
- GET /api/dashboard/engineer
- GET /api/projects
- GET /api/projects/{project_id}
- GET /api/projects/{project_id}/tasks
- GET /api/tasks/{task_id}
- PATCH /api/tasks/{task_id}

## Support Requests

- POST /api/requests
- GET /api/requests
- GET /api/requests/{request_id}
- PATCH /api/requests/{request_id}
- POST /api/requests/{request_id}/respond

## Manager Actions

- GET /api/actions
- POST /api/actions
- PATCH /api/actions/{action_id}
- POST /api/actions/{action_id}/resolve

## Handover

- POST /api/handovers
- GET /api/handovers
- GET /api/handovers/{handover_id}
- POST /api/handovers/{handover_id}/analyze
- POST /api/handovers/{handover_id}/approve
- POST /api/handovers/{handover_id}/accept

## AI

- POST /api/ai/project-briefing
- POST /api/ai/request-summary
- POST /api/ai/handover-brief

## Notifications

- GET /api/notifications
- POST /api/notifications/{notification_id}/read
- POST /api/notifications/{notification_id}/resolve

Add health-check endpoints, including GET /health.

These routes are suggestions, not a requirement to create redundant endpoints. Prefer a consistent, maintainable API.

---

# 9. AI Implementation Requirements

Gemini must be meaningfully integrated. Do not simply add a chat window and claim the product is AI-powered.

## Capability 1: Project briefing

Input: Authorized project/task data, deadlines, dependencies, and open actions.

Output:

- Summary of progress.
- Key risks.
- Supporting task or action IDs.
- Blockers.
- Recommended manager actions.
- Uncertainties and missing information.

## Capability 2: Request interpretation

Input: An engineer's written request.

Output:

- Concise summary.
- Request category suggestion.
- Possible related task.
- Suggested next steps.
- Missing context to ask for.

Allow the engineer or manager to correct the result.

## Capability 3: Handover generation

Input: Task data, project documentation, previous updates, dependencies, pending approvals, and optional handover notes.

Output: The structured handover brief described earlier.

Use only data the requesting user is authorized to access.

## Capability 4: Risk explanation

The rules engine identifies potential delivery risk. Gemini explains it in plain language using the evidence provided.

The AI must distinguish:

- Verified facts.
- Rule-derived findings.
- Hypotheses.
- Recommendations.

Do not allow Gemini to invent task statuses, dates, approvals, or dependencies.

### Structured output

Use Pydantic schemas or equivalent validation for every important AI response.

If the response is invalid, retry safely or fall back to a deterministic message.

### Prompt-injection protection

Treat user-submitted descriptions, imported documents, and task comments as untrusted data. They must not override system instructions, authorize data access, or trigger actions.

---

# 10. Notification Engine

Implement an event-driven notification mechanism.

Relevant events include:

- New support request.
- New approval request.
- Pending action approaching its deadline.
- Explicit blocker created.
- A task becoming overdue.
- A critical dependency becoming blocked.
- Handover requiring manager review.
- Handover approved.
- Backup assignment accepted.

Each notification must contain:

- Recipient.
- Reason.
- Priority.
- Related record.
- Suggested action.
- Creation timestamp.

Implement deduplication and resolution.

For the MVP, in-app notifications with polling or refresh are sufficient. Real email, Slack, and push integrations are optional future work.

Do not send external notifications automatically unless explicitly configured and authorized.

---

# 11. User Interface Requirements

Build a polished, coherent application with consistent spacing, typography, colors, component styles, empty states, loading states, and error handling.

Avoid oversized decorative components, fake charts, dead buttons, and unnecessary animations.

## Main navigation

- Overview.
- Projects.
- My Work.
- Support Requests.
- Action Inbox.
- Handovers.
- Notifications.
- Settings, if needed.

Show only relevant navigation for each role.

## Manager overview

Include:

- Project health.
- Tasks requiring attention.
- Pending approvals.
- Open support requests.
- Upcoming milestones.
- Handover coverage.
- Recent activity.
- AI-generated daily briefing.

Clicking a summary card should open the relevant filtered list.

## Engineer workspace

Include:

- My tasks.
- My blockers.
- My requests.
- Pending responses.
- Upcoming deadlines.
- Availability and handover.
- Recent notifications.

## Action inbox

Make it easy to distinguish:

- Urgent and time-sensitive actions.
- Blocked work.
- Approvals.
- Support requests.
- Routine follow-ups.

Provide filters for project, priority, status, and owner.

## Handover interface

Show:

- Affected tasks.
- Downstream dependencies.
- Candidate recommendations.
- Reasons and scoring breakdown.
- Generated handover brief.
- Missing information.
- Approve and reject actions.

Clearly distinguish recommendations from confirmed assignments.

## Visual design

Use a professional modern SaaS style. A restrained navy, blue, and neutral palette is appropriate.

The UI should look credible in a competition demo, work at desktop and mobile sizes, and communicate important states clearly.

---

# 12. Security and Responsible AI

Implement the following safeguards:

- Enforce authorization in backend endpoints and database access.
- An engineer must not see another engineer's private support requests unless explicitly authorized.
- Managers may access work-related information only for their authorized teams.
- Do not expose private leave reasons.
- Do not implement keystroke monitoring, screen tracking, hidden surveillance, or arbitrary employee productivity scores.
- Do not use AI to make automatic performance judgments.
- Human approval is required for critical work reassignment.
- Record who approved a handover or changed an important action.
- Avoid logging secrets, private request details, or unnecessary personal data.
- Clearly label synthetic demo data.
- Disable development authentication and seed-reset functionality in production.
- Use environment variables for secrets.
- Apply reasonable input validation, output validation, and error handling.

The system should support employees rather than penalize them for reporting blockers or requesting help.

---

# 13. Testing Requirements

Write automated tests for the most important business logic.

At minimum, test:

1. An approval request creates a tracked action item.
2. An unresolved request remains visible after its notification is read.
3. A blocked task with downstream dependencies is identified.
4. A task being old does not automatically classify its owner as underperforming.
5. Duplicate events do not create duplicate notifications.
6. An engineer cannot access unauthorized requests.
7. Backup candidates are ranked using the defined criteria.
8. Ineligible candidates cannot be selected for assignment.
9. A manager must approve a handover before the assignment is finalized.
10. The generated handover contains required fields.
11. Missing information is explicitly identified.
12. AI failure does not corrupt or delete existing work records.
13. Malformed AI output is rejected or safely handled.
14. The manager can resolve an action and the engineer can see the updated state.
15. The application starts successfully in local development mode.

Include frontend tests for important interactions where practical.

Use synthetic data with known expected results to evaluate risk detection and candidate ranking.

---

# 14. Deployment and Configuration

The application must work locally before deployment.

Provide:

- README.md with setup instructions.
- `.env.example` with placeholder values only.
- Frontend and backend dependencies.
- Seed script.
- Dockerfile.
- `.dockerignore`.
- Firestore setup instructions.
- Gemini configuration instructions.
- Google Cloud deployment instructions.
- Automated tests.
- Architecture documentation.
- Troubleshooting instructions.

Never commit real API keys, credentials, or service-account files.

For deployment:

1. Build the frontend.
2. Build the backend container.
3. Configure production environment variables and secrets.
4. Configure Firestore permissions and authentication.
5. Deploy the container to Cloud Run.
6. Verify the health endpoint.
7. Verify the core dashboard and AI workflows.
8. Document the deployment URL only after successful deployment.

Do not claim that deployment succeeded unless it was actually completed and verified.

If Google Cloud credentials are unavailable, complete the application locally, prepare deployment configuration, and clearly document the remaining steps.

---

# 15. Competition Submission Deliverables

Prepare the following after the application works.

## A. Proposal PDF content

Create a concise proposal covering:

1. Problem statement.
2. Target users.
3. Proposed solution.
4. Product workflow.
5. Meaningful use of Gemini.
6. Architecture.
7. Technical feasibility.
8. Scalability.
9. Security and responsible AI.
10. Expected impact.
11. Evaluation results.
12. Future roadmap.

Do not invent market statistics, customer testimonials, adoption, or impact measurements.

## B. Three-minute demo script

Structure the demo as:

- 0:00–0:25 — Explain the manager coordination problem.
- 0:25–0:55 — Show the manager dashboard and a pending approval.
- 0:55–1:25 — Show an engineer reporting a blocker and the manager responding.
- 1:25–2:20 — Simulate emergency leave, show dependency analysis, candidate recommendations, and the generated handover.
- 2:20–2:45 — Show notifications and action tracking.
- 2:45–3:00 — Explain Gemini's role, responsible AI safeguards, and the potential impact.

## C. Evaluation report

Report actual results from your synthetic test set, including:

- Blocker and risk detection results.
- Candidate eligibility and ranking results.
- Handover field completeness.
- Invalid AI output handling.
- Notification deduplication.
- Known limitations.

Clearly distinguish synthetic evaluation from real-world validation.

---

# 16. Suggested Project Structure

Use a maintainable structure similar to:

teampulse-ai/
- frontend/
  - src/
    - components/
    - pages/
    - layouts/
    - hooks/
    - services/
    - types/
  - package.json
- backend/
  - app/
    - api/
    - models/
    - schemas/
    - services/
    - repositories/
    - rules/
    - ai/
    - notifications/
    - core/
  - tests/
  - requirements.txt
- scripts/
  - seed_demo_data.py
- docs/
  - architecture.md
  - evaluation.md
  - demo_script.md
  - proposal.md
- Dockerfile
- .dockerignore
- .env.example
- README.md

Adjust the structure if the repository or chosen framework benefits from a different arrangement.

Keep the AI service, notification service, rules engine, and database access separate enough to test independently.

---

# 17. Implementation Order

Follow this order and continue through implementation rather than stopping after the plan.

### Phase 1 — Inspect and scaffold

- Inspect the repository and available tooling.
- Establish a working frontend and backend.
- Define schemas and environment configuration.
- Add sample data and a local development mode.
- Verify that the application starts.

### Phase 2 — Build the core product

- Implement authentication or development personas.
- Implement projects and tasks.
- Build the manager dashboard.
- Build the engineer workspace.
- Implement support requests and the action inbox.
- Add status transitions and in-app notifications.

### Phase 3 — Add operational intelligence

- Implement dependency traversal.
- Implement deterministic delivery-risk rules.
- Implement candidate ranking.
- Implement handover workflows.
- Add Gemini summaries and handover generation.
- Validate structured AI output.

### Phase 4 — Integrate and test

- Connect the frontend to real backend endpoints.
- Verify every major interaction.
- Add authorization checks.
- Test error states and AI failure paths.
- Run automated tests and fix failures.

### Phase 5 — Deploy and document

- Create the production container.
- Configure Firestore and Gemini integration.
- Prepare Cloud Run deployment.
- Verify deployment if credentials are available.
- Complete the README, architecture document, evaluation report, proposal content, and demo script.

After each phase, run relevant tests and resolve problems before proceeding.

---

# 18. Definition of Done

The MVP is complete only when:

- The application runs locally using documented instructions.
- Manager and engineer experiences are both usable.
- Seeded projects and tasks appear correctly.
- Engineers can submit support requests.
- Managers can respond to requests and resolve actions.
- Project dependencies and delivery risks are shown with explanations.
- The dashboard provides useful AI-generated summaries.
- Emergency leave triggers a functioning handover workflow.
- Candidate recommendations include transparent reasons.
- A manager can approve a handover and notify the selected backup.
- Notifications are persisted and deduplicated.
- Authorization is enforced on the backend.
- Critical business logic has automated tests.
- AI failures are handled safely.
- Google Cloud deployment configuration is documented.
- The competition proposal and demo materials are prepared.

## Final instruction

Start by inspecting the repository and identifying the current state of the project. Then implement the MVP end to end.

Do not spend the entire effort polishing the dashboard while leaving the backend mocked. Do not create decorative buttons that do nothing. Do not substitute hardcoded AI responses for actual Gemini integration in the final working version.

Use deterministic demo data where appropriate, but make the application functional, with real state changes, persistent records, meaningful AI capabilities, and clear error handling.

If the full scope cannot be completed in one pass, prioritize this vertical slice first:

**Engineer submits a blocker → manager sees a prioritized action → manager responds → an emergency handover is generated → backup is recommended and approved → notification is delivered.**

Make that scenario reliable before adding optional features.

Begin implementation now.