"""Ownership boundaries include shared exceptions and both sides of file moves."""

import json
from pathlib import Path

from scripts.check_ownership import branch_owner, path_owner

POLICY = json.loads((Path(__file__).resolve().parents[2] / "contracts/ownership.json").read_text(encoding="utf-8"))


def test_owned_modules_and_frozen_exceptions():
    examples = {"backend/app/forensics/spatial_fft.py": "akarsh", "tests/forensics/new_case.py": "akarsh",
                "backend/app/forensics/common.py": "gautham", "backend/app/forensics/AGENTS.md": "gautham",
                "backend/app/core/inspection.py": "gautham", "contracts/v1/openapi.json": "gautham",
                "frontend/app.js": "aril", "frontend/tests/browser-smoke.cjs": "aril",
                "extension/content.js": "achumit", "docs/new-shared-note.md": "gautham"}
    for path, owner in examples.items():
        assert path_owner(path, POLICY) == owner
    assert path_owner("frontend-other/file.js", POLICY) == "gautham"


def test_async_proposals_do_not_grant_shared_write_ownership():
    assert path_owner("contracts/proposals/aril/TG-UI-01.md", POLICY) == "aril"
    assert path_owner("contracts/proposals/achumit/TG-EXT-01.md", POLICY) == "achumit"
    assert path_owner("contracts/proposals/akarsh/TG-FOR-01.md", POLICY) == "akarsh"
    assert path_owner("contracts/ownership.json", POLICY) == "gautham"


def test_unambiguous_branch_owner_and_unknown_branch_rejection():
    for name in ("aril", "akarsh", "achumit", "gautham"):
        assert branch_owner(f"{name}/task-1", POLICY) == name
    assert branch_owner("main", POLICY) == "gautham"
    assert branch_owner("feature/mixed-changes", POLICY) is None
    assert branch_owner("aril-unscoped", POLICY) is None
