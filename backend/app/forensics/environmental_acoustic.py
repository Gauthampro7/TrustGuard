"""Conditional RT60 estimation from a supplied measured room impulse response.

This is a Schroeder backward energy integration / T20 extrapolation. It is not
a blind reverberation estimator for speech. The caller must supply a measured
impulse response, with an adequate decay tail, rather than ordinary audio.
Environment ranges below are broad demonstration heuristics, not room labels.
"""

from time import perf_counter

import numpy as np

from .common import bounded_text, finite_array, result

_ENVIRONMENTS = {
    "studio": (0.05, 0.4), "office": (0.15, 1.0),
    "conference_hall": (0.4, 2.5), "conference hall": (0.4, 2.5),
    "airport": (0.6, 4.0), "hall": (0.4, 2.5),
}


def analyze(impulse_response, sample_rate=16000, claimed_environment=None):
    """Estimate RT60 only if a measured <=96000-sample IR supports T20 fitting.

    The declared room is contextual input, not an observed video classification.
    Microphone directivity, furnishings and processing can invalidate comparison.
    """
    start = perf_counter()
    impulse = finite_array(impulse_response, "impulse_response", limit=96000, ndim=1)
    if not isinstance(sample_rate, (int, float)) or not np.isfinite(sample_rate) or not 8000 <= sample_rate <= 48000:
        raise ValueError("sample_rate must be between 8000 and 48000 Hz")
    if claimed_environment is not None:
        bounded_text(claimed_environment, "claimed_environment")
    if (np.abs(impulse) > 1).any():
        raise ValueError("impulse_response must be normalized to [-1, 1]")
    profile = claimed_environment.casefold().strip() if claimed_environment else "unspecified"
    base = {"evaluated": False, "rt60Sec": None, "matchScore": None, "profile": profile,
        "inputKind": "caller_supplied_room_impulse_response", "method": "Schroeder T20 extrapolation"}

    def abstain(reason):
        return result("environmental_acoustic", start, findings=[reason,
            "Only a measured room impulse response can support this estimator; ordinary speech must not be submitted as an impulse response."
        ], metrics=base.copy())

    if impulse.size < max(512, int(sample_rate * 0.1)) or float(np.max(np.abs(impulse), initial=0)) < 1e-8:
        return abstain("The impulse response is too short or silent for a decay measurement.")
    # Start at the strongest direct arrival to avoid pre-trigger silence.
    impulse = impulse[int(np.argmax(np.abs(impulse))):]
    if impulse.size < 512:
        return abstain("The direct arrival is too near the end of the supplied response.")
    power = impulse * impulse
    segment = max(32, impulse.size // 10)
    dynamic_range = float(10 * np.log10((power[:segment].mean() + 1e-30) / (power[-segment:].mean() + 1e-30)))
    if dynamic_range < 30:
        return abstain("The decay tail has inadequate dynamic range; background noise or truncation prevents a reliable T20 fit.")
    energy = np.cumsum(power[::-1])[::-1]
    decay_db = 10 * np.log10(np.maximum(energy / energy[0], 1e-30))
    fit_mask = (decay_db <= -5) & (decay_db >= -25)
    selected = np.flatnonzero(fit_mask)
    if selected.size < 32 or float(np.ptp(decay_db[fit_mask])) < 19 or selected[-1] - selected[0] < sample_rate * 0.01:
        return abstain("The response lacks an adequately sampled -5 to -25 dB decay interval.")
    times = selected / sample_rate
    observed = decay_db[fit_mask]
    slope, intercept = np.polyfit(times, observed, 1)
    fitted = slope * times + intercept
    residual = float(np.sum((observed - fitted) ** 2))
    total = float(np.sum((observed - observed.mean()) ** 2))
    r_squared = 1 - residual / max(total, 1e-20)
    rt60 = float(-60 / slope) if slope < 0 else float("inf")
    if r_squared < 0.95 or not 0.04 <= rt60 <= 8:
        return abstain("Decay is not sufficiently linear over the T20 interval for a reliable RT60 extrapolation.")
    expected = _ENVIRONMENTS.get(profile)
    match = None
    anomaly = 0.0
    findings = [f"Supplied impulse-response decay extrapolates to RT60 {rt60:.3f} s (T20 fit R² {r_squared:.3f})."]
    if expected:
        low, high = expected
        distance = (low - rt60) / low if rt60 < low else (rt60 - high) / high if rt60 > high else 0.0
        match = float(np.clip(1 - distance, 0, 1))
        anomaly = min(0.6, (1 - match) * 0.6)
        findings.append("The decay is outside a broad illustrative range for the declared room." if anomaly > 0.2
            else "The decay overlaps a broad illustrative range for the declared room.")
    elif profile == "outdoors":
        findings.append("Outdoor reflections vary too widely for a room-range match score.")
    findings.append("Room size, microphone placement and noise reduction can explain differences; this measurement cannot establish dubbing or deception.")
    return result("environmental_acoustic", start, anomaly, 0.55 if expected else 0.7, findings, {
        **base, "evaluated": True, "rt60Sec": round(rt60, 6),
        "matchScore": None if match is None else round(match, 6),
        "decayFitR2": round(r_squared, 6), "tailDynamicRangeDb": round(dynamic_range, 3),
        "fitDurationSec": round(float(times[-1] - times[0]), 6),
        "expectedRangeSec": list(expected) if expected else None,
    })
