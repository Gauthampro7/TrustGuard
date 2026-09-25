"""GA-2: Integration tests closing core validation gaps.

Covers:
1. Chunked body limits (streaming generator bodies, 413 handling, valid chunked streams).
2. Concurrent and repeated audit requests (thread safety, multiple certificates per case, distinct decisions).
3. Cache expiry and LRU eviction (ExpiringStore bounds, cases eviction, certificate eviction, TTL expiry).
4. Failed canary registration (empty, missing, oversized, non-string, malformed, deque eviction).
5. Dependency failures and error resilience (PDF generator failure, internal errors, array corruption).
6. Privacy & integrity (no raw media samples echoed in errors or stored in certificates).
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core import audit
from backend.app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as connection:
        yield connection


def get_scenario(client, name="homoglyph-clone"):
    response = client.get(f"/api/v1/scenarios/{name}")
    assert response.status_code == 200
    return response.json()["request"]


# ===========================================================================
# 1. Chunked Body Limits
# ===========================================================================

def test_chunked_body_exceeding_limit_returns_413(client):
    """Streaming body chunks exceeding 8 MiB must return 413 before materializing."""
    def stream_over_limit():
        total = 0
        limit = 8 * 1024 * 1024 + 1024
        while total < limit:
            chunk = b"x" * min(65536, limit - total)
            total += len(chunk)
            yield chunk

    response = client.post(
        "/api/v1/inspect",
        content=stream_over_limit(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Request exceeds the 8 MiB transient sample limit"


def test_chunked_body_within_limit_succeeds(client):
    """A valid inspection payload streamed in small chunks must be received and evaluated."""
    bundle = get_scenario(client)
    raw_json = json.dumps(bundle).encode("utf-8")

    def stream_valid_payload():
        for i in range(0, len(raw_json), 512):
            yield raw_json[i:i + 512]

    response = client.post(
        "/api/v1/inspect",
        content=stream_valid_payload(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    verdict = response.json()
    assert verdict["verdictId"].startswith("ver_")
    assert len(verdict["calibratedTrustVector"]) == 5


def test_chunked_body_limits_apply_to_all_post_endpoints(client):
    """Oversized chunked bodies on any mutation endpoint return 413."""
    def stream_too_large():
        for _ in range(130):
            yield b"a" * 65536

    canary_resp = client.post(
        "/api/v1/canaries",
        content=stream_too_large(),
        headers={"Content-Type": "application/json"},
    )
    assert canary_resp.status_code == 413

    audit_resp = client.post(
        "/api/v1/cases/any-case-id/sign-audit",
        content=stream_too_large(),
        headers={"Content-Type": "application/json"},
    )
    assert audit_resp.status_code == 413


# ===========================================================================
# 2. Concurrent and Repeated Audit Requests
# ===========================================================================

def test_concurrent_audit_signing_same_case(client):
    """Multiple concurrent analysts can sign the same case safely without corruption."""
    bundle = get_scenario(client)
    verdict = client.post("/api/v1/inspect", json=bundle).json()
    case_id = verdict["verdictId"]

    def sign_case(idx):
        body = {
            "analystId": f"analyst_{idx}",
            "analystNotes": f"Concurrent verification note {idx} with substantive detail.",
            "finalDecision": "INCONCLUSIVE",
            "completedSteps": [1, 2, 3],
        }
        res = client.post(f"/api/v1/cases/{case_id}/sign-audit", json=body)
        return res.status_code, res.json()

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(sign_case, range(8)))

    # All sign requests succeed
    assert all(status == 200 for status, _ in results)
    cert_ids = [data["auditCertificateId"] for _, data in results]
    # Each signing creates a unique certificate
    assert len(set(cert_ids)) == len(cert_ids)

    # Concurrently verify all generated certificates
    def verify_cert(cert_data):
        verify_url = cert_data["verifyUrl"]
        res = client.get(verify_url)
        return res.status_code, res.json()

    with ThreadPoolExecutor(max_workers=5) as executor:
        verify_results = list(executor.map(verify_cert, [data for _, data in results]))

    assert all(status == 200 for status, _ in verify_results)
    assert all(v["valid"] is True for _, v in verify_results)


def test_concurrent_signing_different_cases(client):
    """Concurrently inspecting and signing distinct cases preserves independent isolation."""
    def inspect_and_sign(idx):
        bundle = get_scenario(client)
        bundle["requestId"] = f"concurrent_req_{idx}"
        v = client.post("/api/v1/inspect", json=bundle).json()
        body = {
            "analystId": f"analyst_diff_{idx}",
            "analystNotes": f"Notes for case {idx} with sufficient length.",
            "finalDecision": "INCONCLUSIVE",
            "completedSteps": [1, 2, 3],
        }
        s = client.post(f"/api/v1/cases/{v['verdictId']}/sign-audit", json=body)
        return s.status_code, s.json(), v["verdictId"]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(inspect_and_sign, range(4)))

    assert all(status == 200 for status, _, _ in results)
    case_ids = {case_id for _, _, case_id in results}
    assert len(case_ids) == 4


def test_repeated_signing_same_case_different_decisions(client):
    """Repeatedly signing a case with different conclusions yields distinct valid certificates."""
    bundle = get_scenario(client)
    verdict = client.post("/api/v1/inspect", json=bundle).json()
    case_id = verdict["verdictId"]

    decisions = ["INCONCLUSIVE", "FRAUD_CONFIRMED", "AUTHENTIC_CONFIRMED"]
    certificates = []
    for decision in decisions:
        body = {
            "analystId": "lead_reviewer",
            "analystNotes": f"Decision updated to {decision} based on new evidence.",
            "finalDecision": decision,
            "completedSteps": [1, 2, 3],
        }
        resp = client.post(f"/api/v1/cases/{case_id}/sign-audit", json=body)
        assert resp.status_code == 200
        certificates.append(resp.json())

    assert len(certificates) == 3
    # Check that each certificate reflects its respective decision
    for cert, expected_decision in zip(certificates, decisions):
        verified = client.get(cert["verifyUrl"]).json()
        assert verified["valid"] is True
        assert verified["payload"]["analystStatement"]["finalDecision"] == expected_decision


def test_repeated_signing_with_validation_failures_leaves_case_intact(client):
    """Validation errors on sign-audit do not corrupt or remove the underlying case."""
    bundle = get_scenario(client)
    verdict = client.post("/api/v1/inspect", json=bundle).json()
    case_id = verdict["verdictId"]

    # Incomplete steps -> 422
    assert client.post(f"/api/v1/cases/{case_id}/sign-audit", json={
        "analystId": "analyst", "analystNotes": "Adequate notes here.", "finalDecision": "INCONCLUSIVE", "completedSteps": [1],
    }).status_code == 422

    # Duplicate steps -> 422
    assert client.post(f"/api/v1/cases/{case_id}/sign-audit", json={
        "analystId": "analyst", "analystNotes": "Adequate notes here.", "finalDecision": "INCONCLUSIVE", "completedSteps": [1, 2, 2],
    }).status_code == 422

    # Notes too short -> 422
    assert client.post(f"/api/v1/cases/{case_id}/sign-audit", json={
        "analystId": "analyst", "analystNotes": "short", "finalDecision": "INCONCLUSIVE", "completedSteps": [1, 2, 3],
    }).status_code == 422

    # Valid sign still succeeds
    valid_resp = client.post(f"/api/v1/cases/{case_id}/sign-audit", json={
        "analystId": "analyst", "analystNotes": "Adequate and detailed notes for signing.", "finalDecision": "INCONCLUSIVE", "completedSteps": [1, 2, 3],
    })
    assert valid_resp.status_code == 200


# ===========================================================================
# 3. Cache Expiry and Eviction
# ===========================================================================

def test_expiring_store_lru_recency():
    """ExpiringStore moves accessed keys to the end to maintain true LRU eviction."""
    store = audit.ExpiringStore(maximum=3, ttl=3600)
    store.put("a", 1)
    store.put("b", 2)
    store.put("c", 3)

    # Access 'a' so 'b' becomes least recently used
    assert store.get("a") == 1

    # Insert 'd'; 'b' should be evicted, 'a', 'c', 'd' remain
    store.put("d", 4)
    assert store.get("b") is None
    assert store.get("a") == 1
    assert store.get("c") == 3
    assert store.get("d") == 4


def test_cases_eviction_when_exceeding_capacity(client):
    """When audit.cases exceeds maximum capacity, oldest cases are evicted and return 404."""
    small_store = audit.ExpiringStore(maximum=2, ttl=3600)
    with patch.object(audit, "cases", small_store):
        # Inspect 3 times
        b1 = get_scenario(client)
        b1["requestId"] = "req_evict_1"
        v1 = client.post("/api/v1/inspect", json=b1).json()

        b2 = get_scenario(client)
        b2["requestId"] = "req_evict_2"
        v2 = client.post("/api/v1/inspect", json=b2).json()

        b3 = get_scenario(client)
        b3["requestId"] = "req_evict_3"
        v3 = client.post("/api/v1/inspect", json=b3).json()

        # v1 should have been evicted
        sign_body = {
            "analystId": "reviewer",
            "analystNotes": "Independent checks recorded.",
            "finalDecision": "INCONCLUSIVE",
            "completedSteps": [1, 2, 3],
        }
        res1 = client.post(f"/api/v1/cases/{v1['verdictId']}/sign-audit", json=sign_body)
        assert res1.status_code == 404
        assert "expired" in res1.json()["detail"].lower()

        # v2 and v3 are still present
        res2 = client.post(f"/api/v1/cases/{v2['verdictId']}/sign-audit", json=sign_body)
        assert res2.status_code == 200


def test_certificates_eviction_when_exceeding_capacity(client):
    """When audit.certificates exceeds maximum capacity, oldest certificate returns 404."""
    small_certs = audit.ExpiringStore(maximum=2, ttl=3600)
    with patch.object(audit, "certificates", small_certs):
        bundle = get_scenario(client)
        v = client.post("/api/v1/inspect", json=bundle).json()
        case_id = v["verdictId"]

        sign_body = {
            "analystId": "reviewer",
            "analystNotes": "Independent checks recorded.",
            "finalDecision": "INCONCLUSIVE",
            "completedSteps": [1, 2, 3],
        }
        c1 = client.post(f"/api/v1/cases/{case_id}/sign-audit", json=sign_body).json()
        c2 = client.post(f"/api/v1/cases/{case_id}/sign-audit", json=sign_body).json()
        c3 = client.post(f"/api/v1/cases/{case_id}/sign-audit", json=sign_body).json()

        # c1 should be evicted
        assert client.get(c1["verifyUrl"]).status_code == 404
        assert client.get(c1["downloadPdfUrl"]).status_code == 404

        # c2 and c3 are still accessible
        assert client.get(c2["verifyUrl"]).status_code == 200
        assert client.get(c3["verifyUrl"]).status_code == 200


def test_ttl_expiry_causes_404_on_signing_and_verification(client):
    """Expired cases and certificates return 404."""
    # Test case expired
    expired_cases = audit.ExpiringStore(maximum=10, ttl=-1)
    with patch.object(audit, "cases", expired_cases):
        bundle = get_scenario(client)
        v = client.post("/api/v1/inspect", json=bundle).json()
        sign_body = {
            "analystId": "reviewer",
            "analystNotes": "Independent checks recorded.",
            "finalDecision": "INCONCLUSIVE",
            "completedSteps": [1, 2, 3],
        }
        assert client.post(f"/api/v1/cases/{v['verdictId']}/sign-audit", json=sign_body).status_code == 404

    # Test certificate expired
    expired_certs = audit.ExpiringStore(maximum=10, ttl=-1)
    with patch.object(audit, "certificates", expired_certs):
        bundle = get_scenario(client)
        v = client.post("/api/v1/inspect", json=bundle).json()
        sign_body = {
            "analystId": "reviewer",
            "analystNotes": "Independent checks recorded.",
            "finalDecision": "INCONCLUSIVE",
            "completedSteps": [1, 2, 3],
        }
        c = client.post(f"/api/v1/cases/{v['verdictId']}/sign-audit", json=sign_body).json()
        assert client.get(c["verifyUrl"]).status_code == 404
        assert client.get(c["downloadPdfUrl"]).status_code == 404


# ===========================================================================
# 4. Failed Canary Registration
# ===========================================================================

@pytest.mark.parametrize("payload", [
    {"text": ""},
    {},
    {"wrongKey": "some text"},
    {"text": None},
    {"text": 12345},
    {"text": ["text in list"]},
    {"text": {"nested": "dict"}},
    {"text": "a" * 2001},
])
def test_failed_canary_registration_invalid_inputs(client, payload):
    """All invalid canary registration payloads must return 422 with structured details."""
    response = client.post("/api/v1/canaries", json=payload)
    assert response.status_code == 422
    details = response.json()["detail"]
    assert isinstance(details, list)
    for issue in details:
        assert "loc" in issue
        assert "msg" in issue
        assert "type" in issue
        assert "input" not in issue


def test_failed_canary_registration_malformed_json(client):
    """Malformed JSON bytes in canary request return 422 cleanly."""
    response = client.post(
        "/api/v1/canaries",
        content=b"{malformed json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"


def test_canary_capacity_and_deque_eviction(client):
    """The canary registry bounds session tokens to 100; old tokens are evicted."""
    from backend.app.api.dependencies import _registered_canaries

    first_reg = client.post("/api/v1/canaries", json={"text": "Original canary item"}).json()
    first_token = first_reg["token"]
    assert first_token in _registered_canaries

    # Register 105 more canaries to trigger deque maxlen eviction
    for i in range(105):
        client.post("/api/v1/canaries", json={"text": f"Canary batch item {i}"})

    assert first_token not in _registered_canaries

    # An inspection using the evicted marker should NOT trigger tripwire
    bundle = get_scenario(client)
    bundle["evidenceItems"][1]["textContent"] += first_reg["markedText"]
    verdict = client.post("/api/v1/inspect", json=bundle).json()
    assert verdict["tripwireStatus"]["tripwireTriggered"] is False


# ===========================================================================
# 5. Dependency Failures & Error Handling
# ===========================================================================

def test_pdf_generation_dependency_failure_handled_gracefully(client):
    """When PDF generation fails, sign-audit returns 500 without leaking sensitive state."""
    bundle = get_scenario(client)
    verdict = client.post("/api/v1/inspect", json=bundle).json()
    case_id = verdict["verdictId"]

    body = {
        "analystId": "analyst",
        "analystNotes": "Detailed independent verification notes.",
        "finalDecision": "INCONCLUSIVE",
        "completedSteps": [1, 2, 3],
    }

    with patch("backend.app.core.audit.SimpleDocTemplate.build", side_effect=RuntimeError("ReportLab engine fault")):
        resp = client.post(f"/api/v1/cases/{case_id}/sign-audit", json=body)
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Certificate generation failed"


def test_extractor_dependency_failure_handled_gracefully(client):
    """Unexpected extractor crash returns 500 without leaking raw data or stack trace."""
    bundle = get_scenario(client)
    with patch("backend.app.forensics.spatial_fft.analyze", side_effect=RuntimeError("FFT computation failure")):
        resp = client.post("/api/v1/inspect", json=bundle)
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Inspection failed due to an internal processing error"


@pytest.mark.parametrize("corrupted_sample", [
    {"imagePixels": [["not_a_number"] * 16] * 16},
    {"imagePixels": [[float("inf")] * 16] * 16},
    {"imagePixels": [[float("-inf")] * 16] * 16},
    {"audioSamples": ["not_a_number"] * 1600},
    {"audioSamples": [float("inf")] * 1600},
    {"roomImpulseResponse": ["not_a_number"] * 1024},
    {"audioEnvelope": ["nan_val"] * 25, "mouthAperture": [0.5] * 25},
])
def test_corrupted_numeric_arrays_rejected(client, corrupted_sample):
    """Corrupted numeric inputs are rejected at schema validation with 422."""
    bundle = get_scenario(client)
    bundle["evidenceItems"][0]["samples"].update(corrupted_sample)
    response = client.post(
        "/api/v1/inspect",
        content=json.dumps(bundle),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    for issue in response.json()["detail"]:
        assert "input" not in issue


def test_mismatched_traces_rejected(client):
    """Mismatched audioEnvelope and mouthAperture lengths fail validation."""
    bundle = get_scenario(client)
    samples = bundle["evidenceItems"][0]["samples"]
    samples["audioEnvelope"] = [0.5] * 30
    samples["mouthAperture"] = [0.5] * 25
    response = client.post("/api/v1/inspect", json=bundle)
    assert response.status_code == 422
    assert any("equal lengths" in issue["msg"] for issue in response.json()["detail"])


def test_audio_duration_too_short_rejected(client):
    """Audio samples shorter than 0.1s at sampleRate return 422."""
    bundle = get_scenario(client, "ceo-wire-scam")
    audio_item = next(item for item in bundle["evidenceItems"] if item["modality"] == "audio")
    # Declared sampleRate is 16000, 0.1s is 1600 samples. Set length to 800 (valid in schema, fails in inspect).
    audio_item["samples"]["audioSamples"] = [0.0] * 800
    response = client.post("/api/v1/inspect", json=bundle)
    assert response.status_code == 422
    assert "at least 0.1 seconds" in response.json()["detail"]


# ===========================================================================
# 6. Privacy & Integrity: No Raw Sample Leaks
# ===========================================================================

def test_profile_evaluation_validation_errors_do_not_leak_pixels(client):
    """Non-rectangular avatarPixels fail with 422 and omit raw inputs."""
    bad_avatar = [[100] * 16] * 15 + [[100] * 15]  # Non-rectangular
    payload = {
        "platform": "twitter",
        "handle": "test_handle",
        "displayName": "Test Name",
        "avatarPixels": bad_avatar,
    }
    response = client.post("/api/v1/extension/evaluate-profile", json=payload)
    assert response.status_code == 422
    for issue in response.json()["detail"]:
        assert "input" not in issue
        assert "100" not in issue["msg"]


def test_certificate_and_verify_payloads_contain_no_raw_samples(client):
    """Signed incident certificates and verify responses never retain raw samples."""
    bundle = get_scenario(client, "ceo-wire-scam")
    verdict = client.post("/api/v1/inspect", json=bundle).json()
    case_id = verdict["verdictId"]

    body = {
        "analystId": "lead_forensic_analyst",
        "analystNotes": "Thorough inspection of synthetic voice and visual data complete.",
        "finalDecision": "INCONCLUSIVE",
        "completedSteps": [1, 2, 3],
    }
    cert = client.post(f"/api/v1/cases/{case_id}/sign-audit", json=body).json()
    verify_resp = client.get(cert["verifyUrl"]).json()

    serialized = json.dumps(verify_resp)
    for forbidden in ("imagePixels", "audioSamples", "roomImpulseResponse", "rgbTrace", "referenceImagePixels"):
        assert forbidden not in serialized, f"Raw sample field '{forbidden}' found in verified certificate!"
