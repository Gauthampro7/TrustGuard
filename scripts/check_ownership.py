"""Check module boundaries in a branch diff, including local uncommitted work."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8", stderr=subprocess.PIPE).strip()


def path_owner(path, policy):
    normalized = path.replace("\\", "/")
    matches = [rule for rule in policy["rules"] if normalized == rule["path"] or (rule["path"].endswith("/") and normalized.startswith(rule["path"]))]
    return max(matches, key=lambda rule: len(rule["path"]))["owner"] if matches else policy["defaultOwner"]


def branch_owner(branch, policy):
    if branch in {"main", "integration"}:
        return policy["integrationOwner"]
    prefix = branch.split("/", 1)[0].casefold()
    return prefix if prefix in policy["members"] and "/" in branch else None


def changed_paths(base):
    ancestor = git("merge-base", base, "HEAD")
    # --no-renames checks both old and new paths so moves cannot cross boundaries.
    tracked = git("diff", "--name-only", "--no-renames", "-z", ancestor, "--")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z")
    return sorted(set(p for chunk in (tracked, untracked) for p in chunk.split("\0") if p))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="Compare work to this ref's merge base")
    parser.add_argument("--owner", choices=("gautham", "akarsh", "aril", "achumit"), help="Local check override; CI derives owner from branch")
    parser.add_argument("--branch", help="Branch name; useful for detached CI checkout")
    args = parser.parse_args(argv)
    try:
        # Read policy from the integration base, not from a contributor's edits.
        policy_text = git("show", f"{args.base}:contracts/ownership.json")
    except subprocess.CalledProcessError:
        # Bootstrap only: integration owner is checked below before accepting local policy.
        policy_text = (ROOT / "contracts/ownership.json").read_text(encoding="utf-8")
        if (args.owner or branch_owner(args.branch or git("branch", "--show-current"), json.loads(policy_text))) != "gautham":
            print("Ownership policy is absent from base; Gautham must publish the integration baseline first.")
            return 1
    policy = json.loads(policy_text)
    owner = args.owner or branch_owner(args.branch or git("branch", "--show-current"), policy)
    if owner is None:
        print("Use <owner>/<task> branches (akarsh, aril, achumit, gautham). Main belongs to Gautham.")
        return 1
    paths = changed_paths(args.base)
    violations = [(path, path_owner(path, policy)) for path in paths if owner != policy["integrationOwner"] and path_owner(path, policy) != owner]
    for path, assigned in violations:
        print(f"OUTSIDE MODULE: {path} belongs to {policy['members'][assigned]['name']}")
    if violations:
        print("Keep cross-module requests in contracts/proposals/<owner>/; Gautham integrates shared changes.")
        return 1
    print(f"Ownership OK: {policy['members'][owner]['name']}, {len(paths)} changed paths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
