"""Typed discovery, registration, certificate and error response boundaries.

Inspection data contracts remain in schemas.py. These models document existing
wire representations without changing their meaning or adding response fields.
"""

from pydantic import BaseModel

from .schemas import AuditSignRequest, ScenarioSummary, TrustGuardInspectionRequest, TrustGuardInspectionVerdict


class HealthResponse(BaseModel):
    status: str
    service: str
    standard: str
    timestamp: str
    rawMediaStorage: bool
    calibration: str
    sessionPublicKey: str


class ExtractorCapability(BaseModel):
    id: str
    modality: str
    description: str


class ForensicCapabilitiesResponse(BaseModel):
    engine: str
    latencyTargetMs: int
    gpuRequired: bool
    extractors: list[ExtractorCapability]
    activeRegisteredCanaries: int
    calibration: str


class CanaryRegistrationResponse(BaseModel):
    markedText: str
    token: str
    notice: str


class ScenarioDetailResponse(ScenarioSummary):
    request: TrustGuardInspectionRequest


class SignedAuditPayload(BaseModel):
    certificateId: str
    timestamp: str
    verdict: TrustGuardInspectionVerdict
    analystStatement: AuditSignRequest
    scope: str


class CertificateVerificationResponse(BaseModel):
    valid: bool
    algorithm: str
    publicKey: str
    payloadSha256: str
    certificateSha256: str
    signature: str
    payload: SignedAuditPayload
    manifestSignature: str
    notice: str


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class HTTPErrorResponse(BaseModel):
    detail: str | list[ValidationIssue]
