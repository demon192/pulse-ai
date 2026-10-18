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
| Backend tests | **138 passed, 0 failed** (2.1 s) |
| Frontend tests | **47 passed, 0 failed** (2.27 s) |
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
| `ai/service.py` | 96 % |
| `ai/client.py` | 70 % |
| `repositories/firestore.py` | 0 % |

`repositories/firestore.py` is uncovered by design: the suite runs entirely
against the in-memory store so it needs no cloud credentials. That adapter is a
thin pass-through to the Google client and is exercised only by running against
the emulator or a real project.

Backend tests by area: authorization 26, handover workflow 17, AI layer 18,
dashboards 11, requests 10, candidate ranking 10, notifications 9,
prioritisation 9, risk rules 9, startup 7, dependencies 4.

Frontend tests cover the interactions where a wrong rendering would mislead a
manager: the candidate list (7 — eligible and ineligible kept apart, no way to
select an ineligible candidate, the scoring breakdown visible, the "no eligible
candidate" message), the handover brief (6 — all eleven sections present,
evidence kinds labelled, missing information shown, provenance stated), the
action inbox row (7 — consequence stated, server-computed due label, blocked
tasks named), the risk card (7 — evidence and suggested actions shown, no model
call until asked, provenance labelled, a failed explanation does not hide the
finding), the task row (7 — blocker reason, dependency, next step, and no
language characterising the owner), the request submission flow (6 — tracked as
an action item, the AI reading shown as a suggestion the engineer can correct,
failures reported without losing input), and the API client (7 — persona header,
query serialisation, error detail, field errors, unreachable backend).

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

Re-run on 18 October 2026 after the sign-in work, against the rebuilt image:

| Check | Result |
| --- | --- |
| `docker build` with the Firebase SDK added | succeeds |
| `/health` | `environment=production`, `ai_configured` reflects the key |
| `GET /api/auth-config` | `sign_in_configured: true`, `dev_personas_enabled: false` |
| Auth domain with only `FIREBASE_PROJECT_ID` set | derived as `<project>.firebaseapp.com` |
| `GET /api/session` with no token | **401** |
| `GET /api/session` with a dev persona header | **401** |
| `POST /api/admin/seed` | **404** |
| SPA at `/` in Firebase mode | renders sign-in; only `/api/auth-config` is requested |

---

## 9. Live Gemini output

Measured on 17 October 2026 against the Gemini Developer API, model
`gemini-3.6-flash`, from a local instance (`DATA_BACKEND=memory`,
`GET /api/session` reporting `ai_configured: true`). This section replaces an
earlier limitation stating that the model had never been called.

All four capabilities were measured, the handover brief a day later than the
rest: the key's free tier allows 20 `generateContent` requests per day for this
model, and diagnosing the defect below consumed the first day's allowance.

### A defect that made every live call degrade

The first live call returned a deterministic fallback, not a model answer.
Gemini 3.x models think before answering and **thought tokens are drawn from the
same budget as `max_output_tokens`**. At the shipped budget the thinking ate it:

| Configuration | `finish_reason` | Thought tokens | Content tokens | Usable |
| --- | --- | --- | --- | --- |
| 2048, thinking uncapped *(as shipped)* | `MAX_TOKENS` | 1965 | 68 | **no — truncated JSON** |
| 2048, thinking `LOW` | `STOP` | 0 | 1091 | yes |
| 2048, thinking `MINIMAL` | `STOP` | 0 | 872 | yes |
| 4096, thinking uncapped | `STOP` | 2116 | 997 | yes, with 52 % spent on thoughts |
| 4096, thinking `LOW` | `STOP` | 0 | 1102 | yes |

The project briefing prompt is ~5950 input tokens, so this was not a marginal
overrun: the reply was cut off mid-object every time, `_extract_json` raised,
and the service degraded. **The test suite could not catch this** — it injects a
stub client, which has no token accounting, so the failure only exists against
the real API.

Fixed in three places:

- `gemini_thinking_level` (default `low`, `GEMINI_THINKING_LEVEL`) caps thinking
  so it cannot starve the structured reply. These capabilities summarise facts
  the rules engine has already derived; they do not need deep reasoning.
- The client now detects `finish_reason == MAX_TOKENS` and raises
  `AIOutputTruncated` rather than reporting a generic schema failure, **and
  doubles the budget on retry** (capped at 8192) instead of repeating a call
  that cannot fit.
- Four tests cover truncation, retry widening, the thinking cap and handing the
  cap back to the model (`gemini-thinking-level=unspecified`).

A second, unrelated bug surfaced on the way: `.env.example` could not be loaded
at all. `cors_allow_origins` is a `list[str]`, so the dotenv source tried to
JSON-decode `CORS_ALLOW_ORIGINS=http://localhost:5173,...` and raised before the
field validator that splits it ever ran. Anyone following the README's
`cp .env.example .env` hit a startup crash. The field is now annotated
`NoDecode`.

### What the model actually produced

After the fix, with `force_refresh=true` so nothing came from cache:

| Capability | Endpoint | Latency | `meta.source` | Grounding notes |
| --- | --- | --- | --- | --- |
| Project briefing | `POST /api/ai/project-briefing` (`proj-payments`) | 10.9 s | `gemini` | none |
| Request interpretation | `POST /api/ai/request-summary` (`req-002`) | 2.5 s | `gemini` | none |
| Risk explanation | `POST /api/ai/risk-explanation` (`risk-blocked-pay-02`) | 2.3 s | `gemini` | none |
| Handover brief | `POST /api/handovers/{id}/analyze` | 9.9 s | `gemini` | none, after the prompt fix below |

"Grounding notes: none" is a measured result, not an absence of checking: the
service drops any cited record id that does not literally appear in the facts
and reports how many it dropped. **Across all three capabilities it dropped
zero.** Every id the model cited was real.

**Fact-checked claim by claim** against the exact facts payload each prompt
received (dumped from `app.services.facts` and compared by hand):

- *No invented dates, statuses, approvals or dependencies.* Every specific claim
  traced back. "Passed its deadline on 2026-10-15 and remains open in
  'in_review' status" matches `pay-01` exactly. "Waiting 3 days and blocks 2
  dependent tasks" matches `risk-pending-act-001`. "Targeted in 3 days with 0 of
  3 tasks completed" matches `ms-pay-1`. The two blocker explanations paraphrase
  the recorded `blocked_reason` text on `pay-02` and `pay-05` without
  embellishment.
- *`key_risks` tracked the rules engine.* Exactly 8 notes for the 8 findings,
  one each, none invented — so the grounder's "relabelled as hypothesis" path
  never fired.
- *`blockers` stayed literal.* Only `pay-02` and `pay-05`, the two tasks whose
  recorded status is `blocked`. It did **not** include `pay-01`, which is
  overdue and in review but not blocked — the distinction the prompt asks for.
- *Task age was not used as evidence.* No statement reasoned from how long a
  task had existed. The durations that do appear ("waiting 3 days", "waiting 1
  day") are pending-decision ages supplied by the rules engine as finding
  evidence, which is what the prompt permits.
- *No assessment of people.* The briefing names no engineer at all, despite
  owner names being present in the facts.
- *Untrusted text was summarised, not obeyed.* The `req-002` description is
  engineer-authored text inside the `<untrusted_content>` envelope; the model
  reported the spec-versus-compliance conflict and grounded
  `suggested_task_id` to `pay-05`, a real candidate task.

**`evidence_kind` was used correctly, with one soft edge.** All 8 `key_risks`
came back `rule_derived` and both `blockers` `verified_fact`, both as
instructed. In the risk explanation, three of four statements are right
(`verified_fact` for the recorded blocker, `rule_derived` for the detection,
`recommendation` for the suggested action). The fourth — "'Settlement
reconciliation UI' depends on 'Implement settlement worker' and cannot proceed"
— is labelled `verified_fact`. The dependency is a recorded fact, but "cannot
proceed" is an inference layered on top of it, so `rule_derived` would be the
honest label. The prompt does not currently say what to do with a claim that
mixes a recorded fact and an inference. Left as measured rather than tuned away,
since one sample is not enough to justify a prompt change.

The same response contained one cosmetic artifact: "the API contract contract
blocker".

### Schemas needed no changes; two prompt rules did

The three capabilities above needed no prompt changes. The handover brief
needed two, both recorded in the subsection above: untrusted text was being
labelled `verified_fact`, and the `dependencies` section ignored the
`dependents` direction. Neither was visible until a prompt put substantial
engineer-authored text in front of the model.

The response schemas translated cleanly to the model's JSON-schema dialect. The
Pydantic classes pass straight to `response_schema`, and `response.parsed`
returned a populated `ProjectBriefingAI` — so the SDK validated server-side
against the same schema. The deliberate avoidance of optionals and free-form
maps paid off: the two enum fields (`RequestCategory`, `Priority`) and the
`HandoverSectionKey` enum round-tripped without a single validation failure. No
schema change is needed.

### The handover brief, and two prompt defects it exposed

Measured 18 October 2026 against the same model. `POST /analyze` generates one
brief per affected task, two per analysis, so this is the only capability that
issues two model calls per request.

Both briefs came back from the model with **all 11 required sections present and
none filled deterministically** — the grounder's "Filled from stored records
because the model omitted them" note did not fire. Section 4 measured that the
fallback can always produce a complete brief; this measures that the model does
too.

Fact-checking it against the facts payload surfaced two defects that the other
three capabilities could not, because the handover brief is the only prompt that
puts substantial engineer-authored text in front of the model:

**1. Untrusted text was being promoted to verified fact.** For `pay-04` the
model wrote "Backoff has been implemented per the RFC." and labelled it
`verified_fact` with an empty `source_ids`. The claim is not invented — it comes
from task update `upd-004`, "Backoff implemented per the RFC. Still need the
sandbox benchmark before enabling it in staging." But that update arrives inside
`<untrusted_content>`: it is the absent engineer's own report, and nothing has
checked it. For a handover brief this is the most consequential label in the
document, because an incoming engineer who reads "verified fact" will not
re-verify the work.

The cause was a gap in the prompt's own taxonomy. `verified_fact` was defined as
"stated directly in <facts>" and no category described "someone wrote this down
and nobody checked it", so the model reached for the closest fit. The rule now
says plainly that a statement resting on `<untrusted_content>` is never a
`verified_fact`, "however confidently that text asserts it: someone wrote it,
nothing checked it", and must be attributed in the prose.

**2. A recorded dependency was reported as absent.** `pay-04`'s `dependencies`
section read "Not recorded in TeamPulse." and was labelled `hypothesis`, while
the facts carried `dependents: [pay-06]`. The facts expose the two directions as
separate keys — `dependencies` (what this task waits on, empty here) and
`dependents` (what waits on it, `pay-06`) — and the prompt named neither, so the
model answered on the key that shares the section's name. For a handover this
under-reports the blast radius: the incoming engineer is not told that the
gateway sandbox load test is waiting on them.

After both fixes, re-measured on the same data:

| Section | Before | After |
| --- | --- | --- |
| `pay-04` work_completed | `verified_fact`, no citation, stated as fact | `hypothesis`, cited, "In task update upd-004, Rhea Kapoor reported that…" |
| `pay-04` dependencies | `hypothesis`, "Not recorded in TeamPulse." | `verified_fact`, cites `pay-06`, names it as the downstream dependent |
| `pay-02` work_completed | `hypothesis`, no citation | `hypothesis`, cited, attributed to the named engineer |
| `missing_information` label | `verified_fact` on one task, `recommendation` on the other | `recommendation` on both |
| Unverifiable references dropped | **1** | **0** |

The regenerated `missing_information` also became the right kind of sharp:
"Verification of committed/merged code reported in task update `upd-004`" — the
brief now tells the incoming engineer exactly which claim is a self-report
awaiting confirmation.

**A structural limitation this exposed, not fixed.** `collect_ids` builds the
citation allow-list by walking `facts` only, so the id of an untrusted item is
not citable: a correctly-sourced claim from task update `upd-004` cannot cite
`upd-004` without the grounder stripping it as unverifiable — which is what the
single dropped reference in the first run was. The prompt now works around this
by requiring attribution in the prose, so provenance survives in the text even
though the structured citation cannot. The clean fix is for the envelope's own
item ids to join the allow-list, since TeamPulse constructs them and they are
not model-invented. That changes grounding semantics the current tests assert,
so it is recorded here rather than done.

### Free-tier quota is the operative constraint

Of ~20 live requests, **6 returned `503 UNAVAILABLE`** ("model is currently
experiencing high demand") and the rest were spread across diagnosis. The daily
allowance then ran out:

```
Quota exceeded for metric: generate_content_free_tier_requests,
limit: 20, model: gemini-3.6-flash ... Please retry in 7h17m30s
```

Two consequences, both unresolved:

- **The handover brief is still unmeasured against the live model.** It is the
  largest prompt — eleven sections per task, two tasks per analysis, so two
  calls per `POST /analyze` — and the most likely to need a budget above the
  4096 it currently asks for. Both attempts returned all 11 sections, but filled
  deterministically from stored records, with `meta.notes` reporting
  `AIUnavailable`. That the fallback produces a complete brief is worth
  something, and is what section 4 already measured; it is not a measurement of
  the model.
- **The retry policy is wrong for quota errors.** `429` matches the transient
  marker list, so the client retries three times with 0.5 s and 1 s backoff —
  useless against a per-minute limit and meaningless against a per-day one, and
  it spends two further requests of a 20-request allowance to discover this. The
  response carries `RetryInfo.retryDelay` (26250 s here) and the client ignores
  it. It should not retry when the server states a delay it cannot wait out.
  Not fixed: it changes failure semantics the existing tests assert, and the
  honest answer for a demo is a paid tier rather than cleverer retries.

Any deployment intended to show the model working needs billing enabled. On the
free tier a single manager walking the demo can exhaust the day's quota.

---

## 10. Against real Google Cloud

Measured 18 October 2026 on project `pulseai-b2d98`, **free tier only** — no
billing account is linked, which is what bounds this section.

The application ran against the real Firestore database and the real Gemini API,
in two configurations: full production mode, and a staging run that keeps the
Firestore backend but uses the development persona header, so the data and model
paths could be exercised without a Firebase sign-in.

**Firestore, with the project's own adapter.** `seed()` wrote the demo
organisation through `FirestoreDocumentStore` into `pulseai-b2d98`
(collection prefix `tp_`), and the records were read back from the database:

| Check | Result |
| --- | --- |
| Collections written | 11 users, 3 projects, 4 milestones, 19 tasks, 5 documents, 3 decisions, 7 task updates, 5 requests, 5 actions, 3 notifications |
| `mgr-001` email rewritten and read back | confirmed from Firestore, not from memory |
| Manager dashboard served from Firestore | 3 projects, 8 risks, 5 inbox items, 4 open requests |
| Project health from Firestore records | Payments `at_risk` (score 7), Identity `needs_attention` (62), Insights `on_track` (100) |

Those are the same numbers the in-memory evaluation reports, which is the point:
the repository abstraction returns the same answers over either store.

**Gemini against Firestore-sourced facts.** `POST /api/ai/project-briefing` on
`proj-payments`, `force_refresh=true`: `meta.source: "gemini"`, not degraded,
**no grounding notes** — 8 key risks for the 8 rules-engine findings and 2
blockers, matching section 9. The facts came out of Firestore rather than the
in-memory seed, so the whole chain — Firestore read, rules engine, fact
assembly, model call, grounding — works against live infrastructure.

**Production guardrails, against the real project.** `ENVIRONMENT=production`,
`DATA_BACKEND=firestore`, `AUTH_MODE=firebase`, real Firebase web config:

| Check | Result |
| --- | --- |
| `/health` | `environment=production`, `data_backend=firestore`, `ai_configured=true` |
| `GET /api/session`, no token | **401** "A bearer token is required." |
| `GET /api/session`, dev persona header | **401** — the header is inert in production |
| `GET /api/session`, malformed bearer token | **401** "Invalid or expired credentials." |
| `POST /api/admin/seed` | **404** |
| `GET /api/auth-config` | `sign_in_configured: true`, real web API key, `pulseai-b2d98.firebaseapp.com` |
| SPA at `/` | renders sign-in; `/api/auth-config` is the only pre-auth request |

The malformed-token row matters more than it looks: a 401 reading "Invalid or
expired credentials" rather than "A bearer token is required" means the Firebase
Admin SDK initialised and actually rejected the token, so verification runs
rather than being skipped.

### What the free tier made impossible

**Cloud Run deployment did not happen.** The project has no billing account —
both accounts visible to the signed-in user are closed — and the required
services cannot even be switched on:

```
FAILED_PRECONDITION: Billing account for project '511197919775' is not found.
Billing must be enabled for activation of service(s)
'artifactregistry, cloudbuild, run, secretmanager'
reason: UREQ_PROJECT_BILLING_NOT_FOUND
```

Running on the free tier is a deliberate choice for this project, so this is a
constraint rather than a fault. **There is no deployment URL, and none is
claimed anywhere.** What stands in its place is the container evidence in
section 8 — the image builds, runs, serves the SPA and enforces every production
guardrail locally — plus the real-infrastructure evidence above.

**A real end-user sign-in was never completed.** Firebase Authentication has
never been provisioned on the project: Firebase's own endpoint, called with the
project's real web API key, answers

```
POST accounts:createAuthUri  ->  400 CONFIGURATION_NOT_FOUND
```

and that is exactly the error the browser received when the sign-in button was
clicked, so the attempt reached Firebase and was refused. Provisioning it
through the Identity Platform API is also closed on the free tier
(`BILLING_NOT_ENABLED : Identity Platform feature requires billing to be
enabled`), and the config cannot be patched because no config exists to patch.
The one free route is the Firebase console — Authentication, "Get started", then
enabling a provider — which is a human action nothing here can perform.

So the sign-in path is verified up to the point of the identity provider and no
further: the SPA fetches its configuration and renders sign-in, the API rejects
absent, stale and malformed credentials, and the email-to-user mapping was
prepared by seeding `mgr-001` with a real address. Whether a genuine Google
identity resolves to the manager dashboard is **unverified**.

---

## Known limitations

**Not validated against reality.** Every number here comes from synthetic data
with hand-written expectations. No real team has used this.

**Live output quality rests on one or two samples per capability.** One
project, one request, one finding, and two runs of the handover brief. Enough to
establish that the model grounds its claims, and enough that the handover brief
exposed two real prompt defects — but not enough to measure how often either
behaviour occurs. The two prompt fixes are verified on exactly one re-run of the
same data, which demonstrates they changed the labelling in the right direction,
not that they hold across varied input. One soft `evidence_kind` edge in the risk
explanation is recorded and deliberately left untuned for the same reason.

**The citation allow-list cannot reach untrusted items.** `collect_ids` walks
`facts` only, so a claim correctly sourced from a task update cannot cite that
update's id without the grounder stripping it. The prompt works around this by
requiring attribution in the prose. Section 9 records the clean fix.

**Not deployed.** Cloud Run configuration is complete and the image is verified
locally, and the application has now been run against the project's real
Firestore and the live Gemini API (section 10). But Cloud Run, Cloud Build,
Artifact Registry and Secret Manager all require a billing account, this project
runs on the free tier by choice, and its two billing accounts are closed — so
the services cannot be enabled, deployment was not executed, and **there is no
URL to report**.

**No real sign-in has been completed.** Firebase Authentication is not
provisioned on the project, and the API route to provision it requires billing
(section 10). Everything up to the identity provider is verified — configuration
delivery, sign-in rendering, and rejection of absent, stale and malformed
credentials — but no genuine identity has reached the manager dashboard, so the
email-to-user mapping is exercised only by the seed script's read-back, not by a
token.

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

**Frontend coverage is targeted, not broad.** 47 component and client tests
cover the interactions where a wrong rendering would mislead a manager. The
pages themselves — routing, the dashboards, the handover page's multi-step
state — are type-checked and were driven manually through the running
application, but have no automated tests. That is the largest remaining gap.

**Single-worker caching.** The AI summary cache is persisted, but the Cloud Run
configuration runs one worker per instance so that in-process state stays
coherent. Multi-worker deployment would need the cache reads to go through
Firestore on every request.
