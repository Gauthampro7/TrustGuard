"""Compose the versioned API while keeping the application import stable."""

from fastapi import APIRouter

from ..models.api_responses import HTTPErrorResponse
from .endpoints import audits, canaries, inspection, profiles, scenarios, system

api_router = APIRouter(responses={
    404: {"model": HTTPErrorResponse, "description": "Requested scenario, case or certificate was not found."},
    413: {"model": HTTPErrorResponse, "description": "The request exceeds the transient body-size limit."},
    422: {"model": HTTPErrorResponse, "description": "Validation failed; detail is a message or a list of sanitized validation issues."},
})
api_router.include_router(system.router)
api_router.include_router(inspection.router)
api_router.include_router(profiles.router)
api_router.include_router(scenarios.router)
api_router.include_router(canaries.router)
api_router.include_router(audits.router)
