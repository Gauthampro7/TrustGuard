# TrustGuard implementation validation

## Integrated release validation (GA-4)

Validated on 2026-09-25 after integrating all team modules into `main`:
- **Core, contracts & integration (Gautham)**: GA-1 baseline, GA-2 validation gaps (chunked streaming limits, concurrent/repeated audit requests, true LRU cache eviction, failed canary registration, and zero raw-sample leakage), GA-3 trustworthy diagnostics.
- **Forensic extractors (Akarsh)**: AK-1 seeded perturbation bench, AK-2 reproduced edge-case fixes (sync ambiguity, near-silent vocoder dither, homoglyph combining mark normalization), AK-3 bounded latency benchmark for every extractor.
- **Chrome extension (Achumit)**: AC-1 three-platform adapter matrix (X, Instagram, LinkedIn), fail-closed handling on malformed URLs/missing headers, zero feed/DM leakage into payloads.
- **Dashboard frontend (Aril)**: AR-1 reversible adversarial sandbox (0%–70% degradation slider, live apply/reset), AR-2 accessibility (high contrast focus, ARIA live regions, non-color-only badges, 200% zoom reflow), AR-3 failure regressions (engine unavailable, 422 payload errors, interrupted media, expired audit link handling).

### Full validation test results
- `python scripts/check_module.py all --browser`: **ALL PASSED**.
  - `python scripts/export_contracts.py --check`: **Valid** (zero drift against v1 contracts and extractor ABI).
  - `python -m pytest tests/`: **336 passed** (including core API, contract architecture, forensic measurements, environmental acoustic, performance, and perturbation bench).
  - JavaScript syntax checks: `node --check` passed for all frontend and extension scripts.
  - `node --test extension/tests/*.test.cjs`: **47 passed** (background, content, platforms fixture matrix, lifecycle debouncing/disposal, UI accessibility/security).
  - `node frontend/tests/browser-smoke.cjs`: **12/12 checks passed** in real headless Chromium against the live backend API.
- `python scripts/diagnostics.py`: **5/5 passed** (~650 ms runtime across all four live scenario extractions, reporting versions, uncertainty bounds, and per-extractor timings without calling whole-request run an SLA).

### Bounded laptop benchmark measurements (AK-3 on Windows)
Host: Intel64 Family 6 Model 170 Stepping 4, Windows build 26200, Python 3.11.9, NumPy 2.4.6. Timing over 10 warmed calls after 3 warm-ups, garbage collection paused during timing:

| Extractor workload | Bound exercised | Median ms | p95 ms | Max ms | < 150 ms |
| --- | --- | ---: | ---: | ---: | :---: |
| spatial_fft | 256x256 RGBA list | 16.37 | 17.40 | 17.40 | yes |
| audio_vocoder@16k | 96,000 samples, 16 kHz | 22.48 | 23.52 | 23.52 | yes |
| audio_vocoder@48k | 96,000 samples, 48 kHz | 22.42 | 23.04 | 23.04 | yes |
| stylometry_drift | 20,000 chars + 20,000-char baseline | 4.35 | 5.91 | 5.91 | yes |
| cross_modal_sync@25 | 1,500 paired samples, 25/s | 0.63 | 1.41 | 1.41 | yes |
| cross_modal_sync@120 | 1,500 paired samples, 120/s | 2.45 | 2.53 | 2.53 | yes |
| homoglyph_hunter | 20,000 adversarial chars + reference | 19.31 | 22.29 | 22.29 | yes |
| perceptual_hash | two 256x256 RGBA lists | 25.58 | 27.61 | 27.61 | yes |
| canary_tripwire.detect | 20,000 chars | 0.02 | 0.03 | 0.03 | yes |
| canary_tripwire.generate | 19,800 chars | 0.03 | 0.04 | 0.04 | yes |
| environmental_acoustic | 96,000-sample measured IR, 16 kHz | 4.66 | 5.12 | 5.12 | yes |
| rppg@25 | 1,500 RGB means, 25/s (60 s) | 0.59 | 0.62 | 0.62 | yes |
| rppg@120 | 1,500 RGB means, 120/s (12.5 s) | 0.57 | 0.60 | 0.60 | yes |

### Proposal Decisions
- **AK-2 (Akarsh)**: **Accepted**. The additive diagnostic metrics (`ambiguousLag`, `alternativeLagMs`, `peakDbfs`) and bounded uncertainty-raising on ambiguous periodic alignments and low-level noise floors are accepted into v1. All v1 schemas, units, and types remain fully backward-compatible.

## Parallel-module refactor validation

Validated on 2026-09-25 after splitting API handlers, relocating owner-specific tests, publishing typed HTTP/forensic contracts and adding independent team checks. The measurements and product results below this section describe the earlier implementation baseline.

- `python scripts/check_module.py all`: 123 Python tests, 11 extension tests, JavaScript syntax and frozen-contract checks passed in the existing environment. After the final typed-response changes, a fresh `.venv` installed from `backend/requirements.txt` with `backend/constraints.txt` passed 122 Python tests with one optional QR-decoding test skipped, plus all 11 extension tests and syntax/contract checks.
- The optional `tests/core/test_api.py::test_pdf_qr_decodes_to_the_verification_endpoint` test passed separately after the final changes in the existing environment, which has PyMuPDF and OpenCV installed. Those optional packages are not required by the runtime setup.
- `python scripts/diagnostics.py` passed all five checks in the fresh environment. `npm ci` installed the locked browser tooling successfully.
- `python scripts/check_module.py dashboard --browser` passed in real Chromium against the final fresh-environment API. All four scenarios rendered the API's vector, evidence, dialectic and playbook correctly; audit gating/PDF verification, canaries, bounded image/audio/video intake and stale-result rejection passed. No browser errors or horizontal overflow were reported at 1440 px desktop and 390 px mobile widths.
- API paths and operation IDs remain stable. Scenario response bytes and existing discovery/canary outputs were checked for parity. Frozen-contract tests reject API/signature/required-metric drift while allowing changed numerical detector measurements. Ownership and architecture checks passed, as did `git diff --check`.

The module backlog is in [the team task board](../team/TASKS.md). This refactor does not complete those separately assigned improvements. Local checks do not establish live social-platform compatibility or empirical detector calibration. GitHub Actions results are recorded by the workflow on the published commit; the results above are local validation.

## Earlier implementation baseline

Validation date: 2026-09-25. CPU: Intel Core Ultra 9 185H. Windows build 26200; Python 3.11.9, NumPy 2.4.6, FastAPI 0.138.2 and Pydantic 2.13.4. No GPU or remote inference service was used.

`python -m pytest tests/ -q`: **102 passed**, including schema compatibility, real extractor measurements, API scenarios (executive wire scam, homoglyph clone, Wi-Fi compression edge case, and creator copyright / canary tripwire), scenario listings, forensic capability introspection, malformed and insufficient inputs, conservative uncertainty, canaries, report signatures and real PDF QR decoding. One dependency deprecation warning concerns Starlette's current HTTPX test transport; no test failed.

`node --test extension/tests/*.test.cjs`: **11 passed**. These validate opt-in collection, exclusion of feed/message/post routes, stale profile detection, bounded avatar sampling and disposal, CORS-incomplete handling, HTTP errors and loopback-only requests. Platform markup is represented by DOM fixtures; live social-site compatibility was not established.

## Bounded CPU extractor measurements

Each measurement below used eight warmed calls. Main-module timings include Python-list conversion. The optional environmental measurements also include construction of synthetic input arrays. These timings describe this host and the tested bounds, not a universal latency guarantee.

| Extractor | Input bound exercised | Median ms | p95 ms | Maximum ms |
| --- | --- | ---: | ---: | ---: |
| Spatial FFT | 256 × 256 RGB list | 16.39 | 19.88 | 20.86 |
| Audio spectral features | 96,000 mono samples | 25.95 | 26.39 | 26.50 |
| Stylometry drift | 20,000 characters plus baseline | 6.45 | 7.13 | 7.18 |
| Cross-modal sync | 1,500 paired samples | 0.96 | 1.09 | 1.09 |
| Unicode confusables | 20,000 adversarial characters | 20.65 | 21.59 | 21.83 |
| Perceptual hash comparison | Two 256 × 256 RGB lists | 24.24 | 33.11 | 36.94 |
| Canary detection | Approximately 20,000 characters | 0.02 | 0.02 | 0.02 |
| Room decay | 96,000 impulse-response samples | — | — | 10.99 |
| Chrominance periodicity | 1,500 RGB means | — | — | 29.16 |

All measured calls were below the 150 ms extractor target. Import/startup time, whole-file browser decoding, HTTP parsing/serialization and PDF generation are separate costs. Run `python -m pytest tests/forensics/test_performance.py tests/forensics/test_environmental.py -s -q` to reproduce the workload on another machine.

## Integrity and evidence checks

- Each scenario passes through the real pipeline; changing the observed handle changes the identity index. The fixtures are generated signals, not a deepfake evaluation dataset.
- At least two actually evaluated modalities are required for complete inspections. Two image items, silent audio, constant pixels and unfetched URLs do not satisfy the rule.
- Copied-avatar pHash matches remain neutral until authorization is established. Both handles and display names receive Unicode lookalike checks.
- Adding duplicate easy signals cannot lower uncertainty from a degraded source. High uncertainty caps every suspicion dimension.
- No raw samples appear in cached verdicts or certificate payloads. Biometric enrollment and persistent embedding storage are not exposed.
- Canary hits require locally registered exact markers; they establish copied marker text, not bot identity or unauthorized use.
- The analyst supplies a decision, notes and each completed verification step. The service does not independently authenticate the analyst's identifier or attest that the reported checks occurred.
- Ed25519 verification covers the canonical assessment and a detached manifest binding payload hash, final PDF hash and session key. Altering the PDF and recomputing its checksum still fails verification. Altered payloads and reported public keys also fail.
- The PDF's QR is rasterized and decoded by OpenCV in the optional integration test, and resolves to the actual local verification endpoint.

## Scope of assurance

The vector's calibration is a transparent heuristic uncertainty bound, not empirical probability calibration. Spectral artifacts, stylistic features and chrominance periodicity cannot prove authenticity, AI generation or biological liveness. RT60 requires a measured room impulse response and does not infer a room from ordinary speech. An absent signal is recorded as unavailable rather than verification.

Certificates and cases are bounded process-local records. They expire after one hour, cache eviction or server restart. A session key seals local records and is not an external identity authority. This build makes no legal compliance certification.

## Live browser result

`scripts/test_dashboard.cjs`: **passed in real headless Chromium against the final local backend**, with zero browser errors and no horizontal overflow at 1440 px desktop or 390 px mobile widths. The test verified exact API-to-UI vector, ledger, dialectic, tripwire and playbook values; blocked missing evidence; enforced audit steps and downloaded a real valid PDF; decoded image pixels, resampled a 22.05 kHz WAV to 16 kHz and extracted one WebM frame; matched a generated canary; verified active tripwire alerting on the creator-copyright scenario; and rejected a stale in-flight assessment after evidence changed.

The measured scenario pipeline times in this browser pass were 15.513 ms (executive request), 39.315 ms (lookalike clone), 2.018 ms (Wi-Fi edge case), and 3.095 ms (creator copyright / canary tripwire). These are the server's extraction/synthesis timings, excluding HTTP overhead and browser decoding. The corresponding uncertainty indices were 0.4562, 0.4688, 0.8000, and 0.4500.

Generated artifacts: [browser report](../../scratch/dashboard-smoke/report.json), [desktop screenshot](../../scratch/dashboard-smoke/dashboard-desktop.png), [mobile screenshot](../../scratch/dashboard-smoke/dashboard-mobile.png). The scratch directory is ignored and these artifacts can be regenerated with the browser smoke script. Reproduction commands are documented in the root README.
