"""
TrustGuard Core Application Configuration
Standard settings for local CPU-optimized execution (<150ms latency target).
"""

import os
from typing import List
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "TrustGuard"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DESCRIPTION: str = "Multi-Modal AI for Digital Trust · Track 01 PS-02 Core Engine"
    
    # Server configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    PUBLIC_BASE_URL: str = os.environ.get("TRUSTGUARD_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    
    # CORS Configuration (Enables local Chrome Extension and Web Portal access)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # Thresholds for Epistemic Uncertainty & False-Positive Dampening
    UNCERTAINTY_THRESHOLD: float = 0.50
    HOMOGLYPH_SIMILARITY_THRESHOLD: float = 0.85
    STYLOMETRIC_Z_THRESHOLD: float = 2.50


settings = Settings()
