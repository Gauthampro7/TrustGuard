"""Session-local canary registration for consented public text."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...forensics import canary_tripwire
from ...models.api_responses import CanaryRegistrationResponse
from ..dependencies import _registered_canaries

router = APIRouter()


class CanaryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)



@router.post("/canaries", response_model=CanaryRegistrationResponse, tags=["Canary"])
def register_canary(request: CanaryRequest):
    try:
        result = canary_tripwire.generate(request.text)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    _registered_canaries.append(result["token"])
    return {"markedText": result["text"], "token": result["token"],
            "notice": "Registered for this server session. A match indicates copied text, not a bot or unauthorized use. Platforms may strip invisible markers."}
