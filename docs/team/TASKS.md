# TrustGuard — bounded parallel backlog

The team starts from an implemented local product: nine CPU forensic measurements, four synthetic scenarios through real extraction, the live API, evidence dashboard, adversarial sandbox, Chrome extension, canary workflow and signed PDF/QR audit records. The existing validation report records 102 Python tests, 11 extension tests and a real Chromium dashboard run; these are historical baseline results, not claims that a new branch has passed. Re-run the gates on every delivered branch.

This board assigns the next improvements. It does not ask four people to reimplement the baseline. GA-1 is completed by this team-layout release with frozen v1 contracts and relocated tests. Teammates begin at AK-1, AR-1 and AC-1; Gautham's next task is GA-2.

| ID | Priority | Owner / branch | Concrete deliverable | Acceptance / dependency |
| --- | --- | --- | --- | --- |
| GA-1 | Completed baseline | Gautham / `main` | Stable ownership layout, contract snapshots/examples, module checks and CI | Included in this release; teammate branches share the tested baseline |
| AK-1 | P0 | Akarsh / `akarsh/forensics` | Seeded detector perturbation/control bench and module validation note | `python -m pytest tests/forensics/ tests/contracts/ -q`; controls record abstentions and limitations; depends only on GA-1 |
| AR-1 | P0 | Aril / `aril/dashboard` | Reversible sandbox transforms for scenario and custom bundles | Live browser tests: degradation 70% → 0%, repeated Apply and Reset restore originals and clear stale results; depends only on GA-1 |
| AC-1 | P0 | Achumit / `achumit/extension` | X/Instagram/LinkedIn adapter fixture matrix | Each platform has valid-header and fail-closed cases; feed/DM text never enters payload; depends only on GA-1 |
| GA-2 | P1 | Gautham / integration | Missing API retention/limit/error-path regressions and justified fixes | `python -m pytest tests/core/ tests/contracts/ -q`; no raw samples in errors or records; can proceed alongside AK/AR/AC work |
| AK-2 | P1 | Akarsh | Reproduced numeric/Unicode/ambiguous-timing edge-case fixes | Failing test before each fix; v1 names, types, units and meanings remain compatible; follows AK-1 |
| AR-2 | P1 | Aril | Keyboard/status/focus/reduced-motion improvements | Browser assertions, 390/1440 px no-overflow checks, recorded manual 200% zoom check; follows AR-1 |
| AC-2 | P1 | Achumit | Monitoring lifecycle and request-bound regressions | Start/Stop, SPA navigation and mutation bursts cannot duplicate monitors or render stale results; follows AC-1 |
| GA-3 | P1 | Gautham | Diagnostics exercising all scenarios and production uncertainty handling | Diagnostics and core tests pass; distinguish extractor timings from whole-request timings |
| AK-3 | P2 | Akarsh | Bounded laptop benchmark and targeted optimization if required | Report CPU/versions, median/p95/max for every extractor; target <150 ms on tested bounds; no weakened uncertainty |
| AR-3 | P2 | Aril | Error-state and JSON/clipboard/audit-link regressions | Offline/422/clipboard-denied/expired-link failures are honest; export is current verdict only; live smoke still passes |
| AC-3 | P2 | Achumit | Popup/panel accessibility and incomplete-advisory tests | No unsafe HTML rendering; keyboard use works; unavailable modalities do not become identity claims |
| GA-4 | Final gate | Gautham | Integrate one reviewed owner PR at a time and refresh validation | Contract checks, all Python tests, extension tests, diagnostics and live browser smoke pass on the combined commit |

P0 items are the first independent assignment for each teammate. Finish the item's acceptance checks and deliver a focused PR before picking up the next item. P1/P2 work is bounded follow-up; do not expand into new infrastructure or modalities merely because a hook exists.

## Ownership map

| Owner | May edit | Shared dependencies read-only |
| --- | --- | --- |
| Akarsh | `backend/app/forensics/**` except `common.py` and `AGENTS.md`; `tests/forensics/**`; own proposal directory and personal brief | Shared ABI/instructions, Python schemas, `contracts/v1/`, API/core/scenarios, clients |
| Aril | `frontend/**` except `AGENTS.md`, including browser smoke; own proposal directory and personal brief | Backend, root tests, frozen contracts, extension, scripts, protected module instructions |
| Achumit | `extension/**` except `AGENTS.md`; own proposal directory and personal brief | Backend, root tests, frozen contracts, frontend, scripts, protected module instructions |
| Gautham | Remaining backend plus detector `common.py`; three protected module `AGENTS.md` files; `tests/core/**`, `tests/contracts/**`, shared test setup; contracts except teammate proposals; scripts, CI, root files and project/team docs except teammate briefs | Teammate module implementations/tests, personal briefs and proposal histories |

Paths outside a teammate's allowlist are not available for incidental cleanup. A change involving two owners is split into an interface decision and owner-specific PRs. Teammates may run read-only checks across the entire repository. Module notes belong inside the module's owned root; final project-level validation is Gautham's responsibility.

## Independent development and integration

1. Each person uses a separate clone/worktree and the assigned branch. Never share one checkout among concurrent human editors. Read your [Akarsh](people/akarsh.md), [Aril](people/aril.md), [Achumit](people/achumit.md) or [Gautham](people/gautham.md) brief for exact commands and acceptance cases.
2. Consume the baseline backend/contracts unchanged. Akarsh needs no server. Aril and Achumit can run their own loopback server from the same baseline; one person's laptop is not another person's required development server.
3. For a breaking need, add a proposal under `contracts/proposals/<your-name>/` with sample input/output, affected owners, migration and test plan. Continue compatible work against v1 while Gautham records the decision. Do not edit `contracts/v1/`, schemas or shared ABI from a teammate branch.
4. Deliver a PR with owned-path changes, the problem/behavior change, exact checks/results, module limitations and any proposal links. Gautham reviews boundaries and integration, then merges. No direct teammate pushes to `main`.
5. After a merged shared update, fetch and incorporate the approved baseline in your own branch. If a conflict touches another owner's file, preserve the integration version and coordinate the required change; do not guess at their implementation.

## Definition of done

Every PR passes `python scripts/check_module.py <core|forensics|dashboard|extension>` for its module, `python scripts/export_contracts.py --check`, `python scripts/check_ownership.py --owner <name> --base origin/main` and `git diff --check`, with no unapproved cross-owner edits. Dashboard acceptance additionally uses `python scripts/check_module.py dashboard --browser` with the local API running. `contracts/ownership.json` is the machine-readable boundary map. Use `--base main` only when the team baseline is local and has not been pushed; otherwise fetch the approved remote baseline before comparing. A local browser or DOM mock is not evidence of live social-site compatibility. Synthetic signal controls are not a real-world deepfake benchmark. Backend/user-visible explanations must continue to communicate uncertainty and independent verification.

The integrated release passes `python scripts/check_module.py all --browser` and `python scripts/diagnostics.py` against a running local server. The module runner includes the frozen-contract checker, all Python tests, extension checks and `node frontend/tests/browser-smoke.cjs`; direct commands in the briefs allow focused reproduction. Install Python dependencies with `python -m pip install -r backend/requirements.txt -c backend/constraints.txt`, shared Playwright tooling with `npm ci` and its browser with `npx playwright install chromium`; only Gautham edits shared dependency files. Gautham records the final command output, four-scenario/browser results, extractor timing conditions and remaining limits in the project validation report.

Biometric enrollment/vaults, raw recording retention, social endpoint scraping, paid inference, GPU dependencies, automatic mouth/face ROI tracking and a frontend framework migration are outside this backlog. Propose them separately rather than introducing shared dependencies during the parallel hardening pass.
