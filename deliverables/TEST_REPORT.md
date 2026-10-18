# TeamPulse AI — local validation

Validated on 18 October 2026, Asia/Kolkata. Existing application source and dependency manifests were left unchanged.

## Environment

- Python 3.12.10, isolated `.venv` with the existing requirements installed.
- Portable Node 24.22.0 and npm, under `.tools/node-v24.22.0-win-x64`.
- Frontend dependencies installed with `npm ci` from the committed lockfile.
- Existing FastAPI app serves the production frontend build on `http://127.0.0.1:8000`.
- Synthetic in-memory data, development personas and Gemini disabled for reproducible local validation.

## Reproduced results

| Check | Result |
|---|---|
| Existing backend test suite | 138 passed |
| Backend statement coverage | 91% rounded: 3,244 statements, 307 missed |
| Existing frontend test suite | 47 passed across 7 files |
| TypeScript and Vite production build | Passed on Node 24 |
| Ruff, `backend` and `scripts` | Passed |
| oxlint | Completed with 16 warnings and no errors |
| Synthetic evaluation harness | All checks passed |

The backend suite emits a Starlette/httpx deprecation warning with the newly installed dependency versions. Frontend warnings concern unsafe optional chaining in two tests and mixed component/utility exports affecting Fast Refresh. These are existing warnings; no product fixes were made.

The README's Node 20+ guidance is too broad for this lockfile: its Firebase packages require Node >=24.12. The supplied Dockerfile uses Node 22. The frontend happened to pass on Node 22 too, but that version produces dependency engine warnings; use Node 24 for the local presentation.

## Synthetic evaluation details

- Expected delivery risks: 8 of 8 found; zero unexpected findings on the labelled payments project.
- Quiet tasks: none of 5 were named as the subject of a finding.
- Task age alone: no risk finding across 6 tested ages.
- Backup ranking: matches the expected order; all 6 ineligible candidates refused.
- Handover briefs: all 8 briefs contain all 11 required sections.
- Invalid AI output: all 8 injected failures returned a usable fallback without corrupting work records.
- Grounding: 3 invented IDs removed; valid source `pay-02` retained.
- Notification sweep: first sweep created 3, the next 4 created 0 duplicates.
- Access control: 45 cross-user request reads and 15 unauthorized project reads refused.

These are checks against synthetic, hand-labelled examples. They do not demonstrate real-world precision, productivity gains, live-model quality or production readiness.

## Evidence and reproduction

- `evidence/backend-tests.xml`: machine-readable backend test results.
- `evidence/browser-checks.json`: completed browser workflow checks, when generated.
- `evidence/*.png`: screenshots of the actual local app.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -o addopts= --cov=backend/app -q
.\.venv\Scripts\python.exe scripts/run_evaluation.py
.\.venv\Scripts\ruff.exe check backend scripts
$env:Path = "$PWD\.tools\node-v24.22.0-win-x64;$env:Path"
cd frontend
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

## Limits and remaining submission work

No live Gemini key, genuine Firebase user login, cloud Firestore integration, Cloud Run deployment, load test or real-team study was exercised in this run. Memory-backed changes reset on restart. The existing handover persistence and AI citation gaps remain backlog items.

The PPT's public demo-video URL and public product URL are pending. The team will record the demo using `TeamPulse_AI_Demo_Script.md`. Uploading that recording and hosting the app are separate external actions; local files and localhost must not be represented as public submission links.

The portable runtimes and installed dependencies are local setup tools and are not committed. On a fresh clone, install Python 3.12 and Node 24.12 or newer, recreate `.venv`, install the existing Python requirements, and run `npm ci` in `frontend` before reproducing these checks. When Node is already on PATH, skip the portable-runtime PATH line above.
