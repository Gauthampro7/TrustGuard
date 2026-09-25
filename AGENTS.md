# TrustGuard workspace protocol

Read docs/team/README.md, the current owner's docs/team/people/<name>.md, and contracts/README.md before editing. The current integration device belongs to **Gautham**. A teammate branch prefix (akarsh/, aril/, achumit/) identifies its work lane.

contracts/ownership.json is the path authority: longest matching path wins; all unspecified paths are Gautham-owned. Akarsh owns detector implementations/tests, Aril the dashboard/tests, Achumit the extension/tests. Gautham owns core/API/schemas/audit, shared ABI, contracts, scenarios, tooling, CI and integration. Each person can edit their brief and own proposal directory. Gautham may integrate across modules when the task calls for it.

Keep public Python imports, /api/v1 paths, units and semantics compatible with contracts/v1/. Teammates must not regenerate snapshots or alter another module to make a feature pass. Record a precise proposal in contracts/proposals/<owner>/<task-id>.md and continue compatible work. Only Gautham adopts shared changes and merges into main.

Run python scripts/check_module.py <module> and python scripts/export_contracts.py --check. Check diffs with python scripts/check_ownership.py --base origin/main and git diff --check. Dashboard acceptance adds --browser against a local API on port 8000. Use separate clones/worktrees for concurrent human work.

Preserve the five-dimensional vector, dual ledger, explicit uncertainty and independent human verification. No scalar establishes authenticity. Do not fetch social endpoints, persist raw biometrics or label synthetic fixtures as real evidence. Missing modalities remain unavailable. Detector changes need controls/abstentions; clients need stale-state and error handling; extension changes preserve opt-in public-profile-only collection.

Keep caches, recordings, credentials and local test artifacts out of Git. Shared dependencies/root configuration belong to Gautham. Preserve unrelated work. README.md and docs/reports/ describe executable scope; historical pitch claims do not override it.
