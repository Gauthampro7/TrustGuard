# Gautham — core, contracts and integration

This device is the integration workspace. Gautham owns the API, evidence synthesis, privacy/integrity controls, shared interfaces and final merged product. Work on `main` or a dedicated `integration` branch according to the repository's merge policy; the other three owners work in separate clones/branches. The product is implemented. The immediate goal is parallel improvements with stable boundaries and repeatable release checks.

## Your boundary

Own `backend/app/api/**`, `backend/app/core/**`, `backend/app/models/**`, `backend/app/scenarios/**`, `backend/app/main.py`, backend package/setup files, `backend/requirements.txt` and `backend/constraints.txt`; also own the shared ABI file `backend/app/forensics/common.py` and protected `backend/app/forensics/AGENTS.md`. Own `frontend/AGENTS.md` and `extension/AGENTS.md`, `tests/core/**`, `tests/contracts/**`, shared test bootstrap/configuration, `contracts/**` except each teammate's proposal directory, `scripts/**`, `.github/**`, root files and project/team documentation under `docs/**` except the three teammates' personal briefs. Use `contracts/proposals/gautham/**` for your own cross-module proposals.

Do not implement teammate changes in `backend/app/forensics/**` outside `common.py` and its protected `AGENTS.md`, `tests/forensics/**`, `frontend/**` outside its protected `AGENTS.md`, `extension/**` outside its protected `AGENTS.md`, or `contracts/proposals/akarsh/**`, `contracts/proposals/aril/**`, `contracts/proposals/achumit/**`. Respect their owned `docs/team/people/akarsh.md`, `aril.md` and `achumit.md` as well. Review and merge their work; for cross-boundary fixes, agree the interface and let the owner supply the module patch. One-time coordinated relocation of tests/browser smoke into these boundaries belongs to the team baseline setup, not concurrent feature work.

## Start locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -c backend/constraints.txt
.\.venv\Scripts\python.exe scripts/diagnostics.py
.\.venv\Scripts\python.exe -m pytest tests/ -q
node --test extension/tests/*.test.cjs
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Reuse an existing `.venv` rather than recreating it. For the live dashboard gate, run `npm.cmd ci` and `.\node_modules\.bin\playwright.cmd install chromium` as described in [Aril's brief](aril.md), then run `node frontend/tests/browser-smoke.cjs` from a second terminal. The shared root package/lockfile installs only development tooling. The live local UI is `http://127.0.0.1:8000/dashboard/`; docs are `http://127.0.0.1:8000/api/v1/docs`.

## Contracts and dependency order

`backend/app/models/schemas.py` remains the Python schema source. `backend/app/forensics/common.py` remains the single `ForensicResult` definition. Generated OpenAPI/schema snapshots and the detector protocol live in `contracts/v1/`; fixtures and examples there are read-only consumer references. `python scripts/export_contracts.py --check` checks the frozen snapshots. Only Gautham regenerates them, with a reviewed proposal for breaking changes. A snapshot update is not permission to silently change v1 consumers. `contracts/ownership.json` is the checked ownership map.

Publish the shared team baseline before the three branches diverge. Akarsh reads the detector protocol; Aril and Achumit read API contracts and run the baseline backend unchanged. They may improve their modules while your core work progresses. API, detector thresholds and client rendering should not be changed together in one unreviewable patch.

Every proposal needs a concrete input/output example, compatibility impact, affected owners, migration tests and a decision recorded by Gautham. If it breaks v1, retain v1 while introducing an explicit new version or negotiated adapter. Do not edit a teammate's proposal history; record the decision through the review process or a Gautham-owned decision note.

## Next work, in order

1. **GA-1: collaboration baseline — completed in this team-layout release.** Tests are separated into `tests/forensics/`, `tests/core/` and `tests/contracts/`; browser smoke lives in `frontend/tests/browser-smoke.cjs`; frozen contracts/examples, owner-aware checks and CI are published together. Teammate branches start at this same baseline. Start new core work at GA-2.
2. **GA-2: close core validation gaps.** Add meaningful integration coverage around chunked body limits, concurrent/repeated audit requests, cache expiry and eviction, failed canary registration, and dependency failures. Inspect existing tests first: signature/PDF tampering, multimodality, quality dampening and basic cache bounds already have coverage. Preserve validation errors that omit submitted media samples. Make behavior changes only where a test or demonstrated defect justifies them.
3. **GA-3: make release diagnostics trustworthy.** Run all four scenarios through schema validation and the live extractors; report unavailable modalities, uncertainty, versions and per-extractor timing without calling a whole-request run an extractor SLA. Extend `scripts/diagnostics.py` so its uncertainty checks exercise production behavior rather than only reproducing the formula. Keep synthetic fixtures explicitly labeled and regenerated by `scripts/build_scenarios.py`.
4. **GA-4: integrate and verify one owner at a time.** Merge compatible detector changes, then dashboard changes and extension changes, running the shared gates after each. Order may change for independent PRs; never merge an unresolved contract break. Refresh validation notes and release/demo instructions only after the final combined suite passes.

Do not add biometric enrollment, persistent raw-media storage, social scrapers, legal-compliance certification or production identity authentication to this work batch. Their architectural implications require a separate scope and threat model.

## Final integration gate

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
.\.venv\Scripts\python.exe -m pytest tests/forensics/test_performance.py tests/forensics/test_environmental.py -s -q
node --test extension/tests/*.test.cjs
.\.venv\Scripts\python.exe scripts/diagnostics.py
.\.venv\Scripts\python.exe scripts/export_contracts.py --check
.\.venv\Scripts\python.exe scripts/check_module.py all --browser
node frontend/tests/browser-smoke.cjs
git diff --check
```

Run browser smoke with the local backend already running. Before merging each owner PR, run `python scripts/check_ownership.py --owner <name> --base origin/main` on that branch; use `main` only when the shared baseline has not yet been pushed. The ownership check for an individual PR is distinct from validating a combined integration branch, which legitimately contains several owners' merged work. Core/contract CI must be automatic; browser installation and live-server setup must be explicit in the relevant job.

Acceptance requires all four scenarios using real extractors; at least two actually evaluated modalities per complete inspection; every suspicion dimension capped when uncertainty is high; no automatic verified-identity claim; canary-copy attribution limits; complete evidence/defense/playbook UI; audit step gating; Ed25519 payload/PDF verification; no raw samples in retained records; and extension consent, CORS and navigation tests. Timings are host-specific measurements, never universal latency promises. Preserve the existing limitation that session keys and case/certificate caches disappear on restart.

Deliver the merged code, compatible frozen contracts, CI/test evidence, updated `docs/reports/IMPLEMENTATION_VALIDATION.md`, reviewed teammate PRs and a short release/demo checklist. Only Gautham merges to the integration branch and publishes the final shared baseline/release.
