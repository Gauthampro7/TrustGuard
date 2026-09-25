"""Discovery and loading of the four local demonstration scenarios."""

import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ...models.api_responses import ScenarioDetailResponse
from ...models.schemas import ScenarioSummary

router = APIRouter()
SCENARIO_IDS = {"ceo-wire-scam", "homoglyph-clone", "wifi-compression-edge-case", "creator-copyright"}


@router.get("/scenarios", response_model=List[ScenarioSummary], tags=["Scenarios"])
def list_scenarios():
    items = []
    scenarios_dir = Path(__file__).resolve().parents[2] / "scenarios"
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



@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse,
            response_model_exclude_unset=True, tags=["Scenarios"])
def get_scenario(scenario_id: str):
    if scenario_id not in SCENARIO_IDS:
        raise HTTPException(404, "Unknown scenario")
    path = Path(__file__).resolve().parents[2] / "scenarios" / f"{scenario_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    ScenarioDetailResponse.model_validate(data)
    # Preserve fixture number representations and absent optional fields exactly.
    return JSONResponse(content=data)
