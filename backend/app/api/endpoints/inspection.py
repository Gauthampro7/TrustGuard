"""Multimodal inspection entry point and derived case retention."""

from fastapi import APIRouter

from ...core import audit
from ...models.schemas import TrustGuardInspectionRequest, TrustGuardInspectionVerdict
from ..dependencies import run_inspection

router = APIRouter()


@router.post("/inspect", response_model=TrustGuardInspectionVerdict, tags=["Inspection"])
def inspect_evidence(request: TrustGuardInspectionRequest):
    verdict = run_inspection(request)
    audit.cases.put(verdict.verdictId, verdict)
    return verdict
