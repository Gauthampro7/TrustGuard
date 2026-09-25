# Achumit — Chrome extension

Work in your own clone on `achumit/extension`. The Manifest V3 extension already has opt-in collection, a loopback API bridge, an in-page panel, a popup, Unicode warnings, the complete vector/ledger/playbook, bounded avatar sampling and stale-navigation protection. Existing tests cover the principal X route and bridge behavior. Your next deliverable is resilient platform adapters and tested lifecycle/UI behavior.

## Your boundary

You may edit `extension/**` except `extension/AGENTS.md`, plus `contracts/proposals/achumit/**` and your own brief `docs/team/people/achumit.md`. This includes the manifest, content/background scripts, shared extension renderer, popup, tests, local sanitized DOM fixtures and extension README/validation notes.

Do not edit `extension/AGENTS.md`, `backend/**`, `frontend/**`, root `tests/**`, `contracts/v1/**`, other people's proposal directories, `scripts/**`, `.github/**`, root files or `docs/**` except your personal brief. Do not patch the API to accommodate a selector bug. Do not copy frontend files into shared roots; the extension's rendering implementation remains inside `extension/`.

## Start locally

From the repository root after checking out the shared baseline:

```powershell
git switch -c achumit/extension
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -c backend/constraints.txt
node --test extension/tests/*.test.cjs
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Use `git switch achumit/extension` if it already exists. In Chrome, visit `chrome://extensions`, enable Developer mode and load the local `extension/` folder unpacked. Reload the extension and target tab after changing content scripts. Open a public profile on X, Instagram or LinkedIn, then use **Inspect this profile**; collection must stay off until that explicit action.

The Node tests require no JavaScript dependencies. Keep the backend running only for manual integration. Synthetic/sanitized local DOM fixtures are the reliable automated adapter baseline; the current suite does not prove compatibility with every live platform layout.

## Frozen interface

Use `POST /api/v1/extension/evaluate-profile` at `http://127.0.0.1:8000` according to `contracts/v1/`. `referenceHandle` is a user-supplied comparison, not a verified identity. Submit only bounded public-header text and already-readable avatar pixels. The server does not retrieve `avatarUrl` or other social URLs.

Preserve response distinctions between complete multimodal inspections and incomplete advisories. If avatar canvas access fails, report the missing visual modality; do not fabricate pixels, fetch around browser restrictions or display a continuous authenticity index as a substitute for evidence. Where the supporting index exists, show the 5D vector, uncertainty, evidence and independent checks with it. It is not a probability.

Keep collection opt-in, profile-scoped and transient. No post/feed/message scraping, raw storage, broad new host permissions or social endpoint requests. Stop, route change and tab lifecycle events must discard stale data. Automatic re-evaluation is debounced with no more than one request per five seconds. Propose any payload or permission expansion in `contracts/proposals/achumit/<topic>.md`; v1-compatible work continues independently.

## Completed deliverables (AC-1, AC-2, AC-3)

1. **AC-1: complete the three-platform fixture matrix.** [Completed] Delivered in `extension/tests/fixtures.cjs` and `extension/tests/platforms.test.cjs`. Covers positive and fail-closed cases for X, Instagram, and LinkedIn; feed and DM text isolation verified; malformed canonical handling hardened in `extension/content.js`.
2. **AC-2: harden monitoring lifecycle.** [Completed] Delivered in `extension/tests/lifecycle.test.cjs`. Proves single observer/timer invariants, rapid same-tab SPA navigation discards, mutation burst rate-limiting (≤ 1 req / 5s), connection error resilience, and guaranteed raw pixel disposal.
3. **AC-3: test popup and panel usability.** [Completed] Delivered in `extension/tests/ui.test.cjs`. Validates complete vs. incomplete advisories (continuous score strictly withheld as `—` when incomplete), unavailable dimensions safely rendered, strict untrusted text handling (XSS injection prevention), homoglyph code-point explanations, and keyboard/ARIA focus management.

Full test suite and execution records are documented in `extension/VALIDATION.md` (47/47 passing tests).

## Acceptance and delivery

```powershell
node --check extension/content.js
node --check extension/background.js
node --check extension/popup/popup.js
node --check extension/verdict-ui.js
node --test extension/tests/*.test.cjs
.\.venv\Scripts\python.exe -m pytest tests/contracts/ -q
.\.venv\Scripts\python.exe scripts/check_module.py extension
.\.venv\Scripts\python.exe scripts/export_contracts.py --check
.\.venv\Scripts\python.exe scripts/check_ownership.py --owner achumit --base origin/main
git diff --check
git diff --name-only
```

For each supported platform, tests must demonstrate at least one recognized public profile and rejection of unsupported/private-content routes. Verify no network request before opt-in, only loopback API targets from the bridge, no persistent storage, complete disposal of sampled pixels and no stale panel after Stop/navigation. An unreadable avatar must remain an incomplete advisory, with no identity claim. `contracts/ownership.json` defines checked boundaries. Use `--base main` if the integration baseline has not yet been pushed; otherwise fetch the approved `origin/main` before the ownership check.

Deliver owned code/tests plus updated `extension/README.md` and `extension/VALIDATION.md` listing fixture coverage, manual checks, remaining selector assumptions and test results. Gautham handles backend integration and approval of any proposed contract or permission changes.
