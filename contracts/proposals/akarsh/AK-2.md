# AK-2: confirm two uncertainty-raising detector fixes are v1-compatible

Owner: akarsh
Status: proposed
Current contract: v1
Related module task: AK-2 (see `backend/app/forensics/VALIDATION.md`, "AK-2 fixes")

## Problem and current behavior

The AK-1 perturbation bench reproduced two cases where a v1 extractor reported a usable measurement at ordinary uncertainty, although the input could not support one:

- `cross_modal_sync.analyze`: for periodic traces, two alignments one period apart are equally correlated. For 2 Hz traces with a true +300 ms mouth delay, v1 returns `lagMs = -200` (opposite sign) at `uncertainty = 0.35`.
- `audio_vocoder.analyze`: peak normalization lifts a bare noise floor to full scale. A 1e-5 dither is evaluated with `activeFrameFraction = 1.0` at the ordinary `uncertainty = 0.45`.

A third fix (homoglyph tokenization across combining marks) restores the documented v1 meaning and needs no decision.

## Exact protocol change

No signature, required metric, type, unit, bound, score formula or abstention rule changes. Both fixes only add a condition that **raises** `uncertainty`, plus additive diagnostic metrics:

- `cross_modal_sync`: if correlation ≥ 0.3 and another distinct local correlation peak is within 0.05 of the best, `uncertainty = 0.75` and the first finding names both alignments. `score` and `lagMs` are unchanged. New metrics: `ambiguousLag: bool`, `alternativeLagMs: float | null` (ms, same sign convention as `lagMs`).
- `audio_vocoder`: new metric `peakDbfs: float` (pre-normalization peak, dBFS). If it is below −60, `uncertainty = max(existing, 0.80)` and a noise-floor finding is appended. `score` is unchanged.

Synthetic example (2 Hz traces, 200 samples at 25/s, +300 ms delay):

```json
before: {"score": 0.2, "uncertainty": 0.35, "metrics": {"lagMs": -200.0}}
after:  {"score": 0.2, "uncertainty": 0.75, "metrics": {"lagMs": -200.0, "ambiguousLag": true, "alternativeLagMs": 320.0}}
```

## Compatibility and independent progress

This is additive for consumers. At uncertainty ≥ 0.70 the core already renders a ledger item neutral, so these two cases become neutral instead of green/red. Because overall uncertainty is bounded by the least usable source, a verdict containing one of them becomes inconclusive. That is the intended effect for evidence that cannot be localized or has no usable level. The CEO scenario and every benign bench control are unchanged, and the full suite passes (295 passed, 1 optional skip). No consumer edits are required. If Gautham prefers not to adopt the policy in v1, the two uncertainty lines can be reverted while keeping the additive metrics and the homoglyph fix.

## Acceptance

- `python -m pytest tests/forensics/test_perturbation_bench.py -q`: the regressions `test_sync_ambiguous_periodic_peaks_are_not_reported_confidently`, `test_sync_ambiguity_names_both_alignments_and_spares_irregular_speech`, `test_audio_near_silent_dither_is_not_treated_as_ordinary_audio` and `test_audio_near_silent_rule_only_changes_uncertainty_below_minus_60_dbfs` pass. They failed before the fix.
- `python scripts/check_module.py forensics` and `python scripts/export_contracts.py --check` pass.
- Latency is unchanged in the warmed performance test (all extractors < 15 ms max on the tested host).

## Integration record — Gautham fills on acceptance

Decision, contract version, integration commit, migration notes and follow-up tasks:
