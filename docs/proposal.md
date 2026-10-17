# TeamPulse AI — proposal

**Never lose track of what your team needs.**
Challenge theme: Future of Work & Enterprise Productivity.

---

## 1. Problem statement

An engineering manager typically supervises several projects and many
engineers. The information needed to run that well is spread across tickets,
pull requests, chat threads, meetings and documents, and none of those systems
knows about the others.

The observable failures are specific and repetitive:

- An engineer requests an approval; it is lost in a thread.
- An engineer is blocked and cannot get time with their manager.
- A manager forgets a promised follow-up or a pending decision.
- A dependency silently puts a delivery milestone at risk.
- An engineer takes emergency leave and nobody knows what needs covering.
- A replacement engineer is given incomplete context and spends hours
  reconstructing it.
- A manager assembles progress reports by hand from several sources.

None of these is a performance problem. They are coordination, visibility and
support problems, and they are the gap between what an engineering organisation
knows and what the person responsible for it can see.

---

## 2. Target users

**Primary — engineering managers** running multiple projects, who need to know
what needs attention today, what is at risk, and what happens when someone is
suddenly unavailable.

**Secondary — engineers**, who need a reliable way to ask for an approval, a
decision or help with a blocker, and to see where that request stands without
chasing anyone.

**Beneficiary — the engineer picking up someone else's work**, who needs the
context that currently lives in the absent person's head.

---

## 3. Proposed solution

TeamPulse AI is an engineering operations dashboard with four integrated
capabilities.

**Project intelligence.** Projects, milestones, tasks and dependencies in one
view, with deterministic detection of overdue work, recorded blockers, blocked
dependency chains, pending decisions that hold up other work, milestones at
risk, and unassigned critical work. Every finding carries the evidence behind it
and links back to the underlying records.

**Engineer support.** Engineers raise blockers, decisions, approvals, one-on-one
requests and progress updates against a specific task, then track them. A
request stays visible until it is resolved or cancelled — reading a notification
never closes it.

**Manager action inbox.** One consolidated, ranked list of everything waiting,
grouped into urgent, blocked work, approvals, support and routine follow-ups.
Each item shows its downstream consequence and a factor-by-factor account of why
it is ranked where it is.

**Intelligent handover.** When someone becomes unavailable, TeamPulse finds the
affected work, walks the dependency graph both ways, collects the milestones,
pending approvals and documentation, ranks eligible backups transparently, and
generates a structured brief. A manager approves and the backup accepts before
any task changes hands.

The product principle: **help managers support engineers and protect delivery
continuity.** Not monitor people.

---

## 4. Product workflow

```
Engineer hits a blocker
  └─ raises a request against the task
      └─ becomes a tracked action item with an owner, priority and deadline
          └─ rules engine scores it by consequence, not arrival time
              └─ manager responds, delegates, or records a durable decision
                  └─ engineer sees the outcome on their own request

Engineer becomes unavailable
  └─ records dates and affected work (never a reason)
      └─ impact analysis: active tasks, dependencies both directions,
         milestones, pending approvals, documents, decisions, updates
          └─ eligibility gate, then transparent weighted ranking
              └─ Gemini writes an eleven-section brief with labelled evidence
                  └─ manager approves and selects a backup
                      └─ backup accepts  →  ownership transfers
```

---

## 5. Meaningful use of Gemini

Gemini is used where language understanding genuinely helps, and nowhere else.
The division is explicit and enforced in code.

| Capability | Input | Output |
| --- | --- | --- |
| Project briefing | Authorised project data, deadlines, dependencies, rules-engine findings | Progress summary, key risks with supporting record ids, blockers, recommended actions, uncertainties |
| Request interpretation | An engineer's written request | Neutral summary, suggested category and priority, probable related task, next steps, missing context |
| Handover synthesis | Task data, documentation, updates, dependencies, pending approvals, optional notes | Eleven-section structured brief with explicit gaps |
| Risk explanation | One rules-engine finding and its evidence | Plain-language explanation, claim by claim |

**What Gemini is not allowed to do.** Deadlines, dependency traversal,
permission checks, eligibility gates, priority scores, severity scores,
assignment approval, status transitions and notification deduplication are all
deterministic Python. The model cannot change an assignment, a status, a
priority or a permission.

**How its output is constrained.** Every response is validated against a
Pydantic schema passed to the model as `response_schema` and re-checked on
return. Every record id it cites is matched against the facts it was given, and
unmatched ids are dropped and reported. A risk note that does not correspond to
a rules-engine finding is relabelled from `verified_fact` to `hypothesis`. Every
statement carries an evidence kind — verified fact, rule-derived, hypothesis or
recommendation — which the UI shows.

**What happens when it fails.** Every capability has a deterministic fallback
that restates what the rules engine established rather than guessing. The UI
labels which produced a given answer. Eight injected failure modes — malformed
JSON, missing fields, invalid enums, `null`, transport failure, rate limiting,
timeout — all degraded safely with no change to any work record.

---

## 6. Architecture

```
React + TypeScript SPA
  └─ FastAPI: authentication → authorization → rules engine → repositories
                                            ↘ Gemini (when reasoning helps)
                                            ↘ notification engine
                                              └─ Firestore
```

One container serves the API and the built frontend on Cloud Run. Data access
goes through a `DocumentStore` abstraction with an in-memory adapter (local
development and the full test suite, no credentials required) and a Firestore
adapter (deployed). The rules engine, notification engine, AI layer and data
access are separated far enough to test independently.

Details in `docs/architecture.md`.

---

## 7. Technical feasibility

Built and running. 130 backend and 47 frontend tests pass, with 90 % statement
coverage of the backend; the container image builds and runs; all three demo
scenarios complete end to end against persisted state. One developer, a conventional Python and
TypeScript stack, no infrastructure beyond Cloud Run, Firestore and the Gemini
API.

Deliberate non-goals that keep it feasible: no microservices, no multi-agent
orchestration, no streaming, no chat interface.

---

## 8. Scalability

**What scales already.** Cloud Run scales to zero and out on demand. Firestore
grows without operational work. No LLM call happens on a dashboard render —
generation is always explicit, and outputs are cached against a fingerprint of
their inputs and invalidated when the underlying data changes. This bounds the
dominant cost.

**What has to change first.** The repository layer currently reads whole
collections and filters in Python — correct at tens of records, wrong at tens of
thousands. The abstraction is the single place where server-side queries go,
and the first composite indexes are already written in
`firestore.indexes.json`. The notification sweep currently runs on dashboard
load; at team scale it becomes a Cloud Scheduler job writing to a queue. The AI
cache would move entirely to Firestore to allow multiple workers per instance.

---

## 9. Security and responsible AI

**Authorization is enforced in the backend** on every endpoint, not by hiding
UI. An engineer cannot read another engineer's support requests — 45 cross-user
read attempts, 45 refused — or see a peer's backup-candidate score. Managers
see work information only for projects they are authorised on.

**Designed not to become surveillance.** No keystroke monitoring, screen
tracking, hidden observation or productivity score exists in the system, and
nothing computes a per-person rating. The only per-person numbers are assigned
hours against weekly capacity, used once, to judge whether someone has room to
take on another person's work.

**A long-running task is never a problem by itself.** Findings come only from
explicit signals — a missed deadline, a recorded blocker, an unresolved
dependency, a pending decision, an approaching milestone, missing ownership on
critical work. `created_at` is not an input to any rule. Measured: a synthetic
task aged from 30 to 720 days with no deadline and no blocker produces zero
findings at every age.

**Unavailability carries no reason.** The data model has no field for a medical
or family reason, the form does not ask, and nothing displays one.

**Reassignment needs two human decisions.** A manager approves and the
nominated backup accepts; only then does ownership move. Both are written to an
audit trail with the actor's id. Eligibility is a hard gate evaluated before
ranking and again at approval — six attempts to approve an ineligible candidate
were all refused, including one whose availability changed after ranking.

**Untrusted input stays untrusted.** Engineer-written text is quarantined in a
separate prompt envelope, stripped of envelope-spoofing markers, explicitly
demoted by the system rules, and — decisively — has no path to any state change.

**Operational hygiene.** Secrets come from the environment and Secret Manager;
logs redact credential-shaped values and never carry request bodies; Firestore
rules deny all direct client access; development authentication and the
seed-reset endpoint are force-disabled when `ENVIRONMENT=production`, verified
inside the built container.

---

## 10. Expected impact

Stated as a mechanism, not a measurement — no real team has used this, and no
impact has been measured.

**A lost approval stops being losable.** A request becomes a tracked item with
an owner, a deadline and a visible downstream consequence, ranked by what it
costs rather than when it arrived.

**An engineer asking for help is visible.** Blockers and decision requests reach
the manager as work items and stay visible until resolved, which removes the
need to chase and the risk of being penalised for asking.

**Delivery risk comes with its reasons.** A manager sees not just that a
milestone is at risk but which task, which dependency and which pending decision
puts it there.

**Sudden absence stops being a scramble.** The affected work, its dependencies,
the eligible backups and a structured brief are produced in one step instead of
assembled by hand over hours — and the gaps are named rather than papered over.

---

## 11. Evaluation results

From the project's own harness on a labelled synthetic dataset
(`python scripts/run_evaluation.py`). Synthetic only; not real-world validation.

| Area | Result |
| --- | --- |
| Automated tests | 130 backend + 47 frontend passed, 90 % backend statement coverage |
| Risk detection | precision 1.00, recall 1.00 (8 expected / 8 found) |
| Quiet tasks wrongly flagged | 0 of 5 |
| Findings from task age alone | 0 across ages 30–720 days |
| Candidate ranking | exact expected order; all 5 factors explained for every candidate |
| Ineligible candidates | 6 of 6 identified with the correct reason, 6 of 6 refused at approval |
| Eligibility re-checked at approval | yes |
| Handover completeness | 8 of 8 briefs with all 11 sections, 11.0 of 11 non-empty |
| Handovers flagging missing information | 4 of 4 |
| Invalid AI output | 8 of 8 degraded safely, 0 cached, 0 records changed |
| Invented record ids kept | 0 of 3 |
| Notification deduplication | 3 created on sweep 1, 0 across sweeps 2–5 |
| Cross-user access refused | 45 of 45 requests, 15 of 15 projects |

Full report, including a correction to the hand-written expectation set and the
known limitations, in `docs/evaluation.md`.

---

## 12. Future roadmap

**Next** — integrations that remove manual entry: GitHub pull requests and
issues, Jira, Slack and Google Calendar as *sources*, so TeamPulse reflects work
that already happened instead of asking someone to re-enter it.

**Then** — move the repository layer to server-side queries with the documented
indexes; move the notification sweep to Cloud Scheduler; extend the frontend
tests from components to the pages themselves.

**After that** — optional outbound notifications (email, Slack, push), explicitly
configured and authorised rather than on by default; a team-level retrospective
view of where delivery risk actually materialised, to calibrate the severity and
candidate weights against outcomes rather than intuition.

**Explicitly not on the roadmap** — individual productivity scoring, activity
monitoring, automatic reassignment without human approval, and any use of
protected characteristics or inferred personality in candidate ranking.
