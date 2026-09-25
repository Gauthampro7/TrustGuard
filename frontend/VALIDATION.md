# TrustGuard Dashboard Module Validation Report (Aril)

**Module Owner**: Aril Travass (`aril/dashboard`)  
**Date**: 2026-09-25  
**Baseline Commit**: `eac2fd5` (`origin/main`)  
**Tasks Delivered**: AR-1 (P0: Reversible Sandbox), AR-2 (P1: Accessibility & Non-Color Labels), AR-3 (P2: Failure & Export Regressions)  

---

## 1. Summary of Changes

### AR-1: Reversible Sandbox Perturbations for Every Bundle
- **Immutable Snapshot**: `state.originalBundle` snapshots clean text, handle, claimed identity, media items, and fixture data on scenario load (`scenarioChanged`) and custom file decoding (`chooseFiles`).
- **Input Derivation**: Perturbations (channel degradation, homoglyphs, urgency injection, canary tripwires) are derived strictly from `state.originalBundle`. Repeated clicks on "Apply" do not stack or duplicate urgency text or homoglyphs.
- **Degradation Zeroing**: When the degradation slider is returned to `0` and applied, `qualityDegradation` is explicitly deleted from all media item metadata rather than persisting as a stale string.
- **Bundle Reset**: Clicking "Reset perturbations" restores original text, handle, and numeric samples exactly for both simulated scenarios and custom user evidence, invalidating stale results and resetting audit button eligibility.

### AR-2: Accessibility, Keyboard, Status Announcements & Non-Color Labels
- **Non-Color-Only Indicators**: Added visible qualitative badges (`[HIGH]`, `[MODERATE]`, `[LOW]`, `[ELEVATED]`) next to numeric values for all five trust dimensions, plus an explicit verdict status badge in `#verdict-banner` (`❓ HIGH UNCERTAINTY (U ≥ 0.50) · CAPPED`, `⚠️ ELEVATED ANOMALY`, `🛡️ LOW ANOMALY`) so color-blind users and screen readers do not rely solely on color gradients.
- **Focus States**: High-contrast outline `:focus-visible` styled with `#1d4ed8` (contrast ratio > 6:1 against white and `#f4f6f8`), including focused states for `.verdict-banner` and `.skip-link`.
- **Keyboard Parity**: Added a dedicated, keyboard-activatable `📋 Copy marked text` button for the canary tripwire tool with live feedback; bound both `input` and `change` listeners on `#final-decision` select element.
- **ARIA Live Regions**: Removed initial HTML `hidden` from `#operation-status` and styled empty state via CSS `.operation-status:empty { display: none; }` to preserve screen reader accessibility tree registration; added `aria-live="polite"` and `aria-atomic="true"`.
- **Playbook Grouping**: Added `role="group"` and `aria-label="Verification playbook checklist"` to `#playbook-steps`; assigned `role="img"` and descriptive fallback to canvas elements.
- **Reduced Motion**: Styled `@media (prefers-reduced-motion: reduce)` with `animation-duration: 0.01ms !important; transition-duration: 0.01ms !important;` and cancelled button active transforms.
- **Responsive & Zoom**: Verified reflow and no horizontal overflow at 1440px desktop, 390px mobile, and 200% zoom (720px width reflow).

### AR-3: Failure & Export State Regressions
- **Network / Engine Failure**: Handled network rejection with honest "Cannot reach the local engine" status, restoring interactive UI and clearing busy states.
- **HTTP 422 Handling**: Formatted Pydantic validation errors cleanly, extracting location paths and messages while suppressing raw objects.
- **Interrupted Media Decoding**: Gracefully caught corrupted or unsupported files without hanging loading state; added 12s timeout race to audio decoding.
- **Truthful Clipboard Handling**: Captured permission denial in `copyBrief()`, truthfully displaying "Clipboard access unavailable; use JSON export" without claiming false success.
- **Pure JSON Dossier Export**: Verified that exported JSON contains only the current assessment verdict, strictly excluding raw media pixels, audio samples, or data URLs.
- **Audit Verification & Safety**: Verified that expired cases (404) and malicious/external URLs in signed certificates are rejected by `safeApiLink()`.

---

## 2. Gate Verification Commands & Results

All verification commands executed cleanly against the live backend server at `http://127.0.0.1:8000`:

### Syntax & AST Check
```powershell
node --check frontend/app.js
node --check frontend/tests/browser-smoke.cjs
node --check scripts/test_dashboard.cjs
```
**Result**: Exit code 0, all syntax valid.

### Frozen Contracts Check
```powershell
python -m pytest tests/contracts/ -q
python scripts/export_contracts.py --check
```
**Result**: 25 passed in 1.99s. v1 API, extractor ABI, and synthetic frozen examples valid.

### Ownership Boundary Check
```powershell
python scripts/check_ownership.py --owner aril --base origin/main
```
**Result**: `Ownership OK: Aril, 5 changed paths.` (Only files in `frontend/**`).

### Browser Smoke & Module Runner
```powershell
python scripts/check_module.py dashboard --browser
```
**Result**:
```json
{
  "passed": true,
  "checks": [
    "Missing evidence blocked before any inspection request",
    "All four real scenario requests rendered exact API vector, ledger, dialectic, tripwire and playbook values",
    "All independent steps, analyst notes and explicit decision gate audit; PDF and integrity links work",
    "Canary generated through local API with explicit session scope",
    "Custom image + text decoded to bounded grayscale numeric samples; raw file never posted; generated canary detected; HTML-like text safe",
    "Real WAV browser decode resamples 22.05 kHz audio to bounded 16 kHz samples",
    "Real WebM browser decode submits one visual frame and clearly marks missing audio/sync analysis",
    "Changing evidence invalidates pending results and prevents stale audit sign-off",
    "AR-1: Sandbox reversible for scenario and custom bundles: 70% -> 0%, repeated apply, and reset restore originals and clear stale results",
    "AR-2: Keyboard accessible controls, high-contrast focus, non-color uncertainty badges, live regions, and 200% zoom reflow verified",
    "AR-3: Regressions for engine unavailable, 422, interrupted media, clipboard denial, expired audit link, and pure JSON export pass",
    "1440px desktop and 390px mobile have no horizontal overflow or browser errors"
  ],
  "scenarios": [
    {
      "id": "ceo-wire-scam",
      "tier": "HIGH_IMPERSONATION_RISK",
      "vector": {
        "mediaSynthesisScore": 0.55,
        "crossModalDiscordanceScore": 0.5,
        "identityMismatchScore": 0,
        "contextualAnomalyScore": 0.85,
        "epistemicUncertainty": 0.4562
      },
      "elapsedMs": "5.408",
      "ledgerSignals": 6
    },
    {
      "id": "homoglyph-clone",
      "tier": "HIGH_IMPERSONATION_RISK",
      "vector": {
        "mediaSynthesisScore": 0.0323,
        "crossModalDiscordanceScore": 0,
        "identityMismatchScore": 0.9,
        "contextualAnomalyScore": 0.35,
        "epistemicUncertainty": 0.4688
      },
      "elapsedMs": "2.304",
      "ledgerSignals": 5
    },
    {
      "id": "wifi-compression-edge-case",
      "tier": "UNCERTAIN_COMPRESSION_NOISE",
      "vector": {
        "mediaSynthesisScore": 0.1633,
        "crossModalDiscordanceScore": 0,
        "identityMismatchScore": 0,
        "contextualAnomalyScore": 0.17,
        "epistemicUncertainty": 0.8
      },
      "elapsedMs": "1.178",
      "ledgerSignals": 5
    },
    {
      "id": "creator-copyright",
      "tier": "HIGH_IMPERSONATION_RISK",
      "vector": {
        "mediaSynthesisScore": 0,
        "crossModalDiscordanceScore": 0,
        "identityMismatchScore": 0.9,
        "contextualAnomalyScore": 0.55,
        "epistemicUncertainty": 0.45
      },
      "elapsedMs": "2.147",
      "ledgerSignals": 6
    }
  ],
  "screenshots": [
    "scratch/dashboard-smoke/dashboard-desktop.png",
    "scratch/dashboard-smoke/dashboard-mobile.png"
  ]
}
dashboard: all selected checks passed.
```

---

## 3. Changed Files Inventory

- [`frontend/app.js`](app.js): Sandbox reversibility, immutable snapshot derivation, non-color labels, live announcements, 422 error extraction, audio timeout race, and clipboard fallback.
- [`frontend/index.html`](index.html): Accessible live regions, qualitative dimension badges, canary copy button, and playbook group roles.
- [`frontend/styles.css`](styles.css): High-contrast `:focus-visible`, dimension badges, reduced-motion rules, and responsive flex wrap.
- [`frontend/tests/browser-smoke.cjs`](tests/browser-smoke.cjs): Full integration regressions covering AR-1, AR-2, and AR-3.
- [`frontend/VALIDATION.md`](VALIDATION.md): Module validation report.
