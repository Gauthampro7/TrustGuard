"""Shared process-local API state and inspection error translation.

Every endpoint imports the same registry; registration, capability counts and
inspection therefore observe one bounded canary collection per server process.
"""

from collections import deque

from fastapi import HTTPException

from ..core.inspection import inspect, InsufficientModalities

_registered_canaries = deque(["creator_canary_token_2026"], maxlen=100)


def run_inspection(request, *, require_multimodal=True):
    try:
        return inspect(request, require_multimodal=require_multimodal, registered_tokens=tuple(_registered_canaries))
    except (InsufficientModalities, ValueError) as error:
        raise HTTPException(422, str(error)) from error
    except Exception as error:
        raise HTTPException(500, "Inspection failed due to an internal processing error") from error
