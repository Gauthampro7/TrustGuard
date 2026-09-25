"""Keep independent modules from acquiring dependencies on their consumers."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_extractors_do_not_depend_on_api_or_trust_synthesis():
    forbidden = ("backend.app.api", "backend.app.core", "backend.app.models", "fastapi", "httpx", "requests", "urllib")
    for source in (ROOT / "backend/app/forensics").glob("*.py"):
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [name.name for name in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= 1, f"{source.name} must not import outside its forensic package"
                names = [node.module or ""]
            else:
                continue
            assert not any(name == prefix or name.startswith(prefix + ".") for name in names for prefix in forbidden), f"{source.name} imports an API, synthesis or networking dependency"


def test_core_has_no_dependency_on_endpoint_modules():
    for source in (ROOT / "backend/app/core").glob("*.py"):
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("api", "backend.app.api")), f"{source.name} imports an endpoint"


def test_router_composer_contains_no_request_handlers():
    source = (ROOT / "backend/app/api/routes.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in tree.body)
    assert "include_router" in source
