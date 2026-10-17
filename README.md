# TeamPulse AI

**Never lose track of what your team needs.**

An AI-powered engineering operations dashboard. It connects project progress,
blockers, manager commitments, notifications and intelligent handovers so an
engineering manager can answer, in one place:

1. What needs my attention today?
2. Which deliveries are at risk, and why?
3. Which engineers have asked for support?
4. Which approvals, decisions and follow-ups are pending?
5. What work is affected if an engineer becomes unavailable?
6. Who is a suitable backup, and what do they need to know?

TeamPulse exists to help managers support engineers and protect delivery
continuity. It is deliberately **not** a monitoring or productivity-scoring
tool — see [Security and responsible AI](#security-and-responsible-ai).

---

## Contents

- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Enabling Gemini](#enabling-gemini)
- [Firestore setup](#firestore-setup)
- [Authentication](#authentication)
- [Running the tests](#running-the-tests)
- [Deploying to Cloud Run](#deploying-to-cloud-run)
- [Project layout](#project-layout)
- [Security and responsible AI](#security-and-responsible-ai)
- [Troubleshooting](#troubleshooting)
- [Current status](#current-status)

---

## What it does

**Project intelligence.** Projects, milestones, tasks and dependencies in one
view, with deterministic detection of overdue work, recorded blockers, blocked
dependency chains, pending decisions that hold up other work, milestones at
risk and unassigned critical work. Every finding carries the evidence behind it
and links to the underlying records.

**Engineer support.** Engineers submit blockers, decision requests, approval
requests, one-on-one requests and progress updates, link them to a task, track
their status, and correct an inaccurate AI summary. A request stays visible
until it is resolved or cancelled — reading a notification never closes it.

**Manager action inbox.** One consolidated, ranked list of everything waiting on
the manager, grouped into urgent, blocked work, approvals, support and routine
follow-ups. Each item shows its downstream consequence and the factor-by-factor
reason it is ranked where it is.

**Intelligent handover.** When an engineer becomes unavailable, TeamPulse finds
their active tasks, walks the dependency graph in both directions, collects the
affected milestones, pending approvals and documentation, ranks eligible backup
candidates with a transparent score, and generates a structured handover brief.
A manager must approve, and the selected backup must accept, before any task
changes owner.

---

## Quick start

Requires **Python 3.12+** and **Node 20+**. No Google Cloud account is needed
to run it locally: the default data backend is in-memory and the default
authentication mode is a labelled development persona switcher.

```bash
git clone <your-fork-url> teampulse-ai && cd teampulse-ai
cp .env.example .env
```

**1. Backend**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend && uvicorn app.main:app --reload --port 8000
```

The in-memory backend auto-loads the synthetic demo organisation on startup, so
the API has data immediately. Check it:

```bash
curl http://localhost:8000/health
```

**2. Frontend** (in a second terminal)

```bash
cd frontend && npm install && npm run dev
```

Open <http://localhost:5173>. The dev server proxies `/api` and `/health` to the
backend, so the app is same-origin in development exactly as it is in
production.

**3. Or run it as one service**, the way Cloud Run does:

```bash
cd frontend && npm run build          # builds into backend/static
cd ../backend && SERVE_FRONTEND=true uvicorn app.main:app --port 8000
```

Open <http://localhost:8000>.

### Walking the demo

Use the **Development personas** switcher at the bottom of the sidebar.

| Persona | Role | Use it to see |
| --- | --- | --- |
| Priya Raman | Manager | The action inbox, project risk, handover approval |
| Arjun Mehta | Engineer | The lost approval, and being nominated as a backup |
| Diego Alvarez | Engineer | Reporting a blocker and receiving the response |
| Rhea Kapoor | Engineer | Recording emergency unavailability |

`docs/demo_script.md` walks the three scenarios in three minutes.

To reset the workspace to its seeded state at any point:

```bash
curl -X POST -H "X-Dev-User-Id: mgr-001" http://localhost:8000/api/admin/seed
```

---

## Configuration

Everything is environment-driven; see `.env.example` for the annotated list.
The settings that change behaviour most:

| Variable | Default | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | `local` | `production` **force-disables** dev auth and the seed endpoint and forces `AUTH_MODE=firebase`. |
| `DATA_BACKEND` | `memory` | `firestore` for a deployed instance. |
| `AUTH_MODE` | `dev` | `firebase` verifies a real ID token. |
| `DEV_AUTH_ENABLED` | `true` | The persona switcher. Cannot be true in production. |
| `SEED_ENDPOINT_ENABLED` | `true` | `POST /api/admin/seed`. Cannot be true in production. |
| `GEMINI_API_KEY` | — | Absent means every AI capability degrades to a deterministic answer. |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Verify the current id before changing — Google retires model ids. |
| `SERVE_FRONTEND` | `false` | Serve the built SPA from the backend. |
| `DEMO_DATA_MODE` | `true` | Labels synthetic records in the UI and auto-seeds the in-memory backend. |

**Never commit real credentials.** `.gitignore` excludes `.env` and
service-account JSON; `.env.example` holds placeholders only.

---

## Enabling Gemini

The app runs fully without Gemini — every AI capability has a deterministic
fallback and the UI labels which one produced a given answer. To enable it:

**Option A — Gemini Developer API (simplest).** Create a key at
<https://aistudio.google.com/apikey>, then:

```bash
GEMINI_ENABLED=true
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.6-flash
```

**Option B — Vertex AI** (no API key; uses Application Default Credentials):

```bash
GEMINI_USE_VERTEX=true
GEMINI_VERTEX_PROJECT=your-gcp-project
GEMINI_VERTEX_LOCATION=us-central1
```

```bash
gcloud services enable aiplatform.googleapis.com
gcloud auth application-default login
```

Confirm which model ids are current before deploying — Google deprecates them
(`gemini-3.5-flash` is deprecated and routed to `gemini-3.6-flash`):

- <https://ai.google.dev/gemini-api/docs/models>
- <https://ai.google.dev/gemini-api/docs/deprecations>

`GET /api/session` reports whether the running instance has a usable
configuration, and the header badge shows it in the UI.

---

## Firestore setup

**Local development does not need Firestore.** `DATA_BACKEND=memory` keeps
everything in process.

To use the **emulator**:

```bash
npm install -g firebase-tools
firebase emulators:start --only firestore          # listens on :8080
```

```bash
export DATA_BACKEND=firestore
export FIRESTORE_PROJECT_ID=teampulse-local
export FIRESTORE_EMULATOR_HOST=localhost:8080      # read by the Google client
python scripts/seed_demo_data.py
```

To use a **real project**:

```bash
gcloud firestore databases create --location=nam5
gcloud auth application-default login
export DATA_BACKEND=firestore FIRESTORE_PROJECT_ID=your-gcp-project
python scripts/seed_demo_data.py
firebase deploy --only firestore:rules,firestore:indexes
```

`firestore.rules` denies all direct client access: TeamPulse reaches Firestore
only through the backend service account, and every authorization decision is
made in `app/services/authz.py`. `firestore.indexes.json` documents the
composite indexes to create first when the repository layer moves from
collection reads to server-side queries.

The seed script refuses to run when `ENVIRONMENT=production`, and
`POST /api/admin/seed` is unavailable there.

---

## Authentication

**Development (`AUTH_MODE=dev`).** The client sends `X-Dev-User-Id`, matched
against a seeded user. Clearly labelled in the UI, and forced off in
production.

**Production (`AUTH_MODE=firebase`).** The client sends
`Authorization: Bearer <firebase-id-token>`; the backend verifies it with the
Firebase Admin SDK and maps the verified email to a TeamPulse user.
`frontend/src/services/api.ts` exposes `setBearerTokenProvider()` as the single
place to attach the token — no page needs to change.

Authentication only establishes *who* is calling. What they may see is decided
separately, server-side, in `app/services/authz.py`.

---

## Running the tests

**Backend — 130 tests**

```bash
source .venv/bin/activate
cd backend && pytest
pytest --cov=app --cov-report=term-missing
```

The suite runs against the in-memory store with the clock frozen, so every
rules assertion is deterministic.

**Frontend — 47 tests**

```bash
cd frontend && npm test
npm run test:coverage
```

**Evaluation harness** — measures the deterministic behaviour against a
labelled synthetic dataset and prints the numbers reported in
`docs/evaluation.md`:

```bash
python scripts/run_evaluation.py
```

**Linting and type checking**

```bash
ruff check backend/ scripts/
cd frontend && npx tsc -b && npm run lint
```

---

## Deploying to Cloud Run

The container serves the API and the built frontend together.

```bash
export PROJECT_ID=your-gcp-project
export REGION=us-central1

gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com

# 1. Secret for the Gemini key (skip when using Vertex AI + ADC).
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create teampulse-gemini-key --data-file=-

# 2. Service account with only the access it needs.
gcloud iam service-accounts create teampulse-run
SA="teampulse-run@${PROJECT_ID}.iam.gserviceaccount.com"
for ROLE in roles/datastore.user roles/secretmanager.secretAccessor \
            roles/aiplatform.user roles/firebaseauth.viewer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA" --role="$ROLE"
done

# 3. Build and deploy.
gcloud builds submit --tag "${REGION}-docker.pkg.dev/${PROJECT_ID}/teampulse/app:latest"

gcloud run deploy teampulse-ai \
  --image "${REGION}-docker.pkg.dev/${PROJECT_ID}/teampulse/app:latest" \
  --region "$REGION" \
  --service-account "$SA" \
  --set-env-vars "ENVIRONMENT=production,DATA_BACKEND=firestore,AUTH_MODE=firebase,SERVE_FRONTEND=true,DEMO_DATA_MODE=false,FIRESTORE_PROJECT_ID=${PROJECT_ID},FIREBASE_PROJECT_ID=${PROJECT_ID},GEMINI_MODEL=gemini-3.6-flash" \
  --set-secrets "GEMINI_API_KEY=teampulse-gemini-key:latest" \
  --min-instances 0 --max-instances 4 --cpu 1 --memory 512Mi

# 4. Verify before announcing anything.
SERVICE_URL=$(gcloud run services describe teampulse-ai --region "$REGION" --format='value(status.url)')
curl -fsS "${SERVICE_URL}/health"
```

Then confirm, in the deployed instance: the health endpoint reports
`environment=production`, `GET /api/session` rejects a request without a token,
`POST /api/admin/seed` returns 404, the manager dashboard loads, and generating
a project briefing reports `source: "gemini"` rather than a degraded fallback.

**Record the deployment URL only after those checks pass.**

Build the image locally first if you want to check it before pushing:

```bash
docker build -t teampulse-ai:local .
docker run --rm -p 8080:8080 \
  -e ENVIRONMENT=local -e DATA_BACKEND=memory -e AUTH_MODE=dev \
  -e DEV_AUTH_ENABLED=true -e SEED_ENDPOINT_ENABLED=true \
  teampulse-ai:local
```

---

## Project layout

```
teampulse-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/     HTTP endpoints, one module per resource
│   │   ├── core/           config, clock, logging, authentication
│   │   ├── models/         domain enumerations
│   │   ├── schemas/        Pydantic entities, analysis results, API contracts
│   │   ├── repositories/   DocumentStore abstraction + memory/Firestore adapters
│   │   ├── rules/          deterministic engine: dependencies, risk, ranking
│   │   ├── ai/             Gemini client, prompts, schemas, grounding, fallbacks
│   │   ├── notifications/  event engine with deduplication and escalation
│   │   ├── services/       business logic, authorization, dashboards
│   │   ├── demo/           labelled synthetic data
│   │   └── main.py         application factory
│   └── tests/              pytest suite
├── frontend/src/           React + TypeScript + Tailwind single-page app
├── scripts/seed_demo_data.py
├── docs/                   architecture, evaluation, demo script, proposal
├── Dockerfile
└── .env.example
```

The AI service, notification service, rules engine and data access are kept
separate enough to test independently — see `docs/architecture.md`.

---

## Security and responsible AI

- Authorization is enforced in the backend on every endpoint, not by hiding UI.
- An engineer cannot read another engineer's support requests, and sees only
  their own backup-candidate score — never a peer's workload-derived ranking.
- Managers see work information only for projects they are authorised on.
- Unavailability records carry dates and affected work. There is no field for a
  medical or family reason, and nothing in the product displays one.
- No keystroke monitoring, screen tracking, hidden surveillance, or employee
  productivity scores. A long-running task is never, on its own, treated as a
  problem or attributed to its owner — only deadlines, recorded blockers,
  dependencies and milestones produce a finding.
- AI never makes a performance judgement, and never changes a priority, a
  deadline, a status or an assignment.
- Reassigning work needs human approval twice: a manager approves, and the
  nominated backup accepts. Both are recorded in an audit trail.
- Candidate eligibility is a hard gate evaluated before ranking and re-checked
  at approval time; an ineligible candidate can never be assigned.
- Engineer-submitted text is treated as untrusted data in every prompt.
- Logs redact credential-shaped values and never carry request bodies.
- Synthetic demo data is labelled in the UI and in every record.

---

## Troubleshooting

**`Could not reach the TeamPulse API`** — the backend is not running on 8000, or
`VITE_API_PROXY_TARGET` points elsewhere. Check `curl localhost:8000/health`.

**`401 Development mode requires the x-dev-user-id header`** — clear the stored
persona (`localStorage.removeItem('teampulse.persona')`) and reload, or confirm
`DEV_AUTH_ENABLED=true` and `ENVIRONMENT` is not `production`.

**`401 Unknown development persona`** — the datastore was reset without
reseeding. Re-run the seed endpoint or restart with the in-memory backend.

**Briefings say "Gemini is not configured"** — expected without a key. Set
`GEMINI_API_KEY` (or the Vertex variables) and restart; `GET /api/session`
confirms `ai_configured`.

**`Gemini output was unusable`** — the call failed or the reply did not validate.
The answer degrades to a deterministic summary rather than erroring, and the
banner says so. Check the model id is current and the key has quota.

**`404` on `/api/admin/seed`** — the seed endpoint is disabled. It is always
disabled when `ENVIRONMENT=production`.

**Firestore `DefaultCredentialsError`** — run `gcloud auth application-default
login`, or set `FIRESTORE_EMULATOR_HOST` for the emulator, or go back to
`DATA_BACKEND=memory`.

**Client routes 404 after a reload in production** — `SERVE_FRONTEND=true`
requires `backend/static/index.html` to exist. Run `npm run build` first.

---

## Current status

Built and verified locally. The application runs, both role experiences work,
and all three demo scenarios complete end to end against real persisted state.
Google Cloud deployment is fully configured and documented but **has not been
executed** — no Google Cloud credentials were available in the build
environment, so there is no deployment URL to report. The Gemini integration is
real and exercised by the test suite through an injected client; it has not
been run against the live API for the same reason, and the application reports
its degraded state honestly when a key is absent.

See `docs/evaluation.md` for measured results and known limitations.
