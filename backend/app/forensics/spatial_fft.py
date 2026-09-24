"""Windowed 2D-FFT radial spectra; periodicity is not a synthesis diagnosis."""

from functools import lru_cache
from time import perf_counter

import numpy as np

from .common import grayscale, result


@lru_cache(maxsize=16)
def _geometry(height, width):
    yy, xx = np.indices((height, width))
    radii = np.floor(np.hypot(yy - height // 2, xx - width // 2)).astype(int)
    counts = np.bincount(radii.ravel())
    window = np.hanning(height)[:, None] * np.hanning(width)[None, :]
    return radii, np.maximum(counts, 1), window


def analyze(image_pixels):
    """Measure <=256x256 pixels in memory; abstain on small or constant images."""
    start = perf_counter()
    gray = grayscale(image_pixels)
    if not gray.size or min(gray.shape) < 16 or float(gray.std()) < 1e-5:
        return result("spatial_fft", start, findings=[
            "Insufficient spatial texture or resolution for a radial spectrum assessment."
        ], metrics={"evaluated": False})
    radii, counts, window = _geometry(*gray.shape)
    centered = gray - gray.mean()
    power = np.abs(np.fft.fftshift(np.fft.fft2(centered * window))) ** 2
    radial = np.bincount(radii.ravel(), weights=power.ravel()) / counts
    total = float(power.sum()) + 1e-20
    nyquist = min(gray.shape) / 2
    high_ratio = float(power[radii >= 0.65 * nyquist].sum() / total)
    # A broad local mean exposes narrow rings; exclude DC and its window leakage.
    smooth = np.convolve(radial, np.ones(9) / 9, mode="same")
    valid = np.arange(len(radial)) >= max(4, int(nyquist * 0.15))
    energetic = radial > radial.max() * 1e-5
    peak_ratio = float(np.max(radial[valid & energetic] / (smooth[valid & energetic] + 1e-20), initial=1))
    fit = (np.arange(len(radial)) >= 4) & (np.arange(len(radial)) <= nyquist) & energetic
    slope = float(np.polyfit(np.log(np.flatnonzero(fit)), np.log(radial[fit]), 1)[0]) if fit.sum() >= 3 else 0.0
    peak_signal = np.clip((peak_ratio - 2.5) / 5.5, 0, 1)
    high_signal = np.clip((high_ratio - 0.5) / 0.5, 0, 1)
    score = float(min(0.85, 0.5 * peak_signal + 0.45 * high_signal))
    low_contrast = float(gray.std()) < 0.015
    uncertainty = 0.75 if low_contrast or min(gray.shape) < 48 else 0.4
    findings = [
        "Concentrated spatial frequency energy merits checking the original capture." if score >= 0.35
        else "No strong periodic spatial anomaly appears in this frame.",
        "Textures, resampling and compression can produce the same spectrum; this heuristic does not identify AI generation.",
    ]
    return result("spatial_fft", start, score, uncertainty, findings, {
        "evaluated": True, "highFrequencyPowerRatio": round(high_ratio, 6),
        "spectralPeakRatio": round(peak_ratio, 6), "rolloffSlope": round(slope, 6),
        "width": gray.shape[1], "height": gray.shape[0],
        "azimuthalPower": np.round(radial / (radial.sum() + 1e-20), 8).tolist(),
    })
