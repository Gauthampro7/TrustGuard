# TrustGuard Extension Module — Validation & Verification Report

**Module Owner**: Achumit (`achumit/extension`)  
**Completed Task**: AC-1 (P0) — Three-platform adapter fixture matrix  
**Date**: September 25, 2026  
**Environment**: Windows, Node.js v22+, Python 3.14  

---

## 1. Scope & Acceptance (AC-1)

* **X (Twitter)**, **Instagram**, and **LinkedIn** public profile header extraction matrix.
* Automated negative and fail-closed test coverage for:
  - Missing profile header
  - Mismatched header / identity handle collision
  - Hidden duplicate headers (e.g., hidden mobile drawers or duplicate SSR markup)
  - Stale canonical route (e.g., LinkedIn `<link rel="canonical">` mismatch during SPA transitions)
  - Malformed canonical and profile URLs
  - Unavailable avatar images (`naturalWidth = 0` / unloaded)
  - Cross-Origin canvas pixel security rejections (CORS tainted canvas)
* Strict verification that feed posts, tweets, captions, and private direct messages / InMails never enter the inspection payload.
* Refinement of platform adapters to guarantee graceful error handling and honest incomplete advisory presentation.
* Full preservation of existing baseline tests (11 baseline tests + 23 platform matrix tests = 34 total tests).

---

## 2. Fixture Matrix & Test Suite Summary

The test harness runs completely offline with zero npm dependencies using Node.js built-in test runner (`node --test extension/tests/*.test.cjs`).

| Platform | Test Case | Target Behavior | Result |
| :--- | :--- | :--- | :--- |
| **X** | Positive extraction | Extracts handle, displayName, bioText, 64×64 avatar | **PASS** |
| **X** | Feed/DM exclusion | Articles and DM drawer text never enter payload | **PASS** |
| **X** | Missing header | Fails closed: `"A matching public profile header was not found."` | **PASS** |
| **X** | Mismatched handle | Different handle in header fails closed | **PASS** |
| **X** | Hidden duplicate header | Hidden `display:none` element skipped; visible header selected | **PASS** |
| **X** | Unavailable avatar | Falls back to text-only advisory with observation note | **PASS** |
| **Instagram** | Positive extraction | Extracts handle, displayName, bioText, 64×64 avatar | **PASS** |
| **Instagram** | Post/DM exclusion | Post grid captions and direct message threads never enter payload | **PASS** |
| **Instagram** | Missing header | Fails closed: `"A public Instagram profile header was not found."` | **PASS** |
| **Instagram** | Mismatched handle | Heading handle mismatch fails closed | **PASS** |
| **Instagram** | Hidden duplicate header | Hidden mobile header skipped; visible header selected | **PASS** |
| **Instagram** | Reserved/non-profile routes | `/direct`, `/explore`, `/reels`, `/p/*`, `/stories/*` rejected | **PASS** |
| **Instagram** | CORS canvas rejection | Generates incomplete advisory (`inspectionComplete: false`) | **PASS** |
| **Instagram** | Unavailable avatar | Omits `avatarPixels`, returns informative note | **PASS** |
| **LinkedIn** | Positive extraction | Extracts handle, displayName, headline, 64×64 avatar | **PASS** |
| **LinkedIn** | Feed/InMail exclusion | `.feed-shared-update-v2` updates and InMails never enter payload | **PASS** |
| **LinkedIn** | Stale canonical route | Throws `"Wait for LinkedIn to finish navigating to the public profile."` | **PASS** |
| **LinkedIn** | Malformed canonical URL | Throws `"The profile address could not be matched."` | **PASS** |
| **LinkedIn** | Missing header / name | Missing top-card or empty name fails closed | **PASS** |
| **LinkedIn** | Hidden duplicate top-card | Hidden draft/template section skipped; visible top-card used | **PASS** |
| **LinkedIn** | Non-profile routes | `/feed`, `/messaging`, `/jobs`, `/in` rejected before inspection | **PASS** |
| **LinkedIn** | CORS canvas rejection | Generates incomplete advisory (`inspectionComplete: false`) | **PASS** |
| **Universal** | Malformed URLs | Malformed URI encodings (`/%E0%A4%A`) fail closed on all platforms | **PASS** |

---

## 3. Verification Commands & Execution Log

### A. JavaScript Syntax Checks
```powershell
node --check extension/content.js
node --check extension/background.js
node --check extension/popup/popup.js
node --check extension/verdict-ui.js
```
*Result*: Exit code 0 (all scripts valid).

### B. Extension Automated Test Suite
```powershell
node --test extension/tests/*.test.cjs
```
*Output*:
```
✔ background rejects requests outside supported content tabs (5.27ms)
✔ background surfaces API validation failures instead of rendering them as verdicts (3.71ms)
✔ background rejects legacy scalar-only API responses (2.88ms)
✔ background sends only to loopback with no cookies, redirects, or cache (4.35ms)
✔ does not inspect or monitor until the popup opts in (7.25ms)
✔ rejects feeds, direct messages, and post pages (18.76ms)
✔ refuses a stale profile header after SPA navigation (3.51ms)
✔ sends a bounded avatar sample and removes raw pixels after evaluation (13.01ms)
✔ reports CORS-blocked images honestly without an image payload (4.47ms)
✔ discards cross-route responses and clears the previous panel (6.54ms)
✔ stopping an in-flight inspection prevents late rendering (6.99ms)
✔ X: positive fixture extracts header, bio, and avatar pixels (28.02ms)
✔ X: feed posts and DMs never enter extracted payload (7.68ms)
✔ X: negative - missing header fails closed without payload (3.15ms)
✔ X: negative - mismatched header handle fails closed (3.02ms)
✔ X: negative - hidden duplicate header is ignored in favor of visible header (7.55ms)
✔ X: negative - unavailable avatar falls back to text-only advisory (5.91ms)
✔ Instagram: positive fixture extracts header, bio, and avatar pixels (7.90ms)
✔ Instagram: post captions and direct messages never enter payload (7.16ms)
✔ Instagram: negative - missing header fails closed (3.01ms)
✔ Instagram: negative - mismatched header handle fails closed (3.23ms)
✔ Instagram: negative - hidden duplicate header is ignored (6.55ms)
✔ Instagram: negative - reserved and non-profile routes are rejected (9.40ms)
✔ Instagram: negative - CORS canvas rejection reports incomplete advisory (2.90ms)
✔ Instagram: negative - unavailable avatar falls back cleanly (2.92ms)
✔ LinkedIn: positive fixture extracts name, headline, and avatar pixels (5.94ms)
✔ LinkedIn: feed updates and in-mail messages never enter payload (6.68ms)
✔ LinkedIn: negative - stale canonical route waits for navigation (2.24ms)
✔ LinkedIn: negative - malformed canonical URL fails closed (2.16ms)
✔ LinkedIn: negative - missing header or name fails closed (4.66ms)
✔ LinkedIn: negative - hidden duplicate top-card is ignored (4.92ms)
✔ LinkedIn: negative - non-profile routes are rejected before collection (7.29ms)
✔ LinkedIn: negative - CORS canvas rejection reports incomplete advisory (2.41ms)
✔ Universal: malformed URL fails closed on all platforms (4.47ms)
ℹ tests 34 | pass 34 | fail 0 | duration_ms ~356ms
```

### C. Contract & Module Boundary Gates
```powershell
python scripts/export_contracts.py --check
python scripts/check_module.py extension
python scripts/check_ownership.py --owner achumit --base origin/main
git diff --check
```
*Result*: All gates pass. `Ownership OK: Achumit`.

---

## 4. Remaining Selector Assumptions & Live Platform Notes

1. **X (Twitter)**:
   - Assumes profile header lives in `<main>` with `[data-testid="UserName"]`, `[data-testid="UserDescription"]`, and avatar anchor matching `/${handle}/photo`.
   - Articles (`<article>`) are explicitly excluded to prevent reading feed content or comments.
2. **Instagram**:
   - Assumes profile header is enclosed in `<header>` inside `<main>` with heading (`[data-testid="user-name"]`, `h1`, `h2`) matching `@handle`.
   - Name is drawn from `[data-testid="profile-name"]` or `h1`; bio from `[data-testid="user-bio"]`, `[data-testid="profile-bio"]`, or `.biography`.
   - Live Instagram dynamic layout changes may introduce new class names; synthetic fixtures cover standard test-id patterns.
3. **LinkedIn**:
   - Assumes top card uses `.pv-top-card`, `.top-card-layout`, or `section` with `h1` and `.text-body-medium` or `.top-card-layout__headline`.
   - Stale navigation is safeguarded via `link[rel="canonical"]` cross-checking against `location.pathname`.
   - Posts in `.feed-shared-update-v2` and messaging overlay elements are strictly outside the top-card boundary.
4. **General Security**:
   - All extracted DOM strings are bounded: `displayName` (≤ 256 chars), `bioText` (≤ 6000 chars).
   - Avatar pixels (if canvas permits) are downsampled to a bounded 64×64 grayscale matrix and erased from memory immediately after dispatch.
   - Text rendering in `verdict-ui.js` uses strict `textContent` node insertion with zero `innerHTML` injection.
