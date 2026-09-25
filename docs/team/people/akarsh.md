# Akarsh — forensic engines

Work in your own clone on `akarsh/forensics`. Your deliverable is a stronger, measured detector library that Gautham can merge without adapting the API. The nine local measurements already work: spatial FFT, audio spectrum, stylometry, timing correlation, Unicode lookalikes, pHash, canaries, conditional room decay and ROI chrominance. Improve their limits and regression coverage; do not rebuild them.

## Your boundary

You may edit `backend/app/forensics/**` **except** `backend/app/forensics/common.py` and `backend/app/forensics/AGENTS.md`, plus `tests/forensics/**`, `contracts/proposals/akarsh/**` and your own brief `docs/team/people/akarsh.md`. Keep module-specific notes in `backend/app/forensics/VALIDATION.md` and synthetic fixtures under `tests/forensics/fixtures/`.

Do not edit `backend/app/forensics/common.py`, `backend/app/forensics/AGENTS.md`, `backend/app/models/**`, `backend/app/core/**`, `backend/app/api/**`, `backend/app/scenarios/**`, `backend/app/main.py`, `backend/requirements.txt`, `backend/constraints.txt`, `frontend/**`, `extension/**`, `tests/core/**`, `tests/contracts/**`, `contracts/v1/**`, other people's proposal directories, `scripts/**`, `.github/**`, root files or `docs/**` except your personal brief. All paths outside your allowlist belong to another owner. Reading them and running their tests is encouraged.

## Start locally

From the repository root, after checking out the shared team baseline:

```powershell
git switch -c akarsh/forensics
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -c backend/constraints.txt
.\.venv\Scripts\python.exe -m pytest tests/forensics/ -q
.\.venv\Scripts\python.exe -m pytest tests/contracts/ -q
.\.venv\Scripts\python.exe scripts/check_module.py forensics
```

Use `git switch akarsh/forensics` when the branch already exists. You do not need a running server, a GPU, a paid API or model downloads for detector development.

## Frozen interface

Read `contracts/v1/` and the current functions before editing. Import the existing `ForensicResult` from `backend.app.forensics.common`; do not create a competing result class. Keep exported function names, parameter defaults, result names, established metric keys, value types and units compatible with v1. `score` is an anomaly index in `[0,1]`; `uncertainty` is also in `[0,1]`; `metrics.evaluated=False` means the extractor abstained. Findings and metrics must serialize with `json.dumps(..., allow_nan=False)`.

The synchrony convention is positive `lagMs` when mouth motion trails audio. pHash identifies coarse asset reuse, not face identity. RT60 requires a caller-supplied measured room impulse response. rPPG accepts caller-supplied ROI RGB means, not a video file, and cannot establish biological liveness. Canary functions return their existing dictionaries rather than `ForensicResult`.

Keep extraction bounds at 256×256 image pixels, 96,000 audio/impulse samples, 1,500 trace samples and 20,000 text characters. API samples have their own stricter representation constraints; do not change these in a detector PR. No imports from the API, frontend or extension; no network access or persistence from an extractor.

If an improvement needs a new required/shared field, shared-helper change or dependency, write `contracts/proposals/akarsh/<topic>.md` with the current behavior, proposed signature/schema, sample input/output, affected consumers and migration test. Additive diagnostic metrics are allowed when existing required keys, types and semantics remain intact. Continue compatible work while Gautham reviews proposals. Do not regenerate v1 snapshots yourself.

## Next work, in order

1. **AK-1: build a reproducible perturbation bench.** Add seeded benign and perturbed synthetic controls for all nine modules, emphasizing resampling/quantization, phase changes versus valid gating, text scarcity, lag sign, multilingual names, authorized avatar reuse, tail noise and shared RGB illumination. Record observed distributions and abstentions in your module validation note. Avoid claims of deepfake accuracy: these controls are not a labeled real-world corpus.
2. **AK-2: harden demonstrated corner cases.** Investigate Unicode combining marks and word boundaries, near-constant numeric inputs, input scaling, periodic signals with ambiguous lag peaks and noisy RT60 tails. Fix only reproduced issues; give each fix a failing regression first. Preserve the ordinary Cyrillic/Greek/Indic and separate-language-name negative controls. If a change alters a v1 metric's meaning or uncertainty policy, use the proposal route.
3. **AK-3: publish laptop measurements.** Run warmed maximum-size workloads on your machine; report Python/NumPy versions, CPU, median, p95 and maximum. Separate imports and fixture construction from extractor timing where applicable. Optimize only the measured bottlenecks, keeping uncertainty and abstention intact.

Do AK-1 before tuning thresholds. AK-2 and AK-3 form one bounded follow-up PR each. New model integrations, biometrics, additional modalities and full Unicode conformance are deferred unless separately accepted through a contract proposal.

## Acceptance and delivery

```powershell
.\.venv\Scripts\python.exe -m pytest tests/forensics/ -q
.\.venv\Scripts\python.exe -m pytest tests/forensics/test_performance.py tests/forensics/test_environmental.py -s -q
.\.venv\Scripts\python.exe -m pytest tests/contracts/ -q
.\.venv\Scripts\python.exe scripts/export_contracts.py --check
.\.venv\Scripts\python.exe scripts/check_ownership.py --owner akarsh --base origin/main
git diff --check
git diff --name-only
```

All detector/contract tests must pass. `contracts/ownership.json` is the machine-readable boundary source. If the integration baseline has not been pushed, use `--base main` in the ownership check instead of `origin/main`; otherwise fetch the current approved remote baseline before checking. Report every measured extractor's maximum alongside the existing p95 assertion; the target is under 150 ms at the documented input bounds on the tested laptop. If a run exceeds the target, disclose the workload and host instead of weakening the limit or hiding samples. Silence, constant images, unstable chrominance and unsuitable impulse responses must still abstain. Findings must retain plausible benign explanations.

Deliver a focused PR to Gautham containing only owned paths, new regressions, a short explanation of changed behavior, measured timings and `backend/app/forensics/VALIDATION.md`. Include any proposal links and the exact commands/results. Gautham runs the complete API and UI integration suite before merging.
