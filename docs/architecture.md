# Architecture

## The shape of the system

```
Browser (React + TypeScript SPA)
  │  same-origin /api, dev proxy in development
  ▼
FastAPI application
  │
  ├─ Authentication          app/core/security.py      who is calling
  ├─ Authorization           app/services/authz.py     what they may see
  │
  ├─ Rules engine            app/rules/                deterministic
  │    ├─ dependencies.py    dependency traversal, both directions
  │    ├─ risk.py            delivery-risk findings with linked evidence
  │    ├─ prioritization.py  action-inbox ranking
  │    └─ candidates.py      eligibility gates, then weighted ranking
  │
  ├─ Services                app/services/             business logic
  │    requests · actions · handovers · dashboard · sweeps · facts · audit
  │
  ├─ Notification engine     app/notifications/        dedup and escalation
  │
  ├─ AI layer                app/ai/                   Gemini, when reasoning helps
  │    client · prompts · schemas · service (grounding, cache) · fallback
  │
  └─ Repositories            app/repositories/         DocumentStore abstraction
       └─ InMemory (local, tests) | Firestore (deployed)
```

## The division of labour

The central design decision is what the model is **not** allowed to do.

**Deterministic code owns everything that must be right:** deadlines,
dependency traversal, permission checks, eligibility gates, priority scores,
severity scores, assignment approval, status transitions and notification
deduplication. These are plain Python, unit-tested against a frozen clock, and
produce the same answer every time.

**Gemini owns interpretation:** summarising a project's state, reading an
engineer's free-text request, synthesising a handover brief, and explaining a
rules-engine finding in plain language.

Concretely: the rules engine decides that `act-001` scores 92 and blocks two
tasks. Gemini is then asked to explain *why that matters* to a manager. If
Gemini is unavailable, the 92 and the two blocked tasks are still correct and
still shown — only the prose degrades.

## Request lifecycle

Each request builds one `WorkContext` (`app/services/context.py`): the
authorised slice of the workspace, loaded once, with the dependency graph built
once. Every rule in that request then evaluates against a single consistent
snapshot, and the dashboards stay cheap.

## Data access

Nothing talks to Firestore directly. `DocumentStore` is a five-method
interface (`get`, `list`, `set`, `delete`, `clear`) with two implementations:

- `InMemoryDocumentStore` — thread-safe and deep-copying, used for local
  development and the whole test suite.
- `FirestoreDocumentStore` — imported lazily, so neither local development nor
  the tests need Google Cloud credentials.

Typed `Repository[Model]` objects sit on top and serialise with
`model_dump(mode="json")`, so the stored shape is identical across backends and
ISO-8601 UTC timestamps sort lexicographically.

The MVP reads whole collections and filters in Python. That is the right
trade-off at this size — the seeded workspace is ~50 records — and the
abstraction is where server-side queries go when it stops being. The composite
indexes to create first are documented in `firestore.indexes.json`.

## The AI pipeline

Every capability runs the same five steps:

```
cache lookup → Gemini call → schema validation → grounding → cache write
                     │                │              │
                     └── failure ─────┴──────────────┴──→ deterministic fallback
```

**Schema validation.** Every response is constrained by a Pydantic schema
(`app/ai/schemas.py`) passed to the model as `response_schema` *and*
re-validated on return. Schemas avoid optionals and free-form maps because
those translate poorly to the model's JSON schema dialect; "unknown" is an
empty string or an empty list.

**Grounding** is the step that keeps the model honest. `collect_ids()` walks the
facts payload and builds the set of record ids that were actually supplied. Any
id the model cites outside that set is dropped, and the caller is told how many
were dropped. A risk note whose title does not match a rules-engine finding is
relabelled from `verified_fact` to `hypothesis`. A suggested task id that is not
among the engineer's candidate tasks is discarded.

**Evidence labelling.** Every AI statement carries an `evidence_kind`:
`verified_fact` (stated in the facts), `rule_derived` (computed by the rules
engine), `hypothesis` (the model's inference) or `recommendation` (a suggested
human action). The UI renders these as badges, so a manager can tell a database
fact from a guess.

**Caching.** Outputs are persisted keyed by a SHA-256 fingerprint of the facts
payload. Identical facts are served from cache; changed facts miss. Mutations
that matter (a task update, a new request, a resolved action) delete the
affected project's cached briefing. **No dashboard render calls the model** —
generation is always an explicit `POST /api/ai/*`, and the manager dashboard
shows a cached briefing or nothing at all. There is a test asserting this.

**Fallbacks.** `app/ai/fallback.py` builds a lower-fidelity answer for every
capability from the same facts. It never guesses: it restates what the rules
engine established. A failed handover generation still produces all eleven
required sections from stored records.

## Prompt-injection handling

Engineer-submitted descriptions, task comments and imported document summaries
are untrusted. They are:

1. Kept out of the trusted `<facts>` block entirely and placed in a separate
   `<untrusted_content>` envelope, after the facts.
2. Stripped of envelope-spoofing markers (`</untrusted_content>`,
   `<system_rules>`, `<facts>`, `</instructions>`) and length-bounded.
3. Explicitly demoted by the system rules, which instruct the model to ignore
   instructions found inside the envelope and to note them as suspicious.
4. Unable to do anything even if they succeed, because the model cannot change
   an assignment, a status, a priority or a permission. Those are all
   deterministic code paths behind authorization checks.

Layer 4 is the one that matters. The first three reduce the chance of a
confused summary; the fourth means a confused summary cannot cause damage.

## Notification engine

One notification per concern, not one per sweep. Callers supply a stable
`deduplication_key`; `attention_key(entity_type, entity_id, recipient_id)`
means that creation, a passing deadline and a worsening blocker about the same
record share a key.

A still-unresolved item **escalates** rather than repeating: at most once per
24 hours, at most three times, and only when the item has actually become more
urgent. Running the sweep five times over the seeded workspace creates three
notifications on the first pass and none thereafter.

Marking a notification read sets `read_at` and touches nothing else. The
underlying request, task or action stays exactly as it was — this separation is
the reason a lost approval stops being losable.

## Handover workflow

```
engineer records unavailability        (dates and affected work only)
        ▼
deterministic impact analysis
    active tasks → downstream (forward edges) → upstream blockers (reverse)
    → affected milestones → pending approvals → documents, decisions, updates
        ▼
eligibility gate       hard requirements, evaluated BEFORE any scoring
        ▼
weighted ranking       skills 30 · familiarity 25 · availability 20
                       workload 15 · access 10        (tunable, not validated)
        ▼
Gemini handover brief  eleven sections, each labelled with its evidence kind
        ▼
manager approval       re-runs the eligibility gate; nominates a backup
        ▼
backup acceptance      ← ownership transfers HERE, and only here
```

Two human decisions are required before any task changes owner, and both are
written to the audit trail with the actor's id. An ineligible candidate is
returned with its blocking reasons and a score of zero, and is refused again at
approval time in case authorisation or availability changed after ranking.

## Why a long-running task is never a problem

The product brief is explicit that task age must not be read as poor
performance, and the rules engine enforces it. `detect_project_risks` produces a
finding only from an explicit signal: a missed due date, a recorded blocker
status, an unresolved dependency, a pending decision, an approaching milestone,
or missing ownership on high-priority work. `created_at` is never an input. A
synthetic task aged from 30 to 720 days with no deadline and no blocker produces
zero findings at every age, and `docs/evaluation.md` reports that measurement.

Nothing in the system computes a per-person score of any kind. The only
per-person numbers are `assigned_workload` against `weekly_capacity`, used once,
to work out whether a candidate has capacity to take on someone else's work.

## Frontend

React 19 + TypeScript + Vite + Tailwind 4, with a small hand-written component
vocabulary in `components/ui/primitives.tsx` rather than a component library.
Every surface composes those primitives, which is what keeps spacing, radii,
borders and type scale identical across pages.

Data fetching is one hook (`useAsync`) handling loading, error, refresh and
polling, so every page handles failure the same way. Notifications poll every
20 seconds; nothing else polls. The API client is the only module that knows how
a request is authenticated — `setBearerTokenProvider()` is where Firebase ID
tokens attach when dev personas are switched off, and no page changes.

Types in `types/api.ts` are hand-written to mirror the Pydantic schemas, so a
backend contract change that matters surfaces as a TypeScript error.

## Deliberate non-goals

- **No microservices.** One FastAPI application with clean module boundaries.
- **No multi-agent orchestration.** Four well-scoped prompts with validated
  structured output, called explicitly.
- **No chat interface.** Gemini appears where a manager is already looking,
  attached to the record it describes.
- **No streaming or websockets.** Polling is sufficient for in-app
  notifications at this scale.
