"""Real extraction, API integration and report integrity regressions."""

import base64
from copy import deepcopy
import hashlib
import json

import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core import audit


@pytest.fixture
def client():
    with TestClient(app) as connection:
        yield connection


def scenario(client, name="homoglyph-clone"):
    response = client.get("/api/v1/scenarios/" + name)
    assert response.status_code == 200
    fixture = response.json()
    assert fixture["simulation"] is True
    return fixture["request"]


@pytest.mark.parametrize("name", ["ceo-wire-scam", "homoglyph-clone", "wifi-compression-edge-case", "creator-copyright"])
def test_live_scenarios(client, name):
    response = client.post("/api/v1/inspect", json=scenario(client, name))
    assert response.status_code == 200, response.text
    verdict = response.json()
    assert len(verdict["calibratedTrustVector"]) == 5
    assert len(verdict["innovationMetadata"]["evaluatedModalities"].split(",")) >= 2
    assert verdict["innovationMetadata"]["simulation"] == "true"
    assert verdict["adversarialDialectic"]["judicialSynthesis"]
    assert len(verdict["verificationPlaybook"]) == 3
    assert all(step["status"] == "pending_analyst" for step in verdict["verificationPlaybook"])
    assert "no single score" in verdict["verdictSummary"]["noScoreIsProofNotice"]
    assert verdict["assessmentTier"] not in {"LOW_RISK_VERIFIED", "BENIGN_AUTHENTIC"}
    polarities = {entry["polarity"] for entry in verdict["evidenceLedger"]}
    assert "green_flag" in polarities
    if name != "wifi-compression-edge-case":
        assert "red_flag" in polarities
    if name == "wifi-compression-edge-case":
        vector = verdict["calibratedTrustVector"]
        assert vector["epistemicUncertainty"] >= 0.8
        assert verdict["assessmentTier"] == "UNCERTAIN_COMPRESSION_NOISE"
        assert max(v for k, v in vector.items() if k != "epistemicUncertainty") <= 1.15 - vector["epistemicUncertainty"] + 0.0001
    if name == "creator-copyright":
        assert verdict["tripwireStatus"]["tripwireTriggered"] is True
        assert any("canary" in entry["signalId"] for entry in verdict["evidenceLedger"])
        assert any("perceptual_hash" in entry["signalId"] for entry in verdict["evidenceLedger"])


def test_list_scenarios(client):
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 4
    ids = {s["scenarioId"] for s in scenarios}
    assert ids == {"ceo-wire-scam", "homoglyph-clone", "wifi-compression-edge-case", "creator-copyright"}
    assert all(s["simulation"] is True for s in scenarios)


def test_forensics_capabilities(client):
    response = client.get("/api/v1/forensics/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["latencyTargetMs"] == 150
    assert len(data["extractors"]) == 9
    extractor_ids = {e["id"] for e in data["extractors"]}
    assert "spatial_fft" in extractor_ids
    assert "environmental_acoustic" in extractor_ids
    assert "rppg" in extractor_ids
    assert "canary_tripwire" in extractor_ids


def test_actual_evidence_changes_verdict(client):
    bundle = scenario(client)
    first = client.post("/api/v1/inspect", json=bundle).json()
    bundle["evidenceItems"][1]["metadata"]["extraMetadata"]["observedHandle"] = "rajesh_verma_cfo"
    second = client.post("/api/v1/inspect", json=bundle).json()
    assert first["calibratedTrustVector"]["identityMismatchScore"] > second["calibratedTrustVector"]["identityMismatchScore"]
    assert first["verdictId"] != second["verdictId"]
    reused = next(item for item in first["evidenceLedger"] if "perceptual_hash" in item["signalId"])
    assert reused["polarity"] == "neutral_uncertain"


@pytest.mark.parametrize("replacement", [
    {"evidenceId": "missing", "modality": "video", "mediaUri": "http://127.0.0.1/private.mp4"},
    {"evidenceId": "empty", "modality": "text", "textContent": ""},
    {"evidenceId": "silent", "modality": "audio", "samples": {"audioSamples": [0] * 1600}},
    {"evidenceId": "constant", "modality": "image", "samples": {"imagePixels": [[120] * 16] * 16}},
])
def test_requires_two_measured_modalities(client, replacement):
    bundle = scenario(client)
    bundle["evidenceItems"][0] = replacement
    response = client.post("/api/v1/inspect", json=bundle)
    assert response.status_code == 422
    assert "two evaluated modalities" in response.json()["detail"]


def test_two_images_do_not_fake_multimodality(client):
    bundle = scenario(client)
    duplicate = deepcopy(bundle["evidenceItems"][0])
    duplicate["evidenceId"] = "second-image"
    bundle["evidenceItems"][1] = duplicate
    assert client.post("/api/v1/inspect", json=bundle).status_code == 422


def test_duplicate_easy_signals_cannot_dilute_bad_quality(client):
    bundle = scenario(client, "wifi-compression-edge-case")
    before = client.post("/api/v1/inspect", json=bundle).json()["calibratedTrustVector"]
    for index in range(5):
        repeated = deepcopy(bundle["evidenceItems"][1])
        repeated["evidenceId"] = "repeated-text-" + str(index)
        bundle["evidenceItems"].append(repeated)
    after = client.post("/api/v1/inspect", json=bundle).json()["calibratedTrustVector"]
    assert before["epistemicUncertainty"] == after["epistemicUncertainty"]


@pytest.mark.parametrize("pixels", [[[1] * 16] * 15, [[1] * 17, [1] * 16] * 8, [[256] * 16] * 16])
def test_invalid_pixels_do_not_echo_raw_samples(client, pixels):
    bundle = scenario(client)
    bundle["evidenceItems"][0]["samples"]["imagePixels"] = pixels
    response = client.post("/api/v1/inspect", json=bundle)
    assert response.status_code == 422
    assert all("input" not in entry for entry in response.json()["detail"])


def test_nan_and_duplicate_identifiers_rejected(client):
    bundle = scenario(client)
    bundle["evidenceItems"][1]["evidenceId"] = bundle["evidenceItems"][0]["evidenceId"]
    assert client.post("/api/v1/inspect", json=bundle).status_code == 422
    bundle = scenario(client)
    bundle["evidenceItems"][0]["samples"]["imagePixels"][0][0] = float("nan")
    response = client.post("/api/v1/inspect", content=json.dumps(bundle), headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_profile_advisory_is_not_authentication(client):
    payload = {"platform": "twitter", "handle": "r\u0430jesh_verma_cfo", "displayName": "Rajesh Verma", "referenceHandle": "rajesh_verma_cfo"}
    response = client.post("/api/v1/extension/evaluate-profile", json=payload)
    assert response.status_code == 200, response.text
    verdict = response.json()
    assert verdict["inspectionComplete"] is False
    assert verdict["modalitiesEvaluated"] == ["text"]
    assert verdict["calibratedTrustVector"]["epistemicUncertainty"] >= 0.9
    assert any("U+0430" in signal for signal in verdict["signals"])
    assert verdict["verificationPlaybook"] and verdict["adversarialDialectic"]
    payload["avatarPixels"] = scenario(client)["evidenceItems"][0]["samples"]["imagePixels"]
    full = client.post("/api/v1/extension/evaluate-profile", json=payload).json()
    assert full["inspectionComplete"] is True
    assert set(full["modalitiesEvaluated"]) == {"text", "visual"}
    payload["avatarPixels"] = [[1] * 16] * 16
    assert client.post("/api/v1/extension/evaluate-profile", json=payload).json()["inspectionComplete"] is False


def test_profile_display_name_lookalikes_and_maximum_bio(client):
    payload = {"platform": "twitter", "handle": "alice", "displayName": "Al\u0456ce", "bioText": "a" * 20000}
    response = client.post("/api/v1/extension/evaluate-profile", json=payload)
    assert response.status_code == 200, response.text
    assert any("U+0456" in signal for signal in response.json()["signals"])


def test_registered_canary_only_reports_copied_text(client):
    registration = client.post("/api/v1/canaries", json={"text": "Public canary bio"}).json()
    bundle = scenario(client)
    bundle["evidenceItems"][1]["textContent"] += registration["markedText"]
    verdict = client.post("/api/v1/inspect", json=bundle).json()
    assert verdict["tripwireStatus"]["tripwireTriggered"] is True
    assert "human verification" in verdict["tripwireStatus"]["details"]
    bundle["evidenceItems"][1]["textContent"] = "Public canary bio with no registered marker."
    assert not client.post("/api/v1/inspect", json=bundle).json()["tripwireStatus"]["tripwireTriggered"]


def test_real_pdf_signature_hash_and_tampering(client):
    verdict = client.post("/api/v1/inspect", json=scenario(client)).json()
    body = {"analystId": "reviewer", "analystNotes": "Compared the supplied sources; this synthetic fixture is inconclusive.", "finalDecision": "INCONCLUSIVE", "completedSteps": [1, 2, 3]}
    signed = client.post(f"/api/v1/cases/{verdict['verdictId']}/sign-audit", json=body)
    assert signed.status_code == 200, signed.text
    certificate = signed.json()
    pdf = client.get(certificate["downloadPdfUrl"])
    assert pdf.content.startswith(b"%PDF")
    assert hashlib.sha256(pdf.content).hexdigest() == certificate["certificateSha256"]
    verified = client.get(certificate["verifyUrl"]).json()
    assert verified["valid"] is True
    payload_bytes = audit.canonical(verified["payload"])
    assert hashlib.sha256(payload_bytes).hexdigest() == verified["payloadSha256"]
    Ed25519PublicKey.from_public_bytes(base64.b64decode(verified["publicKey"])).verify(base64.b64decode(verified["signature"]), payload_bytes)
    manifest = {key: verified[key] for key in ("payloadSha256", "certificateSha256", "publicKey")}
    Ed25519PublicKey.from_public_bytes(base64.b64decode(verified["publicKey"])).verify(base64.b64decode(verified["manifestSignature"]), audit.canonical(manifest))
    # Certificate and cached case contain derived features, never submitted pixel/audio arrays.
    assert "imagePixels" not in json.dumps(verified)
    assert "audioSamples" not in json.dumps(verified)
    cached = audit.certificates.get(certificate["auditCertificateId"])
    changed_pdf = deepcopy(cached)
    changed_pdf["pdf"] += b"altered attachment"
    changed_pdf["certificateSha256"] = hashlib.sha256(changed_pdf["pdf"]).hexdigest()
    assert not audit.verify_certificate(changed_pdf)
    changed_key = deepcopy(cached)
    changed_key["publicKey"] = "altered"
    assert not audit.verify_certificate(changed_key)
    cached["payload"]["analystStatement"]["finalDecision"] = "ALTERED"
    assert client.get(certificate["verifyUrl"]).json()["valid"] is False


def test_signing_requires_existing_case_and_completed_human_steps(client):
    body = {"analystId": "reviewer", "analystNotes": "Independent checks recorded.", "finalDecision": "INCONCLUSIVE", "completedSteps": [1]}
    assert client.post("/api/v1/cases/missing/sign-audit", json=body).status_code == 404
    verdict = client.post("/api/v1/inspect", json=scenario(client)).json()
    url = f"/api/v1/cases/{verdict['verdictId']}/sign-audit"
    assert client.post(url, json=body).status_code == 422
    body["completedSteps"] = [1, 2, 3, 3]
    assert client.post(url, json=body).status_code == 422
    body.update(completedSteps=[1, 2, 3], finalDecision="AUTO_CONFIRMED")
    assert client.post(url, json=body).status_code == 422


def test_limits_cors_health_and_dashboard(client):
    assert client.get("/api/v1/health").json()["rawMediaStorage"] is False
    assert client.get("/dashboard/").status_code == 200
    assert client.get("/api/v1/scenarios/unknown").status_code == 404
    assert client.get("/api/v1/certificates/unknown/verify").status_code == 404
    response = client.post("/api/v1/inspect", content=b" " * (8 * 1024 * 1024 + 1), headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    allowed = client.options("/api/v1/inspect", headers={"Origin": "http://127.0.0.1:8000", "Access-Control-Request-Method": "POST"})
    assert allowed.status_code == 200
    denied = client.options("/api/v1/inspect", headers={"Origin": "https://unrelated.example", "Access-Control-Request-Method": "POST"})
    assert denied.status_code == 400


def test_volatile_cache_bounds_and_expiry():
    cache = audit.ExpiringStore(maximum=2)
    for n in range(3):
        cache.put(str(n), n)
    assert cache.get("0") is None
    assert cache.get("2") == 2
    expired = audit.ExpiringStore(ttl=-1)
    expired.put("old", "data")
    assert expired.get("old") is None


def test_room_response_and_rgb_features_are_conditional(client):
    bundle = scenario(client)
    samples = bundle["evidenceItems"][0]["samples"]
    samples["rgbTrace"] = [[100, 100, 100]] * 250
    verdict = client.post("/api/v1/inspect", json=bundle).json()
    assert verdict["environmentalForensics"]["rppgPulseConfidence"] is None
    time = np.arange(16000) / 16000
    impulse = np.exp(-3 * np.log(10) * time / 0.12)
    bundle["evidenceItems"].append({"evidenceId": "room-decay", "modality": "audio", "samples": {"roomImpulseResponse": impulse.tolist()},
        "metadata": {"extraMetadata": {"claimedEnvironment": "airport"}}})
    response = client.post("/api/v1/inspect", json=bundle)
    assert response.status_code == 200, response.text
    assert response.json()["environmentalForensics"]["rt60Sec"] == pytest.approx(0.12, abs=0.01)
    assert response.json()["environmentalForensics"]["reverberationMatchScore"] < 0.5


def test_pdf_qr_decodes_to_the_verification_endpoint(client):
    fitz = pytest.importorskip("fitz")
    cv2 = pytest.importorskip("cv2")
    verdict = client.post("/api/v1/inspect", json=scenario(client)).json()
    body = {"analystId": "qr-reviewer", "analystNotes": "Synthetic fixture used to verify certificate integrity.", "finalDecision": "INCONCLUSIVE", "completedSteps": [1, 2, 3]}
    certificate = client.post(f"/api/v1/cases/{verdict['verdictId']}/sign-audit", json=body).json()
    pdf = client.get(certificate["downloadPdfUrl"]).content
    with fitz.open(stream=pdf, filetype="pdf") as document:
        rendered = document[-1].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixels = np.frombuffer(rendered.samples, dtype=np.uint8).reshape(rendered.height, rendered.width, 3)
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(pixels)
    assert decoded == certificate["verifyUrl"]
