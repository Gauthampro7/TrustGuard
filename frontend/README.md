# TrustGuard dashboard module

Aril owns the browser dashboard in this directory: presentation, local media preparation, inspection state, accessible evidence rendering and the browser smoke suite. The dashboard is plain HTML, CSS and JavaScript; it has no build step. Backend inference, API contracts, extension behavior and certificate signing belong to their respective modules.

| File | Responsibility |
| --- | --- |
| `index.html` | Accessible layout, input forms, scenario selector, sandbox and evidence panels. |
| `styles.css` | Responsive light theme, vector bars and reduced-motion behavior. |
| `app.js` | Browser decoding, transient state, local API calls, verdict rendering, sandbox controls and analyst actions. |
| `favicon.svg` | Local brand asset; no external asset request. |
| `tests/browser-smoke.cjs` | Real Chromium integration checks against the running backend. |

## Aril's workflow

1. Start from the frozen [v1 OpenAPI contract](../contracts/v1/openapi.json) and the [v1 examples](../contracts/v1/examples/). Each scenario has a `<scenario>.request.json` and `<scenario>.verdict.json`. Examples document valid shapes; they are not live assessments or signed incident records. Coordinate a contract change with the backend owner before relying on new fields.
2. Make dashboard changes inside `frontend/`. Keep the existing IDs consumed by `app.js` and the smoke suite synchronized. Leave `scripts/test_dashboard.cjs` as the compatibility wrapper.
3. Run the syntax checks below. They require Node.js and do not start a browser or backend.
4. With the backend running, run the real-browser smoke, inspect its screenshots, and manually exercise any new interaction the suite does not cover.
5. Hand off the changed files, checks run and any API dependency. Keep contract examples and live results clearly distinguished in UI copy and review notes.

From the repository root:

```powershell
node --check frontend/app.js
node --check frontend/tests/browser-smoke.cjs
node --check scripts/test_dashboard.cjs
```

For an interactive preview, use the existing backend environment in a separate terminal:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/dashboard/`. The backend serves the dashboard; no additional frontend development server is needed. Use HTTP, rather than opening `index.html` directly. The client targets `http://127.0.0.1:8000/api/v1`, and the live API documentation is at `/api/v1/docs`.

## Contract boundary

| Endpoint under `/api/v1` | Dashboard use |
| --- | --- |
| `GET /health` | Actual connection status. |
| `GET /scenarios/{id}` | Load a labeled simulation request; send that request through the real inspection endpoint. |
| `POST /inspect` | Obtain the five-dimensional vector, evidence ledger, dialectic, playbook and optional forensic details. |
| `POST /canaries` | Generate marked text with explicit server-session scope. |
| `POST /cases/{verdictId}/sign-audit` | Submit actual completed step IDs, notes and an explicit analyst decision. |
| `GET /certificates/{id}.pdf` | Download the real incident record. |
| `GET /certificates/{id}/verify` | Check certificate integrity using the local backend. |

The four current scenarios are `ceo-wire-scam`, `homoglyph-clone`, `wifi-compression-edge-case` and `creator-copyright`. The sandbox perturbs current evidence and requests another inspection. Preserve its controls, tripwire banner, optional environmental details, dossier export and incident-brief actions when reorganizing UI code. A scenario label is an assumption in a demonstration, not detector proof.

## Invariants to preserve

- Evidence changes invalidate the previous verdict and audit eligibility. Pending responses must match the current state revision before rendering. Aborted or failed inspections must not restore an older assessment.
- Every full inspection needs at least two actually evaluated modalities. The dashboard requires readable media plus accompanying text; the backend makes the final coverage determination. An unreadable file, empty frame, silent audio or URL cannot be silently counted as usable evidence.
- Keep original files in the browser. Send only bounded numeric samples to the loopback API: images reduced to at most 128 × 128 grayscale pixels, audio limited to the first six seconds at 16 kHz, or a single video frame. Label that video's missing audio, lip-sync and temporal-liveness measurements. Do not add browser storage, raw-file uploads or remote media fetching.
- Render API and user content with safe DOM operations such as `textContent`. Keep error and loading states visible, release temporary object URLs, and leave the interface usable after request failures.
- Display all five trust dimensions, both ledger polarities, unavailable evidence, the rule-based dialectic and the independent verification playbook. Scores are heuristic indices, not authenticity probabilities. Missing dimensions and low anomaly values do not verify identity.
- Keep simulation notices and uncertainty caveats visible. Sandbox perturbations must not invent provenance, turn unchecked metadata into a verified anchor, or replace backend measurements with a fabricated verdict.
- Audit signing requires a current case, every independently completed playbook step, substantive notes, an analyst identifier and an explicit decision. Certificate integrity does not certify the claim's truth. Keep dashboard certificate links on loopback even when the QR uses a separately configured public base URL.
- Keep decoded samples out of user-requested dossier exports and incident briefs. Preserve keyboard access, labeled controls, live status announcements, readable mobile layouts and reduced-motion support.

## Browser verification

The suite needs a resolvable `playwright` Node module and a Chromium executable. Reuse an existing installation when available. If Playwright is installed in the repository's `node_modules`, its normal module resolution is sufficient. To use an installation elsewhere, set absolute paths:

```powershell
$env:PLAYWRIGHT_MODULE = 'C:\path\to\node_modules\playwright'
$env:PLAYWRIGHT_CHROMIUM_EXECUTABLE = 'C:\path\to\chrome.exe'
node frontend/tests/browser-smoke.cjs
```

Without an executable override, Playwright uses its installed Chromium. With the backend still running, either entry point executes the same suite:

```powershell
node frontend/tests/browser-smoke.cjs
node scripts/test_dashboard.cjs
```

Choose one command per verification run. You can also run `node tests/browser-smoke.cjs` from `frontend/`; artifacts always go to the repository's `scratch/dashboard-smoke/`, regardless of the working directory. A failed assertion exits nonzero and attempts to capture `failure.png`.

The suite exercises all four scenarios against real `/api/v1` responses; compares exact vector, ledger, dialectic and playbook rendering; checks the creator tripwire; verifies missing-evidence rejection and stale-response invalidation; decodes synthetic PNG, WAV and WebM inputs in Chromium; registers and detects a canary; and obtains a real audit PDF and valid integrity response. It checks for browser errors and horizontal overflow at 1440px and 390px, then saves `dashboard-desktop.png`, `dashboard-mobile.png` and `report.json`.

The suite does not currently exercise every sandbox toggle, optional environmental panel or export/clipboard action. Manually check those when affected by a change. Browser media-decoding limits and the displayed extractor timings have different scopes; this suite is not a CPU extractor benchmark.
