# PROFILE-1: stop false low authenticity scores in the browser extension

Owner: akarsh (reporter; the fixes belong to Gautham and Achumit)
Status: accepted
Current contract: v1
Related module task: ML-1 follow-up, found while rehearsing the extension demo

## Problem and current behavior

While we demonstrated the extension, genuine profiles showed very low authenticity scores. On current `main` (`78cefc4`) three independent causes produce this; each was reproduced through `POST /api/v1/extension/evaluate-profile`:

1. **Sticky reference handle (extension, Achumit).** `extension/content.js` stores the popup's reference handle when "Inspect this profile" is clicked, and only clears it on Stop. SPA navigation keeps monitoring with the same reference, so every profile visited afterwards is compared against a handle that belongs to someone else.
2. **Any different handle is a red flag (profiles endpoint, Gautham).** `profile:handle_reference_mismatch` is emitted as `red_flag` whenever the handle differs from the reference, even for completely unrelated accounts. Together with cause 1, every unrelated profile is "suspicious".
3. **One red flag collapses the score (profiles endpoint, Gautham).** With any red flag, `consistency = max(0.05, 0.40 − 0.15·red_count − risk)`: at most 0.25, usually 0.05, whatever the flag's strength. There is no middle ground.
4. **AI-text red flag on polished bios (core wiring of ML-1, Gautham + Akarsh).** Corporate "About" text ("Results-driven product manager… passionate about leveraging…") is scored as AI-written with high confidence and becomes a red flag, so the profile falls to 5/100. ML-1 validation already showed this classifier misreads polished and technical prose. AI-assisted bios are also common and legitimate.

Measured on `main` (`78cefc4`) vs `main` + the three patches below (same 64×64 avatar and requests for both):

| Profile | main today | with PROFILE-1 |
| --- | ---: | ---: |
| Ordinary profile, short bio | 71/100 (no red) | 71/100 (no red) |
| Polished LinkedIn-style bio | **5/100** (ai_text_classifier) | 71/100 (no red) |
| Unrelated profile, reference left over | **18/100** (handle_reference_mismatch) | 71/100 (no red) |
| Lookalike: Cyrillic а | 5/100 (homoglyph_hunter, handle_typosquat_lookalike) | 5/100 (unchanged) |
| Lookalike: typosquat `rajesh_vermaa` | 18/100 (handle_typosquat_lookalike) | 52/100 (still red) |
| Lookalike: separator padding `rajesh__verma` | 18/100 (handle_separator_variation) | 52/100 (still red) |
| Genuine account = reference | 74/100 (no red) | 74/100 (no red) |

Real lookalikes stay flagged. Only false alarms disappear, and single weaker flags now land in the amber middle instead of the floor.

## Exact protocol change

No schema, endpoint or contract change. Three patches, one per owner, each `git apply --check`-clean on `main` (`78cefc4`) and together:

| Patch | Owner | Change |
| --- | --- | --- |
| [`PROFILE-1-extension.patch`](PROFILE-1-extension.patch) (3 lines) | Achumit | `updateRoute()` clears `referenceHandle` when the page route changes: a reference describes the profile it was typed on. |
| [`PROFILE-1-profiles.patch`](PROFILE-1-profiles.patch) (8 lines) | Gautham | `handle_reference_mismatch` becomes `neutral_uncertain` with the finding "different account… not evidence of impersonation"; typosquat, separator and Unicode lookalikes stay `red_flag`. Red-path score becomes graded: `max(0.05, min(0.60, 0.75 − 0.20·red_count − 0.50·risk))`. The no-red continuous scoring from `78cefc4` is untouched. |
| [`PROFILE-1-core.patch`](PROFILE-1-core.patch) (3 lines) | Gautham | `ai_text_classifier` is added with `polarity_override="neutral_uncertain"`: it still contributes up to 0.6 to `mediaSynthesisScore` (SUSPICIOUS at most), but is shown as context, never as a red flag. |

## Compatibility and independent progress

- **Additive and behaviour-only.** Label strings, response fields and the v1 contract are unchanged.
- **Dashboard behaviour.** AI-generated images still raise red flags. AI-written text now appears under "Limitations & unavailable evidence" with its caveat instead of "Red flags". All five rehearsed demo acts keep their tiers.
- **Independent.** Each patch helps on its own. The extension patch removes cause 1, and the profiles patch removes the effect of causes 1–3 even if an old extension still sends a stale reference.

## Acceptance

- With all three patches on `main` `78cefc4`: `python -m pytest tests/ -q`: 351 passed, 1 skipped (models installed). `node --test extension/tests/*.test.cjs`: 47 passed.
- Live check: the patched build ran as the demo server with the extension loaded unpacked in Brave; genuine profiles no longer drop, and a Cyrillic lookalike still scores 5/100.
- Suggested regressions for the owners' test suites: an unrelated handle with a reference is not a red flag; a single typosquat flag scores between 0.3 and 0.6; a polished bio without other flags keeps the no-red score; navigating to a new route clears the reference handle.

## Integration record — Gautham fills on acceptance

- **Decision**: Formally accepted. The three patches (`PROFILE-1-extension.patch`, `PROFILE-1-profiles.patch`, and `PROFILE-1-core.patch`) are activated on main. This removes false alarms on corporate/polished bios and sticky reference handles while preserving strict detection and low scores for actual Cyrillic/typosquat lookalikes.
- **Contract Version**: v1 (backward-compatible; 0 schema, endpoint, or contract changes).
- **Integration Commit**: Combined commit on `main`.
- **Validation**: 49 extension tests passed; 85 core/contract tests and 347 full python suite passed; 0 contract drift against v1.
- **Follow-up Tasks**: None required; all three fixes are self-contained and active across extension, core, and profiles endpoints.
