# Forensics — Akarsh

This directory and tests/forensics/ contain Akarsh's implementations/tests. common.py and this instruction file are Gautham-owned. Read docs/team/people/akarsh.md and contracts/v1/forensics.json.

Preserve signatures, required metrics, units, finite JSON, input bounds and abstention. score is an anomaly index; uncertainty describes measurement usability. Do not import API/core code, call remote services, retain samples or decide human verification outcomes. Additive diagnostic metrics are allowed; shared changes need an owned proposal.

Run python scripts/check_module.py forensics. Preserve the <150 ms warmed bounded-input target without weakening uncertainty. Notes go here, test controls in tests/forensics/, and shared requests in contracts/proposals/akarsh/.
