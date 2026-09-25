# TrustGuard Extension Module — Validation & Verification Report

**Module Owner**: Achumit (`achumit/extension`)
**Completed Tasks**:
- **AC-1 (P0)**: Three-platform adapter fixture matrix (X, Instagram, LinkedIn)
- **AC-2 (P1)**: Monitoring lifecycle, debouncing, and request-bound hardening
- **AC-3 (P2)**: Popup/panel accessibility, incomplete-advisory handling, and UI usability
**Date**: September 25, 2026
**Environment**: Windows, Node.js v22+, Python 3.14

---

## 1. Scope & Acceptance

### AC-1: Platform Fixture Matrix
* Complete DOM fixture coverage for public profiles across **X (Twitter)**, **Instagram**, and **LinkedIn**.
* Automated fail-closed negative assertions for:
  - Missing profile header
  - Mismatched header / handle collision
  - Hidden duplicate headers (`display:none` mobile markup/drawers)
  - Stale canonical route (e.g., LinkedIn `<link rel="canonical">` mismatch during SPA transitions)
  - Malformed canonical and profile URLs
  - Unavailable avatar images (`naturalWidth = 0` / unloaded)
  - Cross-Origin canvas pixel security rejections (CORS tainted canvas)
* Strict verification that feed posts, tweets, captions, and private direct messages / InMails never enter the inspection payload.

### AC-2: Lifecycle, Monitoring & Rate-Limiting Hardening
* **Start / Stop Invariants**: Exactly one `MutationObserver` and one route timer per active tab session. Stopping immediately disconnects observers, clears timers, clears pending state, and tears down in-page panels.
* **Rapid SPA Navigation**: Fast same-tab route transitions during in-flight inspection invalidate tickets, discard stale responses, and prevent late rendering on new pages.
* **Feed / Message Route Invalidation**: Navigating to non-profile or reserved routes (`/home`, `/messages`, `/direct`, `/feed`) immediately clears panels.
* **Debounced Request Throttling**: Mutation bursts (50+ DOM mutations) are debounced and strictly throttled to at most one automatic API request per 5 seconds. Unchanged headers skip redundant network requests.
* **Memory Safety & Pixel Purge**: Raw sampled avatar pixel arrays are strictly disposed of (`delete payload.avatarPixels; pixels.length = 0;`) in `finally` blocks after both successful evaluations and backend / network errors.
* **Connection Resilience**: Graceful error handling and retry recovery when the background service worker or local API fails.

### AC-3: UI Usability, Accessibility & Untrusted Text
* **Complete vs. Incomplete Advisories**:
  - Complete evaluations (`inspectionComplete: true`) display the continuous authenticity score (`XX / 100`) alongside the 5D Trust Vector and evidence ledger.
  - Incomplete advisories (`inspectionComplete: false`) strictly withhold the continuous score as a dash (`—`), explicitly highlight missing modalities, and present evidence limitations. No single scalar establishes authenticity or identity.
* **Unavailable Dimensions**: Missing or null vector dimensions cleanly display `"Unavailable"` and fallback to 0 in meters without UI breakage.
* **Untrusted Text & XSS Mitigation**: All profile, verdict, and dialectic text is treated strictly as untrusted text using `textContent` and safe DOM construction. Proved zero script, image, or iframe element execution on hostile XSS strings.
* **Homoglyph Code-Point Formatting**: Lookalike Cyrillic characters and Unicode combining marks (e.g. `U+0430` + `U+0301`) are rendered accurately in the ledger without corruption.
* **Keyboard Navigation & ARIA**: In-page trigger pill button manages `aria-expanded` and `aria-controls`. Pressing `Escape` closes the panel and returns keyboard focus to the trigger pill button.
* **Error & Retry Flow**: Offline engine states and 422 errors render diagnostic feedback, clear old results, and leave the inspect button enabled for immediate retry.

---

## 2. Test Suite Matrix (49 Passing Tests)

The entire suite runs completely offline with zero npm dependencies using Node.js built-in test runner (`node --test extension/tests/*.test.cjs`).

### Platform Adapter Tests (`platforms.test.cjs`)
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
| **Footprint** | Social metrics | Extracts postsCount, followersCount, followingCount from header | **PASS** |
| **Multi-Image** | Post screening & memory safety | Caps at 3 images, samples 64×64 pixels, purges post pixels in finally | **PASS** |

### Lifecycle & Monitoring Tests (`lifecycle.test.cjs`)
| Area | Test Case | Target Behavior | Result |
| :--- | :--- | :--- | :--- |
| **Lifecycle** | Repeated Start / Stop | Exactly one observer and timer set; clean teardown on stop | **PASS** |
| **Navigation** | In-flight SPA transition | Discards stale result; prevents late rendering on new route | **PASS** |
| **Navigation** | Route change to feed | Route timer tick immediately destroys active panel | **PASS** |
| **Throttling** | Mutation bursts | 50+ rapid mutations throttled to ≤ 1 req / 5s; unchanged DOM skipped | **PASS** |
| **Memory** | Pixel disposal on success | `avatarPixels` deleted from payload; pixel buffer zeroed | **PASS** |
| **Memory** | Pixel disposal on error | `avatarPixels` purged in `finally` block on network / engine error | **PASS** |
| **Resilience** | Connection recovery | Extension connection failure handled cleanly; retry succeeds | **PASS** |

### UI Usability, Accessibility & Security Tests (`ui.test.cjs`)
| Area | Test Case | Target Behavior | Result |
| :--- | :--- | :--- | :--- |
| **Advisories** | Complete advisory | Displays score, evaluated modalities, 5D vector, dual ledger | **PASS** |
| **Advisories** | Incomplete advisory | Withholds continuous score as `—`; presents evidence limitations | **PASS** |
| **Dimensions** | Unavailable dimensions | Null dimensions render `"Unavailable"` without breaking meters | **PASS** |
| **Security** | Untrusted text & XSS | Malicious markup (`<script>`, `<img>`, `<iframe>`) rendered inert | **PASS** |
| **Homoglyphs** | Unicode code points | Cyrillic lookalikes and combining marks accurately formatted | **PASS** |
| **A11y** | Keyboard & ARIA | `aria-expanded` / `aria-controls` tracked; `Escape` closes and restores focus | **PASS** |
| **Resilience** | Popup error / retry | Offline engine state surfaces error and preserves retry capability | **PASS** |

### Baseline Extension Tests (`content.test.cjs` & `background.test.cjs`)
| Module | Test Case | Target Behavior | Result |
| :--- | :--- | :--- | :--- |
| **Background** | Sender validation | Rejects messages outside supported content tabs | **PASS** |
| **Background** | HTTP error surfacing | 422 errors reported honestly, not rendered as verdicts | **PASS** |
| **Background** | Scalar rejection | Outdated legacy scalar-only API responses rejected | **PASS** |
| **Background** | Loopback isolation | Loopback only, `credentials: omit`, `cache: no-store` | **PASS** |
| **Content** | Opt-in consent | Zero inspection or monitoring before user popup action | **PASS** |
| **Content** | Route validation | Non-profile routes rejected immediately | **PASS** |
| **Content** | Stale SPA header | Stale header detected and rejected | **PASS** |
| **Content** | Avatar sample bounds | 64×64 bounds enforced and pixels discarded | **PASS** |
| **Content** | CORS reporting | Honest CORS reporting without image payload | **PASS** |
| **Content** | Cross-route discard | In-flight response discarded when route changes | **PASS** |
| **Content** | Stop in-flight | In-flight inspection cancelled cleanly without late render | **PASS** |

---

## 3. Verification Gates & Execution Log

### Command Execution
```powershell
node --check extension/content.js
node --check extension/background.js
node --check extension/popup/popup.js
node --check extension/verdict-ui.js
node --test extension/tests/*.test.cjs
python scripts/export_contracts.py --check
python scripts/check_module.py extension
python scripts/check_ownership.py --owner achumit --base origin/main
git diff --check
```

### Test Runner Summary
```
ℹ tests 49
ℹ suites 0
ℹ pass 49
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms ~238ms
extension: all selected checks passed.
Ownership OK: Achumit.
```

---

## 4. Architectural Invariants Maintained

1. **Epistemic & Evidentiary Integrity**:
   - The extension presents the full calibrated 5D Trust Vector, red flags, green anchors, and verification playbook.
   - Missing or unreadable avatars are reported as incomplete advisories (`inspectionComplete: false`); no continuous score is presented as a substitute for evidence.
2. **Minimal Transient Footprint**:
   - No persistent storage (`chrome.storage` is not requested).
   - Zero background scraping; only loopback HTTP bridge to `127.0.0.1:8000`.
   - Sampled canvas pixels are destroyed immediately upon network dispatch or error.
3. **Safe Rendering**:
   - `verdict-ui.js` constructs DOM elements using textContent and safe DOM nodes; zero `innerHTML` usage.
