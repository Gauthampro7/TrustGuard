"""Local evidence inspection API. No external fetching or raw biometric persistence."""

import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from ..core import audit
from ..core.config import settings
from ..core.inspection import inspect, InsufficientModalities, DIMENSIONS
from ..forensics import canary_tripwire
from ..models.schemas import (
    TrustGuardInspectionRequest, TrustGuardInspectionVerdict,
    ProfileEvaluationRequest, ProfileEvaluationResponse, AuditSignRequest, AuditCertificateResponse,
    ScenarioSummary,
)

api_router = APIRouter()
_registered_canaries = deque(["creator_canary_token_2026"], maxlen=100)
SCENARIO_IDS = {"ceo-wire-scam", "homoglyph-clone", "wifi-compression-edge-case", "creator-copyright"}


@api_router.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "TrustGuard Core API", "standard": "v1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(), "rawMediaStorage": False,
            "calibration": "heuristic, not probability calibrated", "sessionPublicKey": audit.PUBLIC_KEY}


def run_inspection(request, *, require_multimodal=True):
    try:
        return inspect(request, require_multimodal=require_multimodal, registered_tokens=tuple(_registered_canaries))
    except (InsufficientModalities, ValueError) as error:
        raise HTTPException(422, str(error)) from error


@api_router.post("/inspect", response_model=TrustGuardInspectionVerdict, tags=["Inspection"])
def inspect_evidence(request: TrustGuardInspectionRequest):
    verdict = run_inspection(request)
    audit.cases.put(verdict.verdictId, verdict)
    return verdict


@api_router.post("/extension/evaluate-profile", response_model=ProfileEvaluationResponse, tags=["Browser Extension"])
def evaluate_profile(request: ProfileEvaluationRequest):
    evidence = [{"evidenceId": "profile-text", "modality": "text",
                 "textContent": (request.bioText or "").strip() or f"{request.displayName}\n@{request.handle}",
                 "metadata": {"extraMetadata": {"observedHandle": request.handle, "observedDisplayName": request.displayName}}}]
    if request.avatarPixels is not None:
        evidence.append({"evidenceId": "profile-avatar", "modality": "image", "samples": {"imagePixels": request.avatarPixels}})
    bundle = TrustGuardInspectionRequest.model_validate({
        "requestId": "profile_" + uuid4().hex, "timestamp": datetime.now(timezone.utc).isoformat(),
        "sourceChannel": "browser_extension", "evidenceItems": evidence,
        "claimedIdentity": {"referenceHandles": {"x_twitter": request.referenceHandle}}})
    verdict = run_inspection(bundle, require_multimodal=False)
    complete = len(verdict.innovationMetadata["evaluatedModalities"].split(",")) >= 2
    vector = verdict.calibratedTrustVector
    risk = max(getattr(vector, key) for key in DIMENSIONS)
    consistency = min(1 - risk, 1 - vector.epistemicUncertainty)
    red = any(entry.polarity.value == "red_flag" for entry in verdict.evidenceLedger)
    label = "INCOMPLETE_MULTIMODAL_INSPECTION" if not complete else ("REVIEW_LOOKALIKE_SIGNALS" if red else "UNVERIFIED_PROFILE")
    return ProfileEvaluationResponse(continuousAuthenticityScore=round(max(0, consistency), 4),
        badgeStatus="meter-amber" if not complete or not red else "meter-red", label=label,
        signals=[entry.finding for entry in verdict.evidenceLedger], calibratedTrustVector=vector,
        evidenceLedger=verdict.evidenceLedger, verificationPlaybook=verdict.verificationPlaybook,
        adversarialDialectic=verdict.adversarialDialectic,
        modalitiesEvaluated=verdict.innovationMetadata["evaluatedModalities"].split(","), inspectionComplete=complete)


@api_router.get("/scenarios", response_model=List[ScenarioSummary], tags=["Scenarios"])
def list_scenarios():
    items = []
    scenarios_dir = Path(__file__).resolve().parents[1] / "scenarios"
    for scenario_id in sorted(SCENARIO_IDS):
        path = scenarios_dir / f"{scenario_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(ScenarioSummary(
                scenarioId=data.get("scenarioId", scenario_id),
                title=data.get("title", scenario_id),
                description=data.get("description", ""),
                simulation=data.get("simulation", True),
            ))
    return items


@api_router.get("/scenarios/{scenario_id}", tags=["Scenarios"])
def get_scenario(scenario_id: str):
    if scenario_id not in SCENARIO_IDS:
        raise HTTPException(404, "Unknown scenario")
    path = Path(__file__).resolve().parents[1] / "scenarios" / f"{scenario_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@api_router.get("/forensics/capabilities", tags=["System"])
def forensic_capabilities():
    return {
        "engine": "TrustGuard CPU Multimodal Forensic Engine",
        "latencyTargetMs": 150,
        "gpuRequired": False,
        "extractors": [
            {"id": "spatial_fft", "modality": "visual", "description": "2D Fourier azimuthal harmonics, high-frequency energy ratio, roll-off, and checkerboard artifact detection"},
            {"id": "audio_vocoder", "modality": "audio", "description": "STFT phase discontinuity rates, mel-band transitions, and digital silence detection"},
            {"id": "stylometry_drift", "modality": "text", "description": "Function word frequencies, Yule's K vocabulary richness, and urgency/wire-pressure indicators"},
            {"id": "cross_modal_sync", "modality": "audio+visual", "description": "Audio energy envelope vs mouth aperture cross-correlation and lag estimation"},
            {"id": "homoglyph_hunter", "modality": "text", "description": "Unicode TR39 confusable lookalike character detection and cross-script spoofing analysis"},
            {"id": "perceptual_hash", "modality": "visual", "description": "DCT 64-bit perceptual hashing for asset and avatar reuse tracking"},
            {"id": "canary_tripwire", "modality": "text", "description": "Zero-width steganographic honeypot token generator and detector"},
            {"id": "environmental_acoustic", "modality": "audio+context", "description": "Schroeder T20/RT60 room impulse response decay and acoustic profile matching"},
            {"id": "rppg", "modality": "visual", "description": "Facial ROI chrominance periodicity and cardiac micro-flush frequency estimation"}
        ],
        "activeRegisteredCanaries": len(_registered_canaries),
        "calibration": "Heuristic uncertainty bounds; caps suspicion at min(raw, 1.15 - U) when U >= 0.50"
    }


class CanaryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@api_router.post("/canaries", tags=["Canary"])
def register_canary(request: CanaryRequest):
    result = canary_tripwire.generate(request.text)
    _registered_canaries.append(result["token"])
    return {"markedText": result["text"], "token": result["token"],
            "notice": "Registered for this server session. A match indicates copied text, not a bot or unauthorized use. Platforms may strip invisible markers."}


@api_router.post("/cases/{case_id}/sign-audit", response_model=AuditCertificateResponse, tags=["Human Verification"])
def sign_audit(case_id: str, request: AuditSignRequest):
    verdict = audit.cases.get(case_id)
    if verdict is None:
        raise HTTPException(404, "Case not found or expired; run an inspection first")
    if request.finalDecision not in {"FRAUD_CONFIRMED", "AUTHENTIC_CONFIRMED", "INCONCLUSIVE"}:
        raise HTTPException(422, "Select FRAUD_CONFIRMED, AUTHENTIC_CONFIRMED or INCONCLUSIVE")
    required_steps = {step.step for step in verdict.verificationPlaybook}
    if set(request.completedSteps) != required_steps or len(request.completedSteps) != len(required_steps):
        raise HTTPException(422, "Complete each independent verification step exactly once before signing")
    if not request.analystId.strip() or len(request.analystNotes.strip()) < 10:
        raise HTTPException(422, "An analyst ID and substantive verification notes are required")
    certificate_id, entry = audit.create_certificate(verdict, request, settings.PUBLIC_BASE_URL)
    return AuditCertificateResponse(auditCertificateId=certificate_id, timestamp=entry["timestamp"],
        certificateSha256=entry["certificateSha256"], downloadPdfUrl=f"/api/v1/certificates/{certificate_id}.pdf", verifyUrl=entry["verifyUrl"])


@api_router.get("/certificates/{certificate_id}/verify", tags=["Human Verification"])
def verify_certificate(certificate_id: str):
    entry = audit.certificates.get(certificate_id)
    if entry is None:
        raise HTTPException(404, "Certificate not found or expired")
    return {"valid": audit.verify_certificate(entry), "algorithm": "Ed25519", "publicKey": entry["publicKey"],
            "payloadSha256": entry["payloadSha256"], "certificateSha256": entry["certificateSha256"],
            "signature": entry["signature"], "payload": entry["payload"],
            "manifestSignature": entry["manifestSignature"],
            "notice": "Integrity of this local session record only; no independent identity or factual verification."}


@api_router.get("/certificates/{certificate_id}.pdf", tags=["Human Verification"])
def download_certificate(certificate_id: str):
    entry = audit.certificates.get(certificate_id)
    if entry is None:
        raise HTTPException(404, "Certificate not found or expired")
    return Response(entry["pdf"], media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{certificate_id}.pdf"', "Cache-Control": "no-store"})
