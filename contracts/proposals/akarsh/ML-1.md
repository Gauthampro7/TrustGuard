# ML-1: activate two optional pretrained extractors (AI-generated text and images)

Owner: akarsh
Status: accepted
Current contract: v1
Related module task: new extractors `ai_text_classifier`, `ai_image_classifier` (see `backend/app/forensics/VALIDATION.md`, "ML-1 pretrained extractors")

## Problem and current behavior

PS-02 asks for a multimodal **AI** system, but every current extractor is a hand-written heuristic. In a practicality test with genuinely AI-generated inputs (macOS text-to-speech, SDXL/SDXL-Turbo/FLUX images, LLM-written messages), no existing extractor responded to synthetic media. The earlier practicality check also showed a core aggregation issue: the verdict takes the **maximum uncertainty of every result**, including extractors that abstained (uncertainty 1.0). Any short message therefore turns every bundle into "Inconclusive", including reliable red flags.

Two extractors now exist in the forensics module, fully tested, and abstain cleanly when not installed:

| Extractor | Model (pinned revision) | Licence | Labelled validation (details in VALIDATION.md) | Warm latency, Apple M4 |
| --- | --- | --- | --- | --- |
| `ai_text_classifier.analyze(text)` | `fakespot-ai/roberta-base-ai-text-detection-v1` | Apache-2.0 | Everyday emails/reviews/messages, ≥40 words, decisive outputs (≥0.95): 8/10 AI caught, **0/26** human flagged | 26 ms (90 words), p95 ≤101 ms (512 tokens) |
| `ai_image_classifier.analyze(image_pixels)` | `haywoodsloan/ai-image-detector-deploy` | Apache-2.0 | Colour: 18/18 AI caught, 2/15 real flagged (94%). Grayscale 128 px (current API): 9/18 caught, 0/15 flagged (73%) | median ~161 ms, p95 ≤184 ms |

## Exact protocol change

1. **Core activation (`backend/app/core/inspection.py`).** The exact 23-line diff is in [`ML-1-core.patch`](ML-1-core.patch) (`git apply --check` passes on this branch):
   - Call `ai_image_classifier` for image/video pixels and `ai_text_classifier` for text/document items, both in `mediaSynthesisScore`. The text score is capped at 0.6, so AI-assisted writing alone can reach SUSPICIOUS, never HIGH.
   - Bound each signal by **its own** uncertainty (`min(score, 1.15 − U_signal)` when `U_signal ≥ 0.5`). Previously every dimension was capped by the worst uncertainty in the bundle.
   - Compute overall uncertainty from **evaluated** results only; abstentions no longer count as 1.0.
   - Keep the global cap for channel-level degradation (declared quality loss) and single-modality inputs.
   - Tier: HIGH / SUSPICIOUS when a reliable signal crosses 0.7 / 0.4; otherwise "Inconclusive" when uncertainty ≥ 0.5.
2. **Optional dependency.** `backend/app/forensics/requirements-ml.txt` (torch, transformers, huggingface_hub, pillow) sits on top of `backend/requirements.txt`. Weights are fetched explicitly with `python -m backend.app.forensics.model_store --download` (pinned revisions, about 1.3 GB). Extractors load with `local_files_only`, never touch the network, and abstain without the dependency or with `TRUSTGUARD_ML=0`.
3. **Colour frames (Gautham schema + Aril dashboard, optional follow-up).** `EvidenceSamples.imagePixels` accepts only 2-D grayscale. Validation shows colour lifts image accuracy from 73% to 94%. Proposed: accept `HxWx3` RGB in the same 0–255 range and ≤256×256 bound (the shared `common.grayscale` helper already supports it), and have `frontend/app.js` send RGB.
4. **Latency budget.** `ai_image_classifier` exceeds the 150 ms heuristic target (median ~161 ms). A 224/192 px input, int8 dynamic quantization, bfloat16 and float16 were all slower or less accurate. Proposed: a separate 250 ms p95 budget for pretrained extractors, asserted in `tests/forensics/test_pretrained_models.py`. First use loads both models in about 2.5 s, so warm them at startup (`model_store.load("ai_text")`, `model_store.load("ai_image")`).

## Compatibility and independent progress

No v1 names, types, units or required metrics change; the two extractors are new modules outside the frozen manifest. Without the ML extras everything behaves as today: the extractors abstain, and CI (no torch) still passes 312 tests with the model tests skipped.

With the core patch, all 315 tests pass, including every core, scenario and anti-dilution test. The four demo scenarios keep their tiers. The poor-connection case stays inconclusive through the channel cap. Measured changes on realistic bundles (grayscale via the current API):

| Bundle | Current core | With patch |
| --- | --- | --- |
| SDXL-Turbo image + AI-written email | Inconclusive | **Suspicious** (AI-text red flag) |
| SDXL image + AI-written job scam | Inconclusive | **Suspicious** |
| Real photo + human Enron email | Inconclusive | Inconclusive (not flagged) |
| Real photo + human Amazon review | Inconclusive | Inconclusive (not flagged) |
| Real photo + human Yelp review | Inconclusive | Suspicious (known text-model false alarm, capped below HIGH) |
| Cyrillic lookalike handle vs reference | High | High |
| Short CEO wire-scam SMS + TTS voice | Inconclusive | Inconclusive (separate: `stylometry_drift` short-text uncertainty) |

If only the extractors are wanted without the aggregation change, drop the three aggregation hunks of the patch. Their scores are then capped by the worst uncertainty, as today.

## Acceptance

- `python -m pytest tests/ -q` with and without `requirements-ml.txt` installed (315 passed / 312 passed + 4 skipped on the tested host).
- `python -m pytest tests/forensics/test_pretrained_models.py -s -q`: abstention without models, input bounds, direction checks, text p95 < 150 ms, image p95 < 250 ms.
- `python scripts/export_contracts.py --check`, `python scripts/check_module.py all --browser`.
- Privacy: samples stay in memory; models run locally; no remote inference.

## Integration record — Gautham fills on acceptance

- **Decision**: Formally accepted. The two pretrained extractors (`ai_text_classifier`, `ai_image_classifier`) and the core activation patch (`ML-1-core.patch`) are accepted into main. Signal-bounded uncertainty and evaluated-only aggregation resolve the bundle-wide dilution issue while preserving strict epistemic caps, and a 250 ms p95 budget is adopted for pretrained image inference.
- **Contract Version**: v1 (backward-compatible; 0 drift against v1 schemas and frozen extractor ABI).
- **Integration Commit**: `0ca521b` (merge of Akarsh's forensics commit `3ee8cd5`) and `990fac5` (core activation in `backend/app/core/inspection.py`).
- **Migration Notes**: Optional dependencies in `backend/app/forensics/requirements-ml.txt`. Weights fetched explicitly via `python -m backend.app.forensics.model_store --download` (pinned revisions, offline-only with `local_files_only=True`). Clean abstention maintained without weights or when `TRUSTGUARD_ML=0`.
- **Validation**: 347 tests passed (5 skipped without model weights), 47 extension tests passed, full diagnostics suite (5/5) passed, and browser smoke suite (12/12) passed with 0 contract drift.
- **Follow-up Tasks**:
  1. Colour frames: Gautham schema update to `EvidenceSamples.imagePixels` accepting `HxWx3` RGB, and Aril dashboard update to send RGB frames (improves image classification accuracy from 73% to 94%).
  2. Pre-warming: Wire `model_store.load()` into FastAPI startup when `TRUSTGUARD_ML=1` to absorb the ~2.5s cold start.
  3. Model weights caching in deployment/container pipeline.
