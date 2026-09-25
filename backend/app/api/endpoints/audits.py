"""Human verification statements and signed incident certificates."""

from fastapi import APIRouter, HTTPException, Response

from ...core import audit
from ...core.config import settings
from ...models.api_responses import CertificateVerificationResponse
from ...models.schemas import AuditSignRequest, AuditCertificateResponse

router = APIRouter()


@router.post("/cases/{case_id}/sign-audit", response_model=AuditCertificateResponse, tags=["Human Verification"])
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
    try:
        certificate_id, entry = audit.create_certificate(verdict, request, settings.PUBLIC_BASE_URL)
    except Exception as exc:
        raise HTTPException(500, "Certificate generation failed") from exc
    return AuditCertificateResponse(auditCertificateId=certificate_id, timestamp=entry["timestamp"],
        certificateSha256=entry["certificateSha256"], downloadPdfUrl=f"/api/v1/certificates/{certificate_id}.pdf", verifyUrl=entry["verifyUrl"])



@router.get("/certificates/{certificate_id}/verify", response_model=CertificateVerificationResponse, tags=["Human Verification"])
def verify_certificate(certificate_id: str):
    entry = audit.certificates.get(certificate_id)
    if entry is None:
        raise HTTPException(404, "Certificate not found or expired")
    return {"valid": audit.verify_certificate(entry), "algorithm": "Ed25519", "publicKey": entry["publicKey"],
            "payloadSha256": entry["payloadSha256"], "certificateSha256": entry["certificateSha256"],
            "signature": entry["signature"], "payload": entry["payload"],
            "manifestSignature": entry["manifestSignature"],
            "notice": "Integrity of this local session record only; no independent identity or factual verification."}



@router.get("/certificates/{certificate_id}.pdf", response_class=Response,
            responses={200: {"description": "Signed incident certificate PDF", "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            }}}, tags=["Human Verification"])
def download_certificate(certificate_id: str):
    entry = audit.certificates.get(certificate_id)
    if entry is None:
        raise HTTPException(404, "Certificate not found or expired")
    return Response(entry["pdf"], media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{certificate_id}.pdf"', "Cache-Control": "no-store"})
