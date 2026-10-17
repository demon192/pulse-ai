# Evaluation report

All numbers below were produced by running the project's own harness against a
labelled synthetic dataset, on 17 October 2026:

```bash
pytest                                  # from backend/
python scripts/run_evaluation.py        # from the repository root
```

> **This is a synthetic evaluation.** The dataset is a fictional organisation
> defined in `backend/app/demo/seed.py`, and the expectations are hand-written
> from that seed data. It demonstrates that the deterministic rules behave as
> specified. It is **not** evidence of real-world accuracy, and nothing here has
> been validated against a real engineering team.

---

## 1. Automated test suite

| Metric | Result |
| --- | --- |
| Tests | **129 passed, 0 failed** |
| Runtime | 2.55 s |
| Statement coverage (`backend/app`) | **90 %** |

Coverage by the modules that carry the business logic:

| Module | Coverage |
| --- | --- |
| `rules/prioritization.py` | 100 % |
| `rules/risk.py` | 97 % |
| `rules/dependencies.py` | 93 % |
| `rules/candidates.py` | 89 % |
| `services/handovers.py` | 91 % |
| `services/authz.py` | 90 % |
| `notifications/service.py` | 90 % |
| `ai/service.py` | 91 % |
| `repositories/firestore.py` | 0 % |

`repositories/firestore.py` is uncovered by design: the suite runs entirely
against the in-memory store so it needs no cloud credentials. That adapter is a
thin pass-through to the Google client and is exercised only by running against
the emulator or a real project.

Tests by area: authorization 26, handover workflow 17, AI layer 18,
dashboards 11, requests 10, candidate ranking 10, notifications 9,
prioritisation 9, risk rules 8, startup 7, dependencies 4.

Every case the product brief asks for is covered, and each has a named test:

| # | Required behaviour | Test |
| --- | --- | --- |
| 1 | An approval request creates a tracked action item | `test_approval_request_creates_a_tracked_action_item` |
| 2 | An unresolved request survives its notification being read | `test_unresolved_request_survives_the_notification_being_read` |
| 3 | A blocked task with downstream dependencies is identified | `test_blocked_task_with_downstream_dependencies_is_identified` |
| 4 | Task age does not classify its owner as underperforming | `test_task_age_alone_produces_no_finding_and_no_owner_judgement` |
| 5 | Duplicate events do not create duplicate notifications | `test_duplicate_event_does_not_create_a_second_notification` |
| 6 | An engineer cannot access unauthorised requests | `test_engineer_cannot_read_another_engineers_request` |
| 7 | Candidates are ranked by the defined criteria | `test_ranking_uses_the_defined_criteria` |
| 8 | Ineligible candidates cannot be selected | `test_ineligible_candidate_cannot_be_approved` |
| 9 | A manager must approve before the assignment is final | `test_manager_approval_then_backup_acceptance_transfers_ownership` |
| 10 | The handover contains the required fields | `test_generated_brief_has_every_required_section` |
| 11 | Missing information is explicitly identified | `test_missing_information_names_specific_gaps` |
| 12 | AI failure does not corrupt existing records | `test_transport_failure_degrades_without_touching_records` |
| 13 | Malformed AI output is rejected or handled safely | `test_malformed_output_is_rejected_and_degraded` |
| 14 | A manager resolves and the engineer sees it | `test_manager_resolves_action_and_engineer_sees_the_outcome` |
| 15 | The application starts in local development mode | `test_health_endpoint_is_public`, `test_demo_data_is_loaded` |

---

## 2. Blocker and delivery-risk detection

Eight findings were expected for the payments project, hand-written from the
seed data before running the engine.

| Metric | Result |
| --- | --- |
| Expected findings | 8 |
| Produced | 8 |
| True positives | 8 |
| Missed | 0 |
| Unexpected | 0 |
| **Precision** | **1.00** |
| **Recall** | **1.00** |
| Findings carrying linked evidence | 8 / 8 |
| Findings carrying a suggested action | 8 / 8 |

The eight: one overdue task (`pay-01`, two days past its date), one blocked
dependency chain (`pay-02`, with `pay-03` waiting on it), one blocked task with
nothing downstream (`pay-05`), two pending decisions holding up work
(`act-001`, `act-002`), one unassigned high-priority task (`pay-07`), and two
milestones at risk (`ms-pay-1` three days out with blocked and overdue work in
scope; `ms-pay-2` with a blocked task in scope).

**A correction worth recording.** The first run reported `act-002` as an
"unexpected" finding, precision 0.875. On review the finding was correct — it is
the open blocker decision Diego is waiting on for `pay-05` — and the
hand-written expectation set had simply missed it. The expectation was added
and the omission is noted in `scripts/run_evaluation.py`. The 1.00 above
therefore reflects a corrected expectation, not a changed rule.

### Quiet tasks stay quiet

Five open tasks with no missed deadline, no recorded blocker, no unresolved
dependency and no imminent milestone were checked.

| Metric | Result |
| --- | --- |
| Quiet tasks checked | 5 |
| Named as the subject of a finding | **0** |
| Listed only as milestone context | 2 (`pay-04`, `pay-06`) |

The two appear in `ms-pay-2`'s finding as remaining scope — "3 of 4 tasks still
open" — not as a claim about those tasks. The first version of this metric
counted any appearance as a flag; it was corrected to distinguish a finding's
subject from the context it lists.

### Task age is never a signal

| Task age (days) | Findings |
| --- | --- |
| 30 | 0 |
| 90 | 0 |
| 180 | 0 |
| 365 | 0 |
| 720 | 0 |

A task with no due date, no blocker and no dependents produces nothing at any
age. The same task given a due date three days in the past produces exactly one
finding, `overdue_task`, whose summary names the deadline and not the owner.

---

## 3. Backup candidate eligibility and ranking

Rhea Kapoor's two open payments tasks (`pay-02`, `pay-04`) require the skills
`backend`, `python` and `payments`. Ten candidates were ranked.

| Metric | Result |
| --- | --- |
| Expected eligible ranking | `eng-001, eng-002, eng-003, eng-007` |
| Actual eligible ranking | `eng-001, eng-002, eng-003, eng-007` |
| **Exact order match** | **yes** |
| Expected ineligible | 6 |
| Actual ineligible | 6 |
| Ineligible set exact match | yes |
| Ineligible with the correct blocking reason | 6 / 6 |
| Ineligible carrying a score of zero | 6 / 6 |
| Eligible candidates with all 5 factors explained | 4 / 4 |

Scores and the reasoning behind the top two:

| Candidate | Score | Why |
| --- | --- | --- |
| Arjun Mehta | 84.0 | 3/3 skills (30), 90 % familiarity (22.5), available (20), 90 % utilised so almost no headroom (1.5), authorised (10) |
| Lena Fischer | 72.5 | 2/3 skills (20), 60 % familiarity (15), available (20), 50 % headroom (7.5), authorised (10) |
| Diego Alvarez | 43.75 | 0/3 skills, 40 % familiarity, available, some headroom |
| Tom Bergqvist | 42.0 | 0/3 skills, 30 % familiarity, available, some headroom |

The gap between Arjun and Lena is informative rather than decisive: Arjun knows
the work far better, Lena has four times the spare capacity. That is exactly
the judgement the product leaves to the manager.

Blocking reasons, each stated to the manager:

| Candidate | Reason |
| --- | --- |
| Mei Tanaka, Samuel Okafor, Nora Haddad, Aisha Khan | No access authorisation for `proj-payments` |
| Victor Oliveira | Availability is `on_leave`, not assignable |
| Priya Raman | Only engineers can be assigned task ownership |

### Ineligible candidates cannot be assigned

| Metric | Result |
| --- | --- |
| Approval attempts with an ineligible candidate | 6 |
| Refused | **6 / 6** |
| Eligibility re-checked at approval time | yes |
| Assignment left unset after every refusal | yes |

The re-check matters: a candidate marked `on_leave` *after* ranking but before
approval is still refused, because `check_eligibility` is the single source of
truth and runs again at approval.

### Factors deliberately excluded

Protected personal characteristics, inferred personality, private leave reasons
and performance scores are not inputs to any of the five factors, and no such
field exists in the data model. The weights (30/25/20/15/10) are initial,
tunable values chosen for this MVP — **not** validated industry standards.

---

## 4. Handover brief completeness

Four engineers were made unavailable in turn; the system analysed the impact and
generated briefs for their highest-impact tasks.

| Metric | Result |
| --- | --- |
| Handovers analysed | 4 |
| Briefs generated | 8 |
| Required sections per brief | 11 |
| **Briefs containing all 11 sections** | **8 / 8** |
| Mean non-empty sections per brief | **11.0 / 11** |
| Sections citing a source record | 56 |
| Handovers flagging missing information | **4 / 4** |
| Missing-information items per handover | 5, 13, 9, 9 |

These briefs were produced on the **deterministic fallback path** (no Gemini key
in the evaluation environment), which is the stricter test: it shows the
required structure survives total AI unavailability. When Gemini is configured,
grounding fills any section the model omits from stored records and reports
which ones it filled.

Gaps are named specifically rather than generically — "No next step is recorded
on 'Payment retry policy'", "No progress updates have been written for 'Payment
retry policy'", "Remaining effort is not estimated". A brief is produced even
when the engineer wrote no handover notes, and says so.

---

## 5. Invalid and hostile AI output

Eight failure modes were injected through a stub client.

| Metric | Result |
| --- | --- |
| Cases | 8 |
| Degraded safely to a deterministic answer | **8 / 8** |
| Returned a usable answer to the caller | **8 / 8** |
| Invalid output written to the cache | **0 / 8** |
| Work records unchanged | **yes** |

Cases: a reply missing a required field; wrong field types; an invalid enum
value; an empty object; `null`; a transport failure; a 429 rate limit; a
timeout. Record counts before and after were identical — 19 tasks, 5 requests,
5 actions, 3 decisions, 7 updates.

### Output grounding

| Metric | Result |
| --- | --- |
| Invented record ids supplied by the model | 3 |
| Invented ids kept | **0** |
| Valid ids kept | `pay-02` |
| Risk note with no matching rule, relabelled to `hypothesis` | yes |
| Grounding notes surfaced to the caller | 2 |

### Prompt injection

| Metric | Result |
| --- | --- |
| Envelope-spoofing probes | 4 |
| Markers neutralised | **4 / 4** |

Probes attempted to close the untrusted envelope, forge a `<facts>` block,
override instructions, and claim administrator authority. Marker stripping is
one layer; the untrusted text is also quarantined in a separate envelope after
the facts, the system rules demote it explicitly, and — most importantly — the
model has no path to change an assignment, status, priority or permission. All
of those are deterministic code behind authorization checks.

---

## 6. Notification deduplication

The sweep was run five times over an unchanged workspace.

| Metric | Result |
| --- | --- |
| Seeded notifications | 3 |
| Created on sweep 1 | 3 |
| Created on sweeps 2–5 | **0** |
| Total notifications | 6 |
| Distinct deduplication keys | 6 |
| Duplicate open keys | **0** |

An unresolved item escalates instead of repeating: at most once per 24 hours, at
most three times, and only when it has become more urgent. A test walks a
notification from `low` to `critical` across four days and asserts the same
record is updated rather than a new one created.

---

## 7. Authorization

Every cross-user access the seeded workspace allows was attempted directly
against the authorization layer.

| Metric | Result |
| --- | --- |
| Cross-user support-request reads attempted | 45 |
| Refused | **45 / 45** |
| Unauthorised project reads attempted | 15 |
| Refused | **15 / 15** |

At the HTTP layer, 26 authorization tests confirm the same decisions through the
API: an engineer cannot read another engineer's request, filter by another
engineer's id to see their data, respond on their behalf, read a project they
are not authorised on, edit a task they do not own, create an action item, open
the manager dashboard, act on another user's notification, or see a peer's
backup-candidate score. A manager cannot delegate an action to someone
unauthorised on its project.

---

## 8. Scenario verification

All three required scenarios were driven through the running application and
confirmed against persisted state, not mocks.

**Scenario 1 — the lost approval.** `req-001` sat open for three days; the
action inbox ranked it first at score 92 and stated the consequence ("2
dependent task(s) cannot proceed; 'Settlement API GA' is 3.0 day(s) away"). The
manager responded and resolved it with a recorded decision. Verified after:
`act-001` resolved, `req-001` resolved with the manager's notes, decision record
`dec-…` written and linked to `pay-01`, the engineer notified, and an audit
entry naming `mgr-001` as the resolver.

**Scenario 2 — an engineer needs help.** `req-002` (Diego, blocked on ambiguous
declined-card messaging) was linked to `pay-05` and `proj-payments`,
interpreted, surfaced in the inbox as blocked work, answered, and the response
appeared on Diego's own request with a notification.

**Scenario 3 — emergency leave.** Rhea recorded unavailability with no handover
notes. The analysis found 2 active tasks, 2 downstream dependencies, `pay-01`
as the upstream blocker, 2 at-risk milestones, the pending `act-001` approval
and 3 relevant documents; ranked 4 eligible and 6 ineligible candidates with
full breakdowns; and generated two 11-section briefs. The manager approved with
Arjun selected — ownership did **not** move at that point. Arjun accepted, and
only then did `pay-02` and `pay-04` transfer to him. The audit trail recorded
create (eng-008), analyze (eng-008), approve (mgr-001) and accept (eng-001).

### Deployment artifacts

The container image was built and run locally and behaved correctly in both
modes:

| Check | Result |
| --- | --- |
| `docker build` | succeeds |
| `/health` in the container | `{"status":"ok", ...}` |
| SPA served, client route `/handovers` after reload | 200 |
| Manager dashboard through the container | 5 inbox items, 3 projects |
| With `ENVIRONMENT=production`: dev persona header | **401** |
| With `ENVIRONMENT=production`: `POST /api/admin/seed` | **404** |
| With `ENVIRONMENT=production`: no credentials | **401** |
| With `ENVIRONMENT=production`: auth mode in startup log | `auth=firebase` |

---

## Known limitations

**Not validated against reality.** Every number here comes from synthetic data
with hand-written expectations. No real team has used this.

**Gemini has not been exercised against the live API.** No API key was available
in the build environment. The integration is real — correct SDK surface,
response schemas, retries, timeouts, grounding — and is tested through an
injected client covering success, malformed output, invalid enums, transport
failure, rate limiting and timeouts. But the prompts have not been run against
the actual model, so output quality is unmeasured. The deterministic fallback
path, which is what the evaluation above measured, is fully exercised.

**Not deployed.** Cloud Run configuration is complete and the image is verified
locally, but no Google Cloud credentials were available, so deployment was not
executed and there is no URL to report.

**Risk weights are guesses.** The severity formula and the 30/25/20/15/10
candidate weights were chosen to produce sensible orderings on this dataset.
They are tunable starting points, not calibrated against outcomes.

**Precision is measured on one project.** Eight findings on `proj-payments`.
A larger and more varied dataset would likely expose rules that are too eager
or too quiet — the pending-decision rule, which fired on both `act-001` and
`act-002`, is the most likely candidate for producing near-duplicate findings
alongside a blocked-task finding about the same work.

**Firestore adapter is untested in CI.** 0 % coverage; verified only by reading
against the abstraction's contract.

**Scale is untested.** Reads load whole collections and filter in Python, which
is correct for ~50 records and wrong for 50,000. The repository abstraction is
where server-side queries go, and the first indexes are documented, but no load
testing has been done.

**No frontend test suite.** The UI is type-checked (`tsc -b` with `strict`) and
every interaction was driven manually through the running application, but there
are no automated component tests. That is the largest gap in the test coverage.

**Single-worker caching.** The AI summary cache is persisted, but the Cloud Run
configuration runs one worker per instance so that in-process state stays
coherent. Multi-worker deployment would need the cache reads to go through
Firestore on every request.
