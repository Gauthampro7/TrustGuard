"""One entry point for each owner's checks; browser checks use a running local API."""

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def commands_for(module, browser=False):
    commands = [[sys.executable, "scripts/export_contracts.py", "--check"]]
    if module == "all":
        commands.append([sys.executable, "-m", "pytest", "tests/"])
    elif module == "core":
        commands.append([sys.executable, "-m", "pytest", "tests/core/", "tests/contracts/"])
    elif module == "forensics":
        commands.append([sys.executable, "-m", "pytest", "tests/forensics/", "tests/contracts/test_frozen_protocol.py", "tests/contracts/test_architecture.py"])
    if module in {"dashboard", "all"}:
        for script in ("frontend/app.js", "frontend/tests/browser-smoke.cjs", "scripts/test_dashboard.cjs"):
            commands.append(["node", "--check", script])
    if module in {"extension", "all"}:
        for script in sorted((ROOT / "extension").rglob("*.js")):
            commands.append(["node", "--check", script.relative_to(ROOT).as_posix()])
        commands.append(["node", "--test", *[p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "extension/tests").glob("*.test.cjs"))]])
    if browser:
        if module not in {"dashboard", "all"}:
            raise ValueError("--browser applies to dashboard or all; start the local API on port 8000 first")
        commands.append(["node", "frontend/tests/browser-smoke.cjs"])
    return commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", choices=("core", "forensics", "dashboard", "extension", "all"))
    parser.add_argument("--browser", action="store_true", help="Requires npm ci and the local API running on port 8000")
    args = parser.parse_args()
    try:
        commands = commands_for(args.module, args.browser)
    except ValueError as error:
        parser.error(str(error))
    for command in commands:
        print("CHECK:", " ".join(command), flush=True)
        try:
            completed = subprocess.run(command, cwd=ROOT, check=False)
        except FileNotFoundError as error:
            print(f"Missing prerequisite: {error.filename}. Follow docs/team/README.md.")
            return 1
        if completed.returncode:
            return completed.returncode
    print(f"{args.module}: all selected checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
