# Aril — dashboard and browser workbench

Work in your own clone on `aril/dashboard`. The dashboard already calls the live API, decodes local media, displays the 5D vector and dual ledger, renders prosecutor/defense explanations, loads all four scenarios, generates canaries and signs/downloads audit PDFs. It also has the adversarial sandbox, JSON export and incident-brief copy action. Your work is interaction correctness, accessibility and browser regression coverage.

## Your boundary

You may edit `frontend/**` except `frontend/AGENTS.md`, including `frontend/tests/browser-smoke.cjs`, plus `contracts/proposals/aril/**` and your own brief `docs/team/people/aril.md`. Keep module notes within `frontend/`; keep generated screenshots/reports in ignored `scratch/dashboard-smoke/`.

Do not edit `frontend/AGENTS.md`, `backend/**`, `extension/**`, root `tests/**`, `contracts/v1/**`, other people's proposal directories, `scripts/**`, `.github/**`, root files or `docs/**` except your personal brief. In particular, backend schema fixes belong to Gautham and extractor changes belong to Akarsh. `scripts/test_dashboard.cjs`, retained as a compatibility wrapper, is Gautham-owned; the browser test implementation is yours in `frontend/tests/browser-smoke.cjs`.

## Start locally

From the repository root after checking out the shared baseline:

```powershell
git switch -c aril/dashboard
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -c backend/constraints.txt
npm.cmd ci
.\node_modules\.bin\playwright.cmd install chromium
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Use `git switch aril/dashboard` if it already exists. Keep the last command running in one terminal. Open `http://127.0.0.1:8000/dashboard/`; run this in a second terminal at the same repository root:

```powershell
node frontend/tests/browser-smoke.cjs
```

The Python server serves your current frontend files directly. There is no bundler requirement and no separate frontend server. Do not launch from `file://`. For an already installed Chromium, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to that binary's path. `npm ci` consumes Gautham's shared root lockfile; do not change that manifest or lockfile from this branch. It installs Playwright as a development dependency, not a frontend runtime framework.

## Frozen interface

Read the OpenAPI, schemas, extractor protocol and examples in `contracts/v1/` as needed; build requests against v1. The frontend talks only to `http://127.0.0.1:8000/api/v1`. Preserve `requestId`, `evidenceItems`, response field names, declared units and unavailable-dimension behavior. Render all five vector dimensions with evidence/uncertainty; never turn them into a standalone authenticity probability. `innovationMetadata` values are strings in the current contract.

Reuse the read-only backend and all four real-pipeline scenarios during development. They are synthetic demonstrations and must remain visibly labeled. A browser fixture may mock errors or delayed responses to test UI states; it must not replace the live-API acceptance run. The backend remains the source of verdicts, multimodality decisions, audit eligibility and certificate verification.

Keep file decoding transient and bounded. The current browser pathway samples one video frame and up to six seconds of mono audio; it does not track mouths or estimate pulse from video. Changing capability labels is part of correctness. API changes go in `contracts/proposals/aril/<topic>.md`, including example JSON and a compatibility plan; continue building against v1.

## Next work, in order

1. **AR-1: make the sandbox reversible for every bundle.** Preserve an immutable original bundle and derive each applied transformation from the current controls. Today, applying degradation and returning the slider to 0 leaves a prior `qualityDegradation`; custom-bundle Reset does not restore mutated evidence/text. Cover apply 70% → apply 0%, repeated Apply, and Reset for both scenario and custom evidence. Restore the original text, handle and numeric samples exactly; stale audit eligibility must clear when evidence changes.
2. **AR-2: close accessibility gaps.** Verify full keyboard use for evidence selection, sandbox controls, ledger, verification checkboxes and audit actions; ensure visible focus, useful status announcements and non-color-only uncertainty labels. Honor reduced motion. Add browser assertions for the behavior you change and retain no horizontal overflow at 390 px and 1440 px, plus a manual 200% zoom check.
3. **AR-3: exercise failure and export states.** Add targeted regressions for engine unavailable/422 responses, interrupted media decoding, clipboard denial and expired audit links. JSON export must contain the current verdict only, and copying must report failure without claiming success. Ensure a request finishing after file/scenario/control changes cannot repopulate stale results. Build on existing stale-response coverage.

Each item is a separate, reviewable PR. A framework migration, new API fields, automatic face tracking and a new design-system dependency are outside this batch.

## Acceptance and delivery

With the local engine running:

```powershell
node --check frontend/app.js
node frontend/tests/browser-smoke.cjs
.\.venv\Scripts\python.exe -m pytest tests/contracts/ -q
.\.venv\Scripts\python.exe scripts/check_module.py dashboard --browser
.\.venv\Scripts\python.exe scripts/export_contracts.py --check
.\.venv\Scripts\python.exe scripts/check_ownership.py --owner aril --base origin/main
git diff --check
git diff --name-only
```

The smoke run must inspect `ceo-wire-scam`, `homoglyph-clone`, `creator-copyright` and `wifi-compression-edge-case` through the actual API. Check exact vector/ledger/dialectic/playbook rendering, the canary alert, degraded-evidence language, no horizontal overflow, media sampling, human-step gating, real PDF download and stale-result rejection. Add the AR-1 reset cases before delivering sandbox work. Zero page errors is required; record expected failed HTTP calls separately in failure-state tests. The ownership checker reads `contracts/ownership.json`; use `--base main` if the shared baseline has not yet been pushed, otherwise check against the fetched approved `origin/main`.

Deliver only owned files, an updated browser regression, and `frontend/VALIDATION.md` with commands/results and any manual checks. Attach regenerated screenshots/report artifacts to the review rather than committing scratch output. Gautham integrates your branch; Achumit owns the similar-looking extension UI independently.
