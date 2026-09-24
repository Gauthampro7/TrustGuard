# TrustGuard implementation validation

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

All measured calls were below the 150 ms extractor target. Import/startup time, whole-file browser decoding, HTTP parsing/serialization and PDF generation are separate costs. Run `python -m pytest tests/test_performance.py tests/test_environmental.py -s -q` to reproduce the workload on another machine.

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
