"""Transient browser-extension profile evaluation."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from ...core.inspection import DIMENSIONS
from ...models.schemas import (
    ProfileEvaluationRequest, ProfileEvaluationResponse, TrustGuardInspectionRequest,
)
from ..dependencies import run_inspection

router = APIRouter()


@router.post("/extension/evaluate-profile", response_model=ProfileEvaluationResponse, tags=["Browser Extension"])
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
