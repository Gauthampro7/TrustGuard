"""Local engine health and forensic capabilities."""

from datetime import datetime, timezone

from fastapi import APIRouter

from ...core import audit
from ...models.api_responses import HealthResponse, ForensicCapabilitiesResponse
from ..dependencies import _registered_canaries

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    return {"status": "healthy", "service": "TrustGuard Core API", "standard": "v1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(), "rawMediaStorage": False,
            "calibration": "heuristic, not probability calibrated", "sessionPublicKey": audit.PUBLIC_KEY}



@router.get("/forensics/capabilities", response_model=ForensicCapabilitiesResponse, tags=["System"])
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
