"""Small, bounded forensic measurements; anomaly indices are not probabilities."""

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ForensicResult:
    name: str
    score: float
    uncertainty: float
    findings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0


def result(name, start, score=0.0, uncertainty=1.0, findings=None, metrics=None):
    """Finish a measurement with finite, JSON-compatible scalar outputs."""
    return ForensicResult(
        name=name,
        score=round(float(np.clip(score, 0.0, 1.0)), 6),
        uncertainty=round(float(np.clip(uncertainty, 0.0, 1.0)), 6),
        findings=findings or [],
        metrics=metrics or {},
        elapsed_ms=round((perf_counter() - start) * 1000, 3),
    )


def finite_array(values, name, *, limit, ndim=None):
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a rectangular numeric array") from exc
    if array.size > limit:
        raise ValueError(f"{name} exceeds the {limit}-value extraction limit")
    if ndim is not None and array.ndim != ndim:
        raise ValueError(f"{name} must have {ndim} dimension(s)")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    return array


def grayscale(values):
    """Accept <=256x256 grayscale/RGB(A) data and scale to [0, 1]."""
    pixels = finite_array(values, "image_pixels", limit=256 * 256 * 4)
    if pixels.size == 0:
        return np.empty((0, 0))
    if pixels.ndim not in (2, 3) or max(pixels.shape[:2]) > 256:
        raise ValueError("image_pixels must be at most 256x256 grayscale or RGB(A)")
    if pixels.ndim == 3:
        if pixels.shape[2] not in (3, 4):
            raise ValueError("image_pixels needs 3 RGB or 4 RGBA channels")
        pixels = np.einsum("ijk,k->ij", pixels[:, :, :3], [0.2126, 0.7152, 0.0722])
    if pixels.min() < 0 or pixels.max() > 255:
        raise ValueError("image_pixels must be in [0, 1] or [0, 255]")
    return pixels / 255.0 if pixels.max() > 1 else pixels


def bounded_text(text, name="text"):
    if not isinstance(text, str):
        raise ValueError(f"{name} must be a string")
    if len(text) > 20000:
        raise ValueError(f"{name} exceeds the 20000-character extraction limit")
    return text
