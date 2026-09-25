# Shared protocols — owner: Gautham

These files let each module evolve without depending on another teammate's unpublished changes.

| File | Meaning |
| --- | --- |
| `ownership.json` | Exact path ownership and branch lanes; longest matching path wins |
| `v1/openapi.json` | Generated snapshot of the current HTTP API, including Pydantic request/response schemas and operation IDs |
| `v1/forensics.json` | Public extractor signatures, ordered `ForensicResult` fields and required consumed metrics |
| `v1/examples/` | Synthetic request/verdict and profile request/response fixtures; no real biometric recordings |
| `proposals/<owner>/` | Each teammate's independent shared-interface requests |

`backend/app/models/schemas.py` remains the runtime schema authority. `backend/app/forensics/common.py` remains the shared forensic result/validation implementation. Both are Gautham-owned. Snapshot checks detect uncoordinated drift; they do not replace validation of heuristic accuracy or legal compliance.

## Forensic protocol

Functions process bounded in-memory inputs synchronously and return a finite, JSON-compatible `ForensicResult`. The `name` is stable; `score` is an anomaly index, `uncertainty` describes measurement usability, `findings` explain the measurement and limitations, `metrics.evaluated` explicitly reports whether a usable measurement exists, and `elapsed_ms` measures local computation. An absent signal must abstain, never authenticate. Canary generation/detection and pHash helper functions retain their separate dictionary/scalar interfaces listed in the manifest.

Units must not drift: pixels are 0–255 or explicitly supported normalized arrays; PCM is normalized; audio rates are Hz; synchronized trace rates are samples/second; returned delay is milliseconds; RT60 is seconds; chrominance periodicity is Hz and is never a biological-liveness probability. Consult the actual per-function bounds in the frozen manifest and Pydantic samples contract.

The core owns dimension aggregation, uncertainty caps, assessment tiers, human verification and persistence decisions. Extractors must not import API/core modules, call remote inference endpoints or write biometric samples. A new extractor may be developed in Akarsh's module without affecting current behavior; activation in the core is Gautham's integration task.

## HTTP protocol

The API origin is local, `http://127.0.0.1:8000`; its versioned prefix is `/api/v1`. Requests use JSON and the existing camelCase field names. Only complete inspections evaluate at least two actual modalities. Profile responses may be explicitly incomplete. No caller should infer authenticity from a low index or a missing dimension. Clients render all five indices, evidence, uncertainty and verification steps together.

The current request body limit is 8 MiB. Sample arrays must match their declared modality. The API never downloads media URLs. `innovationMetadata` values are strings, including serialized timing maps; do not silently reinterpret their type. Audit completion is a self-declared human statement, not a verified identity credential. Verification returns signed payload and detached PDF manifest data, not a proof that the incident is true.

Errors use a non-2xx HTTP status and a `detail` field: usually a string, or a list of `{loc, msg, type}` validation issues. `404` includes missing/expired cases and certificates; `413` is the body limit; `422` includes malformed samples, insufficient modalities and incomplete audit steps. Do not render an error payload as a verdict. Browser unreachability/CORS errors must leave an unavailable state, and stale responses must be discarded after evidence/navigation changes.

Discovery, canary registration, scenario details and certificate verification have typed response models in `backend/app/models/api_responses.py`. The shared error schema covers both string details and structured validation issues. PDF responses are documented as binary `application/pdf`. Scenario JSON preserves original sample numbers and omitted fields after validation. These published types are shared contracts, not teammate-editable implementation details.

## Changing a shared protocol

1. Add a proposal in your own directory using `proposals/TEMPLATE.md`. Never modify `v1/`, shared schema files or another module to make your feature pass.
2. Gautham evaluates consumer compatibility. Additive optional fields/metrics may stay in v1; removed/renamed fields, changed units, required inputs, semantic reversals or endpoint removals require an explicit migration/version decision.
3. Gautham updates runtime schemas and consumer tests together, runs `python scripts/export_contracts.py --write`, reviews the generated diff and executes `python scripts/check_module.py all --browser` against the integrated backend.
4. Publish the accepted baseline. Teammates update their branch from `main` and consume the accepted interface. Until then, continue against v1 or work on another assigned task.

Everyone runs `python scripts/export_contracts.py --check`; only Gautham regenerates snapshots. The checker deliberately validates example shape and required semantics without requiring future extractor improvements to reproduce the old heuristic numbers. This is a compatibility test, not numerical training data.
