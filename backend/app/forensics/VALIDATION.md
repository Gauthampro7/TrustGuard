# Forensics module validation — AK-1 perturbation bench, AK-2 fixes and AK-3 latency

Owner: Akarsh · Branch: `akarsh/forensics` · Contract: `contracts/v1/forensics.json` (unchanged)

This note records how the nine v1 extractors respond to seeded **synthetic** controls. The controls are generated signals (textures, harmonic tones, bursty envelopes, exponential decays, ROI traces, fixed strings). They are **not** a labeled real-world corpus, and nothing here measures deepfake-detection accuracy. They show which ordinary transformations each heuristic tolerates, which ones it flags, and where it abstains.

## Reproduce

```bash
python -m pytest tests/forensics/test_perturbation_bench.py -q     # invariants + AK-2 regressions
python -m tests.forensics.fixtures.controls --seeds 20              # prints the table below
```

- Controls: `tests/forensics/fixtures/controls.py`. Every control takes a seeded `numpy.random.Generator` and is deterministic per seed (tested).
- Host for the numbers below: Apple M4, macOS 26.6.2 (arm64), Python 3.13.7, NumPy 2.4.6. The team constraint targets Python 3.11; no numeric difference is expected, but Gautham's integration run should confirm.
- `Kind` is the control's role: `benign` = ordinary input, `perturbed` = known transformation, `abstain` = input that must not be measured.
- For `canary_tripwire` (dictionary interface) the score column is `tripwireTriggered` as 0/1 and uncertainty is not applicable.
- `perceptual_hash` reports 0.75 on a match at module level; the core re-weights a match to a neutral 0.35 because reuse may be authorized.

## Observed distributions (20 seeds, after AK-2)

| Module | Control | Kind | Evaluated | Score min / median / max | Uncertainty median |
| --- | --- | --- | ---: | --- | ---: |
| spatial_fft | natural texture | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.40 |
| spatial_fft | natural texture, normalized 0-1 input | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.40 |
| spatial_fft | quantized to 16 levels | perturbed | 20/20 | 0.00 / 0.00 / 0.13 | 0.40 |
| spatial_fft | 2x stride + nearest upsample | perturbed | 20/20 | 0.00 / 0.00 / 0.02 | 0.40 |
| spatial_fft | 8x8 block flattening | perturbed | 20/20 | 0.00 / 0.00 / 0.09 | 0.40 |
| spatial_fft | additive sensor noise sd 8 | perturbed | 20/20 | 0.00 / 0.00 / 0.18 | 0.40 |
| spatial_fft | checkerboard amplitude 12 | perturbed | 20/20 | 0.50 / 0.50 / 0.50 | 0.40 |
| spatial_fft | near-constant frame, +/-1 level dither | perturbed | 20/20 | 0.12 / 0.15 / 0.37 | 0.75 |
| spatial_fft | constant frame | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| spatial_fft | 12x12 frame | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| audio_vocoder | speech-like tone | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.45 |
| audio_vocoder | speech-like tone, scaled x0.05 | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.45 |
| audio_vocoder | resampled 16k->8k->16k | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.45 |
| audio_vocoder | native 8 kHz | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.45 |
| audio_vocoder | 8-bit quantization | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.45 |
| audio_vocoder | STFT phase scrambled | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.45 |
| audio_vocoder | three 100 ms exact-zero gates | perturbed | 20/20 | 0.55 / 0.55 / 0.55 | 0.45 |
| audio_vocoder | three 100 ms low-noise gates | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.45 |
| audio_vocoder | near-silent dither 1e-5 | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.80 |
| audio_vocoder | digital silence | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| audio_vocoder | 0.05 s clip | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| stylometry_drift | business text | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.48 |
| stylometry_drift | business text vs same baseline | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.48 |
| stylometry_drift | topic shift vs baseline | perturbed | 20/20 | 0.32 / 0.32 / 0.32 | 0.56 |
| stylometry_drift | first 5 words | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.97 |
| stylometry_drift | first 15 words | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.91 |
| stylometry_drift | first 40 words | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.75 |
| stylometry_drift | 20 words vs baseline (too short) | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.88 |
| stylometry_drift | urgency + payment + bypass | perturbed | 20/20 | 0.85 / 0.85 / 0.85 | 0.35 |
| stylometry_drift | Hindi request | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| stylometry_drift | digits and punctuation only | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| cross_modal_sync | mouth lag +0 ms | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.35 |
| cross_modal_sync | mouth lag +200 ms | perturbed | 20/20 | 0.20 / 0.20 / 0.20 | 0.35 |
| cross_modal_sync | mouth lag -200 ms | perturbed | 20/20 | 0.20 / 0.20 / 0.20 | 0.35 |
| cross_modal_sync | periodic 2 Hz traces, 120 ms lag | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.75 |
| cross_modal_sync | periodic 2 Hz traces, 300 ms lag | perturbed | 20/20 | 0.20 / 0.20 / 0.20 | 0.75 |
| cross_modal_sync | lag beyond +/-600 ms search | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.90 |
| cross_modal_sync | independent noise traces | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.90 |
| cross_modal_sync | constant mouth | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| cross_modal_sync | 0.4 s traces | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| homoglyph_hunter | Latin handle | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.35 |
| homoglyph_hunter | Cyrillic name | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.35 |
| homoglyph_hunter | Greek name | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.35 |
| homoglyph_hunter | Devanagari name | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.35 |
| homoglyph_hunter | separate-language tokens | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.35 |
| homoglyph_hunter | Latin with combining acute | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.35 |
| homoglyph_hunter | same handle as reference | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.15 |
| homoglyph_hunter | Cyrillic a in Latin handle | perturbed | 20/20 | 0.65 / 0.65 / 0.65 | 0.35 |
| homoglyph_hunter | Cyrillic a vs reference | perturbed | 20/20 | 0.90 / 0.90 / 0.90 | 0.15 |
| homoglyph_hunter | l->1 digit swap vs reference | perturbed | 20/20 | 0.90 / 0.90 / 0.90 | 0.15 |
| homoglyph_hunter | Cyrillic o + combining acute in Latin handle | perturbed | 20/20 | 0.65 / 0.65 / 0.65 | 0.35 |
| homoglyph_hunter | combining acute after leading Cyrillic a | perturbed | 20/20 | 0.65 / 0.65 / 0.65 | 0.35 |
| homoglyph_hunter | combining acute vs plain reference | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.15 |
| homoglyph_hunter | bidi override | perturbed | 20/20 | 0.45 / 0.45 / 0.45 | 0.35 |
| homoglyph_hunter | empty identifier | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| perceptual_hash | authorized reuse, identical | benign | 20/20 | 0.75 / 0.75 / 0.75 | 0.35 |
| perceptual_hash | reuse, brightness +20 | perturbed | 20/20 | 0.75 / 0.75 / 0.75 | 0.35 |
| perceptual_hash | reuse, 16-level quantization | perturbed | 20/20 | 0.75 / 0.75 / 0.75 | 0.35 |
| perceptual_hash | reuse, 8x8 block flattening | perturbed | 20/20 | 0.75 / 0.75 / 0.75 | 0.35 |
| perceptual_hash | reuse, 2x resampled | perturbed | 20/20 | 0.75 / 0.75 / 0.75 | 0.35 |
| perceptual_hash | reuse, 5% border crop | perturbed | 20/20 | 0.00 / 0.00 / 0.75 | 0.35 |
| perceptual_hash | reuse, noise sd 8 | perturbed | 20/20 | 0.75 / 0.75 / 0.75 | 0.35 |
| perceptual_hash | unrelated images | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.35 |
| perceptual_hash | no reference | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| perceptual_hash | constant reference | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| canary_tripwire | unmarked text | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.00 |
| canary_tripwire | verbatim copy | perturbed | 20/20 | 1.00 / 1.00 / 1.00 | 0.00 |
| canary_tripwire | copy with edits around marker | perturbed | 20/20 | 1.00 / 1.00 / 1.00 | 0.00 |
| canary_tripwire | platform strips zero-width | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.00 |
| canary_tripwire | marker truncated by length limit | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.00 |
| environmental_acoustic | RT60 0.3 s declared office | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.55 |
| environmental_acoustic | RT60 0.8 s declared conference hall | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.55 |
| environmental_acoustic | RT60 1.5 s declared studio | perturbed | 20/20 | 0.60 / 0.60 / 0.60 | 0.55 |
| environmental_acoustic | RT60 0.8 s, tail noise -60 dB | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.55 |
| environmental_acoustic | RT60 0.8 s, tail noise -45 dB | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.55 |
| environmental_acoustic | RT60 0.8 s, tail noise -30 dB | perturbed | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| environmental_acoustic | RT60 0.8 s truncated at 0.25 s | perturbed | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| environmental_acoustic | speech submitted as IR | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| environmental_acoustic | silent response | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| rppg | 1.2 Hz pulse | benign | 20/20 | 0.00 / 0.00 / 0.00 | 0.65 |
| rppg | 1.2 Hz pulse at 10 samples/s | perturbed | 20/20 | 0.00 / 0.00 / 0.00 | 0.65 |
| rppg | pulse + strong shared illumination | perturbed | 19/20 | 0.00 / 0.00 / 0.00 | 0.65 |
| rppg | shared illumination only | perturbed | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| rppg | pulse drifts 1.0 -> 1.8 Hz | perturbed | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| rppg | noise only | perturbed | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |
| rppg | 6 s trace | abstain | 0/20 | 0.00 / 0.00 / 0.00 | 1.00 |

## What the controls show

**spatial_fft.** Input scale (0–1 versus 0–255) gives identical metrics. 16-level quantization, 2× stride + nearest upsampling, 8×8 block flattening and sensor noise all stay below the 0.35 review finding (max 0.18). The heuristic therefore does **not** detect ordinary resampling or compression. It responds to a strong pixel-periodic grid (checkerboard: spectral peak ratio 8.1, score 0.50). A near-constant ±1-level dither reaches 0.37 on one seed, but the low-contrast rule keeps uncertainty at 0.75, so it stays neutral.

**audio_vocoder.** Amplitude scale, 16k→8k→16k resampling, native 8 kHz and 8-bit quantization do not move the score. STFT phase scrambling triples `phaseDiscontinuityRate` (median 0.005 → 0.017) but stays far below the 0.18 onset, so the phase term does not respond to this edit. Three exact-zero 100 ms gates score 0.55. A noise gate or packet-loss concealment that writes exact zeros is a plausible benign cause, and the finding says so. The same gates with a 1e-4 noise floor score 0. Native 8 kHz synthetic tones give a phase rate of exactly 0 on every seed; this is recorded, not yet explained.

**stylometry_drift.** Uncertainty falls monotonically with length (5 words 0.97, 15: 0.91, 40: 0.75, full: 0.48). A 20-word text skips baseline comparison (uncertainty 0.88). A topic shift against a same-author baseline gives drift 0.32, above a same-text baseline (0). Topic, not authorship, explains it, as the finding states. Hindi text is evaluated at uncertainty 1.0 with a limited-coverage finding.

**cross_modal_sync.** Lag sign is recovered exactly for ±200 ms under noise (correlation > 0.99). Offsets beyond the ±600 ms search window look like unrelated traces: correlation < 0.3, score 0, uncertainty 0.9. A large desynchronization is therefore **undetermined**, not flagged. Periodic traces with equally strong alignments are now reported as ambiguous (AK-2 fix 2).

**homoglyph_hunter.** Cyrillic, Greek and Devanagari names, separate-language tokens, and Latin names with combining accents are not flagged. A Cyrillic `а` in a Latin handle scores 0.65 (0.90 against a reference), an `l→1` swap collides with its reference (0.90), and a bidi override scores 0.45. Combining accents no longer split identifier tokens (AK-2 fix 1).

**perceptual_hash.** Identical reuse, +20 brightness, 16-level quantization, block flattening, 2× resampling and noise all match (Hamming ≤ 6). Unrelated textures are separated by 24–38 bits. A 5% border crop defeats the global DCT hash on most seeds (distance 4–14, median 10). Crop-robust reuse is outside this hash's reach.

**canary_tripwire.** Verbatim copies and copies edited around the marker trigger. Stripping zero-width characters or truncating the marker removes the evidence, and the explanation states that absence does not rule out copying.

**environmental_acoustic.** Schroeder T20 recovers RT60 0.3 / 0.8 / 1.5 s within ±4% on clean decays, and within +5% with −45 dB tail noise (bias upward as noise rises). −30 dB tail noise and a response truncated at 0.25 s abstain, as does speech submitted as an impulse response. A 1.5 s decay declared as a studio gives the bounded 0.60 context index.

**rppg.** A 1.2 Hz component is recovered at 1.17 Hz (FFT bin) at 25 and 10 samples/s. Shared illumination alone, a drifting 1.0 → 1.8 Hz component and noise alone all abstain. Strong shared flicker masks a real component on 1 of 20 seeds. `biologicalLivenessEstablished` is always false.

## AK-2 fixes

The AK-1 bench reproduced three issues. Each had a failing regression before its fix (`tests/forensics/test_perturbation_bench.py`). Only the four affected bench rows changed (the table above). Every benign control and the one scenario with lip-sync traces (`ceo-wire-scam`) are unchanged, and the full repository suite passes (295 passed, 1 optional skip).

1. **Combining marks split identifier tokens** (`homoglyph_hunter`). `\w+` excludes combining marks (category M), so `"а́pple"` tokenized as `а` + `pple` and scored 0 despite a counted confusable. Tokens now include letters, marks, numbers and connector punctuation, so a mark stays with its base letter. `"а́pple"`, `"paypáа"` and `"pо́stmaster"` score 0.65 and report the whole token. Accented Latin, Cyrillic, Greek and Devanagari names and separate-language tokens remain unflagged. Largest-input latency: 12.2 ms max.
2. **Ambiguous periodic lag was reported confidently** (`cross_modal_sync`). For 2 Hz traces with a true +300 ms mouth delay, −200 ms was equally correlated, chosen as the closer peak and reported at uncertainty 0.35. When a distinct local correlation peak is within 0.05 of the best (and correlation ≥ 0.3), uncertainty is now 0.75 and the finding names both alignments. The chosen `lagMs` and the score are unchanged. Additive metrics: `ambiguousLag` (bool), `alternativeLagMs` (ms or null). Irregular speech-like controls at 0/±200 ms are never ambiguous (20/20 seeds).
3. **Near-silent audio was evaluated as ordinary audio** (`audio_vocoder`). Peak normalization lifted 1e-5 noise to full scale. The pre-normalization peak is now recorded as the additive metric `peakDbfs`; below −60 dBFS uncertainty is raised to 0.80 with a noise-floor finding. The score is unchanged, and a quiet clip at −28 dBFS keeps the ordinary 0.45.

**Contract note for review.** No v1 names, types, units, bounds, required metrics or score formulas changed; three diagnostic metrics were added. Fixes 2 and 3 add new conditions that *raise* uncertainty in cases the v1 policy did not anticipate. They never lower it and never change a score. Gautham should confirm this counts as a compatible fix rather than an uncertainty-policy change needing a proposal.

Still documented limits, not defects: phase-scramble insensitivity, exact-zero gate sensitivity, pHash crop fragility, canary stripping. Changing any of them alters a v1 score meaning and needs a contract proposal first.

## AK-3 bounded laptop latency

Reproduce with `python -m tests.forensics.benchmark --repeats 100` (add `--json` for machine-readable output). `tests/forensics/test_performance.py` runs the same workloads with 20 warmed calls and asserts p95 < 150 ms, printing median, p95 and max.

Each workload is the largest input the v1 extractor accepts, shaped so the extractor **fully evaluates**. The benchmark refuses to time a workload that abstains. Inputs are Python lists, as the API delivers them, so list-to-array conversion counts as extractor time. Fixtures are built before timing. Cold costs come from a fresh subprocess per workload.

Host: Apple M4 · macOS-26.6.2-arm64-arm-64bit-Mach-O · Python 3.13.7 · NumPy 2.4.6 · 100 warmed calls after 3 warm-ups, GC paused during timing.

| Extractor workload | Bound exercised | Median ms | p95 ms | Max ms | < 150 ms |
| --- | --- | ---: | ---: | ---: | :---: |
| spatial_fft | 256x256 RGBA list | 8.82 | 8.99 | 9.08 | yes |
| audio_vocoder@16k | 96,000 samples, 16 kHz | 11.26 | 11.41 | 12.48 | yes |
| audio_vocoder@48k | 96,000 samples, 48 kHz | 11.24 | 11.40 | 11.55 | yes |
| stylometry_drift | 20,000 chars + 20,000-char baseline | 2.83 | 2.85 | 2.88 | yes |
| cross_modal_sync@25 | 1,500 paired samples, 25/s | 0.35 | 0.35 | 0.37 | yes |
| cross_modal_sync@120 | 1,500 paired samples, 120/s (widest lag search) | 1.37 | 1.38 | 1.44 | yes |
| homoglyph_hunter | 20,000 adversarial chars + reference | 11.20 | 11.49 | 11.55 | yes |
| perceptual_hash | two 256x256 RGBA lists | 16.27 | 16.69 | 17.11 | yes |
| canary_tripwire.detect | 20,000 chars | 0.01 | 0.01 | 0.01 | yes |
| canary_tripwire.generate | 19,800 chars | 0.01 | 0.01 | 0.02 | yes |
| environmental_acoustic | 96,000-sample measured IR, 16 kHz | 2.06 | 2.10 | 2.16 | yes |
| rppg@25 | 1,500 RGB means, 25/s (60 s) | 0.32 | 0.34 | 0.34 | yes |
| rppg@120 | 1,500 RGB means, 120/s (12.5 s) | 0.32 | 0.33 | 0.33 | yes |

| Extractor workload | NumPy import ms | Module import ms | Fixture build ms | First call ms |
| --- | ---: | ---: | ---: | ---: |
| spatial_fft | 27.2 | 1.1 | 14.1 | 10.4 |
| audio_vocoder@16k | 26.2 | 1.1 | 13.0 | 13.9 |
| audio_vocoder@48k | 26.2 | 1.1 | 13.2 | 13.7 |
| stylometry_drift | 26.3 | 1.1 | 0.0 | 3.3 |
| cross_modal_sync@25 | 26.5 | 1.1 | 8.7 | 0.4 |
| cross_modal_sync@120 | 26.5 | 1.1 | 8.9 | 1.5 |
| homoglyph_hunter | 26.4 | 2.8 | 0.0 | 18.6 |
| perceptual_hash | 26.3 | 1.1 | 19.3 | 18.9 |
| canary_tripwire.detect | 27.0 | 3.9 | 0.0 | 0.0 |
| canary_tripwire.generate | 27.0 | 3.9 | 0.0 | 0.0 |
| environmental_acoustic | 27.4 | 1.1 | 10.9 | 2.3 |
| rppg@25 | 27.3 | 1.1 | 8.9 | 1.4 |
| rppg@120 | 26.6 | 1.1 | 9.0 | 1.4 |

**Result: every extractor is under the 150 ms target at its documented bound on this host.** The slowest is `perceptual_hash` at 17.1 ms max. The widest lag search (`cross_modal_sync` at 120 samples/s, ±72 lags) takes 1.4 ms. No optimization was needed, so no detector code changed in AK-3, and uncertainty and abstention are untouched.

Where the time goes, measured separately on this host:

- **Image extractors are dominated by input conversion.** Converting one 256×256 RGBA list to an array takes about 7.2 ms (in `common.finite_array`, Gautham-owned). `spatial_fft` computes in about 1 ms and `perceptual_hash` in 0.6 ms on arrays. If image latency ever matters, the lever is the shared conversion or a denser API encoding, which would be a contract proposal, not a detector change.
- **`audio_vocoder` is compute-bound:** 11.4 ms on an array versus 1.2 ms for conversion (STFT, mel projection, phase residuals).
- **`homoglyph_hunter`** pays about 7 ms once to load the Unicode 17.0.0 confusables table on first call (18.6 ms cold versus 11.2 ms warm). The per-character tokenizer added in AK-2 keeps the warm 20,000-character adversarial case at 11.5 ms max.
- **Cold start:** NumPy import (about 27 ms) dominates process start-up. Detector module imports take 1–4 ms each.

Changes to measurement practice in AK-3: the previous performance test timed `cross_modal_sync` only at 25 samples/s and images only as RGB, so the 120 samples/s lag search and the RGBA bound were never measured. The environmental test built its fixture inside the timed call; fixture construction is now outside it.

Limits: one host (Apple M4, arm64). Python 3.13.7 was used because 3.11 (the team constraint) is not installed here; Gautham's integration run should record the Windows / 3.11 numbers. Timings exclude HTTP parsing, Pydantic validation and core synthesis.

## Out of scope

No existing thresholds were tuned in AK-1, AK-2 or AK-3. The bench and benchmark only call the public functions.
