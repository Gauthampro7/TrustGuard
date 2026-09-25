"""Export the v1 boundary coordinated by Gautham; --check never rewrites fixtures.

The default/--write mode records API and extractor contracts and creates synthetic
reference examples. Scores in those examples are illustrative frozen outputs,
not probability truth or numerical regression targets for extractor owners.
"""

from __future__ import annotations

import argparse
from dataclasses import MISSING, asdict, fields
import importlib
import inspect
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, get_type_hints

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.forensics.common import ForensicResult
from backend.app.models.schemas import (
    ProfileEvaluationRequest, ProfileEvaluationResponse,
    TrustGuardInspectionRequest, TrustGuardInspectionVerdict,
)

PROTOCOL_VERSION = "1.0.0"
CONTRACT_DIR = ROOT / "contracts" / "v1"
FROZEN_TIMESTAMP = "2026-09-24T00:00:00+00:00"
SCENARIOS = ("ceo-wire-scam", "creator-copyright", "homoglyph-clone", "wifi-compression-edge-case")
PROFILE_EXAMPLES = ("profile-text-only", "profile-multimodal")
MODULE_FUNCTIONS = {
    "spatial_fft": ("analyze",),
    "audio_vocoder": ("analyze",),
    "stylometry_drift": ("analyze",),
    "cross_modal_sync": ("analyze",),
    "homoglyph_hunter": ("analyze", "skeleton"),
    "perceptual_hash": ("analyze", "hash_image", "hamming_distance"),
    "canary_tripwire": ("generate", "detect"),
    "environmental_acoustic": ("analyze",),
    "rppg": ("analyze",),
}
# This list is intentionally maintained with core/inspection.py's consumers.
# All analyze results must include evaluated; the other keys are conditional on
# evaluated=true. New diagnostic metrics may be added without breaking v1.
REQUIRED_METRICS = {
    "spatial_fft": {"highFrequencyPowerRatio": "number", "spectralPeakRatio": "number"},
    "audio_vocoder": {"phaseDiscontinuityRate": "number", "briefDigitalSilenceGaps": "integer"},
    "stylometry_drift": {"yulesK": "number", "urgencyScore": "number"},
    "cross_modal_sync": {"lagMs": "number", "correlation": "number"},
    "homoglyph_hunter": {"confusables": "array<{codePoint:string,looksLike:string}>"},
    "perceptual_hash": {"matched": "boolean", "hammingDistance": "integer"},
    "environmental_acoustic": {"rt60Sec": "number", "matchScore": "number|null", "profile": "string"},
    "rppg": {"pulseRegularity": "number", "pulseFrequencyHz": "number"},
}
HELPER_RETURNS = {
    "generate": {"text": "string", "token": "string", "marker": "string", "tokenId": "string", "warning": "string"},
    "detect": {"tripwireTriggered": "boolean", "tokenId": "string", "occurrenceCount": "integer", "explanation": "string"},
    "hash_image": "16-character hexadecimal string",
    "hamming_distance": "integer in [0,64]",
    "skeleton": "string",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def read_json(path: Path) -> Any:
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def forensic_module(name):
    return importlib.import_module(f"backend.app.forensics.{name}")


def annotation_name(annotation):
    if annotation is inspect.Signature.empty:
        return None
    if isinstance(annotation, type):
        return annotation.__qualname__ if annotation.__module__ == "builtins" else f"{annotation.__module__}.{annotation.__qualname__}"
    return str(annotation).replace("typing.", "")


def build_forensics_manifest():
    field_types = get_type_hints(ForensicResult)
    result_fields = []
    for field in fields(ForensicResult):
        entry = {"name": field.name, "type": annotation_name(field_types[field.name]),
                 "required": field.default is MISSING and field.default_factory is MISSING}
        if field.default is not MISSING:
            entry["default"] = field.default
        if field.default_factory is not MISSING:
            entry["defaultFactory"] = annotation_name(field.default_factory)
        result_fields.append(entry)
    modules = {}
    for module_name, function_names in MODULE_FUNCTIONS.items():
        functions = {}
        for name in function_names:
            signature = inspect.signature(getattr(forensic_module(module_name), name))
            parameters = []
            for parameter in signature.parameters.values():
                value = {"name": parameter.name, "kind": parameter.kind.name,
                         "required": parameter.default is inspect.Parameter.empty,
                         "annotation": annotation_name(parameter.annotation)}
                if parameter.default is not inspect.Parameter.empty:
                    value["default"] = parameter.default
                parameters.append(value)
            functions[name] = {"signature": str(signature), "parameters": parameters,
                               "returnAnnotation": annotation_name(signature.return_annotation),
                               "returns": "ForensicResult" if name == "analyze" else HELPER_RETURNS[name]}
        modules[module_name] = {"importPath": f"backend.app.forensics.{module_name}", "functions": functions}
        if "analyze" in function_names:
            modules[module_name]["metrics"] = {
                "alwaysRequired": {"evaluated": "boolean"},
                "requiredWhenEvaluated": REQUIRED_METRICS[module_name],
                "additionalMetricsAllowed": True,
            }
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "ForensicResult": {"frozen": ForensicResult.__dataclass_params__.frozen, "fields": result_fields},
        "semantics": {
            "score": "Finite anomaly index in [0,1]; never an authenticity probability or proof.",
            "uncertainty": "Finite evidence limitation index in [0,1]; larger means less reliable evidence.",
            "findings": "Human-readable statements; wording and numeric measurements may evolve without an ABI break.",
            "metrics.evaluated": "Mandatory boolean on every analyze output. False means abstention and cannot count as an evaluated modality.",
            "elapsed_ms": "Finite nonnegative extractor duration; runtime values are not frozen regression targets.",
            "inputOwnership": "Callers supply bounded in-memory samples. No external fetching or raw biometric persistence.",
            "compatibility": "Freeze callable signatures, ordered dataclass fields and consumed metric keys; permit implementation and score changes.",
            "requiredMetricsMaintenance": "Manual core-consumer list in scripts/export_contracts.py; coordinate changes with Gautham.",
        },
        "modules": modules,
    }


def current_contracts():
    from backend.app.main import app
    app.openapi_schema = None
    return {"openapi.json": app.openapi(), "forensics.json": build_forensics_manifest()}


def validate_forensic_result(name, measured):
    if not isinstance(measured, ForensicResult):
        raise ValueError(f"{name}.analyze must return ForensicResult")
    canonical_json(asdict(measured))
    if measured.name != name or not isinstance(measured.findings, list) or not all(isinstance(item, str) for item in measured.findings):
        raise ValueError(f"{name}: invalid result name or findings")
    if not 0 <= measured.score <= 1 or not 0 <= measured.uncertainty <= 1 or measured.elapsed_ms < 0:
        raise ValueError(f"{name}: invalid scalar bounds")
    if type(measured.metrics.get("evaluated")) is not bool:
        raise ValueError(f"{name}: mandatory metrics.evaluated boolean is missing")
    if measured.metrics["evaluated"]:
        for key, kind in REQUIRED_METRICS[name].items():
            if key not in measured.metrics:
                raise ValueError(f"{name}: required metric {key} is missing")
            value = measured.metrics[key]
            valid = ((kind == "number|null" and value is None) or
                     (kind in {"number", "number|null"} and type(value) in {int, float} and math.isfinite(value)) or
                     (kind == "integer" and type(value) is int) or
                     (kind == "boolean" and type(value) is bool) or
                     (kind == "string" and isinstance(value, str)) or
                     (kind.startswith("array<") and isinstance(value, list) and all(
                         isinstance(item, dict) and isinstance(item.get("codePoint"), str) and isinstance(item.get("looksLike"), str)
                         for item in value)))
            if not valid:
                raise ValueError(f"{name}: metric {key} must have type {kind}")


def validate_live_abi():
    """Exercise successful/abstaining return shapes without snapshotting scores."""
    import numpy as np
    image = np.fromfunction(lambda y, x: (13 * x + 7 * y) % 256, (64, 64))
    t = np.arange(16000) / 16000
    impulse = np.exp(-3 * np.log(10) * t / .55) * np.cos(2 * np.pi * 1337 * t)
    trace_t = np.arange(300) / 25
    rgb = np.column_stack([np.full(300, 145.0), 105 + np.sin(2 * np.pi * 1.2 * trace_t), np.full(300, 80.0)])
    envelope = 1 + np.sin(np.arange(100) * .23)
    calls = {
        "spatial_fft": [(image,), (np.ones((64, 64)),)],
        "audio_vocoder": [(.5 * np.sin(2 * np.pi * 220 * t),), (np.zeros(16000),)],
        "stylometry_drift": [("This synthetic contract text discusses careful independent verification. " * 20,), ("",)],
        "cross_modal_sync": [(envelope, envelope), (np.zeros(100), np.zeros(100))],
        "homoglyph_hunter": [("rаjesh", "rajesh"), ("",)],
        "perceptual_hash": [(image, image), (image,)],
        "environmental_acoustic": [(impulse, 16000, "office"), (np.zeros(16000),)],
        "rppg": [(rgb,), (np.ones((300, 3)),)],
    }
    for name, inputs in calls.items():
        for arguments in inputs:
            validate_forensic_result(name, forensic_module(name).analyze(*arguments))
    canary = forensic_module("canary_tripwire")
    generated = canary.generate("Synthetic contract marker.", "contract_example_token_v1")
    detected = canary.detect(generated["text"], generated["token"])
    for name, output in (("generate", generated), ("detect", detected)):
        canonical_json(output)
        for key, kind in HELPER_RETURNS[name].items():
            value = output.get(key)
            expected = {"string": str, "boolean": bool, "integer": int}[kind]
            if type(value) is not expected:
                raise ValueError(f"canary_tripwire.{name}: missing or invalid {key}")
    image_hash = forensic_module("perceptual_hash").hash_image(image)
    distance = forensic_module("perceptual_hash").hamming_distance(image_hash, image_hash)
    if not isinstance(image_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{16}", image_hash):
        raise ValueError("perceptual_hash.hash_image must return a 16-character hexadecimal string")
    if type(distance) is not int or not 0 <= distance <= 64:
        raise ValueError("perceptual_hash.hamming_distance must return an integer in [0,64]")
    if not isinstance(forensic_module("homoglyph_hunter").skeleton("contract"), str):
        raise ValueError("homoglyph_hunter.skeleton must return a string")


def normalize_verdict(verdict, scenario_id):
    data = verdict.model_dump(mode="json")
    data["verdictId"] = f"ver_contract_v1_{scenario_id}"
    data["evaluatedAt"] = FROZEN_TIMESTAMP
    metadata = data["innovationMetadata"]
    metadata["elapsedMs"] = "0.000"
    metadata["extractorTimingsMs"] = json.dumps({key: 0.0 for key in sorted(json.loads(metadata["extractorTimingsMs"]))}, sort_keys=True)
    metadata["contractExample"] = "Frozen synthetic reference; not probability truth or a numeric regression target."
    return data


def build_examples():
    from backend.app.api.endpoints.profiles import evaluate_profile
    from backend.app.core.inspection import inspect as inspect_evidence
    examples = {}
    for scenario_id in SCENARIOS:
        scenario = read_json(ROOT / "backend" / "app" / "scenarios" / f"{scenario_id}.json")
        request = TrustGuardInspectionRequest.model_validate(scenario["request"])
        request.requestId = f"req_contract_v1_{scenario_id}"
        request.timestamp = FROZEN_TIMESTAMP
        verdict = inspect_evidence(request, registered_tokens=("creator_canary_token_2026",))
        examples[f"{scenario_id}.request.json"] = request.model_dump(mode="json", exclude_none=True)
        examples[f"{scenario_id}.verdict.json"] = normalize_verdict(verdict, scenario_id)
    for name in PROFILE_EXAMPLES:
        payload = {"platform": "twitter", "handle": "contract_example", "displayName": "Synthetic Contract Example",
                   "bioText": "Synthetic reference profile for protocol tests. No real person is represented. Verify identity through an independent known channel."}
        if name == "profile-multimodal":
            payload["avatarPixels"] = [[(13 * x + 7 * y) % 256 for x in range(64)] for y in range(64)]
        request = ProfileEvaluationRequest.model_validate(payload)
        examples[f"{name}.request.json"] = request.model_dump(mode="json", exclude_none=True)
        examples[f"{name}.response.json"] = evaluate_profile(request).model_dump(mode="json")
    examples["index.json"] = {
        "protocolVersion": PROTOCOL_VERSION, "synthetic": True,
        "notice": "All samples are synthetic demonstrations. Frozen scores are not authenticity probabilities, truth labels, or numeric regression targets.",
        "normalization": "Stable request/verdict IDs and evaluatedAt; elapsedMs and extractorTimingsMs zeroed. No raw real-world biometrics.",
        "scenarios": list(SCENARIOS), "profiles": list(PROFILE_EXAMPLES),
        "files": sorted(examples),
    }
    return examples


def validate_examples(contract_dir=CONTRACT_DIR):
    folder = Path(contract_dir) / "examples"
    index = read_json(folder / "index.json")
    if index.get("protocolVersion") != PROTOCOL_VERSION or index.get("synthetic") is not True:
        raise ValueError("Examples must identify their protocol version and synthetic origin")
    expected = {f"{name}.{suffix}.json" for name in SCENARIOS for suffix in ("request", "verdict")}
    expected |= {f"{name}.{suffix}.json" for name in PROFILE_EXAMPLES for suffix in ("request", "response")}
    if set(index.get("files", [])) != expected or {p.name for p in folder.glob("*.json")} != expected | {"index.json"}:
        raise ValueError("The frozen example file set differs from the v1 manifest")
    for filename in sorted(expected | {"index.json"}):
        canonical_json(read_json(folder / filename))
    for scenario_id in SCENARIOS:
        request = TrustGuardInspectionRequest.model_validate(read_json(folder / f"{scenario_id}.request.json"))
        verdict = TrustGuardInspectionVerdict.model_validate(read_json(folder / f"{scenario_id}.verdict.json"))
        if request.requestId != verdict.requestId:
            raise ValueError(f"{scenario_id}: request/verdict IDs do not match")
        supplied_modalities = set()
        for item in request.evidenceItems:
            if item.textContent and item.textContent.strip() and item.modality.value in {"text", "document"}:
                supplied_modalities.add("text")
            if item.samples:
                if item.samples.imagePixels is not None or item.samples.rgbTrace is not None:
                    supplied_modalities.add("visual")
                if item.samples.audioSamples is not None or item.samples.roomImpulseResponse is not None:
                    supplied_modalities.add("audio")
        if len(supplied_modalities) < 2:
            raise ValueError(f"{scenario_id}: request must supply at least two distinct modalities")
        metadata = verdict.innovationMetadata or {}
        modalities = set(filter(None, metadata.get("evaluatedModalities", "").split(",")))
        if len(modalities) < 2 or not modalities <= {"audio", "visual", "text"} or metadata.get("simulation") != "true":
            raise ValueError(f"{scenario_id}: a synthetic multimodal verdict is required")
        if not modalities <= supplied_modalities:
            raise ValueError(f"{scenario_id}: verdict claims a modality absent from its request")
        if not verdict.evidenceLedger or not verdict.verificationPlaybook or not verdict.adversarialDialectic:
            raise ValueError(f"{scenario_id}: vector, evidence, dialectic and human verification are required")
    for name in PROFILE_EXAMPLES:
        request = ProfileEvaluationRequest.model_validate(read_json(folder / f"{name}.request.json"))
        response = ProfileEvaluationResponse.model_validate(read_json(folder / f"{name}.response.json"))
        complete = name == "profile-multimodal"
        if response.inspectionComplete != complete or (request.avatarPixels is not None) != complete:
            raise ValueError(f"{name}: inconsistent modality completeness")
        if set(response.modalitiesEvaluated) != ({"visual", "text"} if complete else {"text"}):
            raise ValueError(f"{name}: incorrect evaluated modalities")
        if not response.calibratedTrustVector or not response.evidenceLedger or not response.verificationPlaybook or not response.adversarialDialectic:
            raise ValueError(f"{name}: partial advisory still requires the complete explanation contract")
        if not response.noScoreIsProofNotice or response.badgeStatus == "meter-green":
            raise ValueError(f"{name}: fixtures must not claim verified authenticity")


def check_contracts(contract_dir=CONTRACT_DIR):
    errors = []
    try:
        current = current_contracts()
        for filename, content in current.items():
            path = Path(contract_dir) / filename
            if not path.exists() or path.read_text(encoding="utf-8") != canonical_json(content):
                errors.append(f"Contract drift: {path}. Coordinate protocol changes with Gautham; do not silently regenerate v1.")
    except (AttributeError, TypeError, ValueError) as error:
        errors.append(f"Cannot inspect the current contract: {error}")
    try:
        validate_live_abi()
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        errors.append(f"Extractor ABI violation: {error}")
    try:
        validate_examples(contract_dir)
    except (OSError, TypeError, ValueError) as error:
        errors.append(f"Frozen example validation failed: {error}")
    return errors


def write_contracts(contract_dir=CONTRACT_DIR):
    folder = Path(contract_dir)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "examples").mkdir(exist_ok=True)
    for filename, content in current_contracts().items():
        (folder / filename).write_text(canonical_json(content), encoding="utf-8", newline="\n")
    for filename, content in build_examples().items():
        (folder / "examples" / filename).write_text(canonical_json(content), encoding="utf-8", newline="\n")
    validate_examples(folder)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="read-only API/ABI drift and frozen-fixture validation")
    modes.add_argument("--write", action="store_true", help="write coordinated Gautham contract updates (default)")
    args = parser.parse_args(argv)
    if args.check:
        errors = check_contracts()
        for message in errors:
            print(message, file=sys.stderr)
        if errors:
            return 1
        print("v1 API, extractor ABI and synthetic frozen examples are valid; numeric outputs were not compared.")
    else:
        write_contracts()
        print(f"Exported coordinated v1 contracts and synthetic examples to {CONTRACT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
