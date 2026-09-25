"""Versioned API/ABI drift checks and reusable synthetic reference examples."""

from dataclasses import replace
import json
import shutil

import pytest

from scripts import export_contracts as contracts


def copied_contracts(tmp_path):
    destination = tmp_path / "v1"
    shutil.copytree(contracts.CONTRACT_DIR, destination)
    return destination


def test_frozen_api_abi_and_example_contracts_match():
    assert contracts.check_contracts() == []


def test_stale_openapi_is_reported(tmp_path):
    folder = copied_contracts(tmp_path)
    path = folder / "openapi.json"
    document = contracts.read_json(path)
    document["paths"]["/api/v1/inspect"]["post"]["operationId"] = "changed_operation_id"
    path.write_text(contracts.canonical_json(document), encoding="utf-8")
    assert any("Contract drift:" in message and "openapi.json" in message for message in contracts.check_contracts(folder))


def test_changed_extractor_signature_is_reported(monkeypatch):
    module = contracts.forensic_module("spatial_fft")
    original = module.analyze

    def analyze(image_pixels, added_parameter=None):
        return original(image_pixels)

    monkeypatch.setattr(module, "analyze", analyze)
    assert any("Contract drift:" in message and "forensics.json" in message for message in contracts.check_contracts())


def test_stale_ordered_result_fields_are_reported(tmp_path):
    folder = copied_contracts(tmp_path)
    path = folder / "forensics.json"
    document = contracts.read_json(path)
    document["ForensicResult"]["fields"].reverse()
    path.write_text(contracts.canonical_json(document), encoding="utf-8")
    assert any("Contract drift:" in message and "forensics.json" in message for message in contracts.check_contracts(folder))


@pytest.mark.parametrize("missing_metric", ["evaluated", "highFrequencyPowerRatio"])
def test_missing_required_extractor_metric_is_rejected(monkeypatch, missing_metric):
    module = contracts.forensic_module("spatial_fft")
    original = module.analyze

    def analyze(image_pixels):
        measured = original(image_pixels)
        metrics = dict(measured.metrics)
        metrics.pop(missing_metric, None)
        return replace(measured, metrics=metrics)

    monkeypatch.setattr(module, "analyze", analyze)
    assert any("Extractor ABI violation:" in message and missing_metric in message for message in contracts.check_contracts())


def test_numeric_extractor_changes_do_not_regenerate_or_invalidate_frozen_examples(monkeypatch):
    module = contracts.forensic_module("spatial_fft")
    original = module.analyze

    def analyze(image_pixels):
        measured = original(image_pixels)
        return replace(measured, score=min(1.0, measured.score + .1))

    def forbidden_regeneration():
        raise AssertionError("--check must not regenerate live verdict fixtures")

    monkeypatch.setattr(module, "analyze", analyze)
    monkeypatch.setattr(contracts, "build_examples", forbidden_regeneration)
    assert contracts.check_contracts() == []


def test_every_reference_example_is_valid_finite_json_and_explicitly_synthetic():
    contracts.validate_examples()
    index = contracts.read_json(contracts.CONTRACT_DIR / "examples" / "index.json")
    assert index["synthetic"] is True
    assert len(index["files"]) == 12
    for filename in index["files"]:
        document = contracts.read_json(contracts.CONTRACT_DIR / "examples" / filename)
        json.dumps(document, allow_nan=False)
        if filename.endswith(".verdict.json"):
            assert document["evaluatedAt"] == contracts.FROZEN_TIMESTAMP
            assert document["verdictId"].startswith("ver_contract_v1_")
            metadata = document["innovationMetadata"]
            assert metadata["elapsedMs"] == "0.000"
            assert set(json.loads(metadata["extractorTimingsMs"]).values()) <= {0.0}
            assert "not probability truth" in metadata["contractExample"]


def test_fixture_cannot_claim_multimodality_without_supplied_media(tmp_path):
    folder = copied_contracts(tmp_path)
    path = folder / "examples" / "homoglyph-clone.request.json"
    request = contracts.read_json(path)
    request["evidenceItems"] = [item for item in request["evidenceItems"] if item["modality"] == "text"]
    path.write_text(contracts.canonical_json(request), encoding="utf-8")
    with pytest.raises(ValueError, match="two distinct modalities"):
        contracts.validate_examples(folder)


def test_missing_and_malformed_example_files_fail_check(tmp_path):
    folder = copied_contracts(tmp_path)
    path = folder / "examples" / "profile-text-only.response.json"
    response = contracts.read_json(path)
    response["inspectionComplete"] = True
    path.write_text(contracts.canonical_json(response), encoding="utf-8")
    assert any("inconsistent modality completeness" in message for message in contracts.check_contracts(folder))
    path.unlink()
    assert any("example file set" in message for message in contracts.check_contracts(folder))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), b"raw bytes"])
def test_json_contracts_reject_nonfinite_values_and_raw_bytes(value):
    with pytest.raises((TypeError, ValueError)):
        contracts.canonical_json({"value": value})


def test_check_cli_reports_drift_without_writing(monkeypatch, capsys):
    monkeypatch.setattr(contracts, "check_contracts", lambda: ["Contract drift: test ABI"])
    assert contracts.main(["--check"]) == 1
    assert "Contract drift" in capsys.readouterr().err
