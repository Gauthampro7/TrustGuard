"""Audio-envelope/mouth-aperture alignment; does not infer phonemes or identity."""

from time import perf_counter

import numpy as np

from .common import finite_array, result


def _correlation(left, right):
    left = left - left.mean()
    right = right - right.mean()
    denominator = float(np.sqrt(np.sum(left * left) * np.sum(right * right)))
    return float(np.sum(left * right) / denominator) if denominator > 1e-12 else 0.0


def analyze(audio_envelope, mouth_aperture, sample_rate=25):
    """Compare synchronized, equally sampled traces (<=1500 values each).

    Positive lag means mouth aperture trails the audio envelope. Values must
    share timestamps and a sample rate; the caller supplies measured mouth ROIs.
    """
    start = perf_counter()
    audio = finite_array(audio_envelope, "audio_envelope", limit=1500, ndim=1)
    mouth = finite_array(mouth_aperture, "mouth_aperture", limit=1500, ndim=1)
    if not isinstance(sample_rate, (int, float)) or not np.isfinite(sample_rate) or not 5 <= sample_rate <= 120:
        raise ValueError("sample_rate must be between 5 and 120 samples/second")
    if audio.size != mouth.size:
        raise ValueError("audio_envelope and mouth_aperture must have equal lengths and timestamps")
    if (audio < 0).any() or (mouth < 0).any():
        raise ValueError("Envelope and aperture measurements must be nonnegative")
    if audio.size:
        audio = audio / max(float(audio.max()), 1e-12)
        mouth = mouth / max(float(mouth.max()), 1e-12)
    if audio.size < max(12, int(sample_rate)) or float(audio.std()) < 1e-8 or float(mouth.std()) < 1e-8:
        return result("cross_modal_sync", start, findings=[
            "Too few aligned samples or insufficient mouth/audio movement; alignment is undetermined."
        ], metrics={"evaluated": False})
    max_lag = min(int(round(sample_rate * 0.6)), audio.size // 4)
    lags = np.arange(-max_lag, max_lag + 1)
    correlations = []
    for lag in lags:
        if lag > 0:
            pair = audio[:-lag], mouth[lag:]
        elif lag < 0:
            pair = audio[-lag:], mouth[:lag]
        else:
            pair = audio, mouth
        correlations.append(_correlation(*pair))
    # Prefer the closest alignment when periodic traces offer indistinguishable peaks.
    maximum = max(correlations)
    candidates = [i for i, corr in enumerate(correlations) if corr >= maximum - 1e-6]
    best = min(candidates, key=lambda i: abs(lags[i]))
    lag_sec = float(lags[best] / sample_rate)
    correlation = float(correlations[best])
    zero_correlation = correlations[max_lag]
    score = max(0.0, min(0.9, (abs(lag_sec) - 0.12) / 0.4)) * max(0, correlation)
    if correlation < 0.3:
        score, uncertainty = 0.0, 0.9
        finding = "Mouth and audio traces have weak association; a reliable offset cannot be inferred."
    else:
        uncertainty = max(0.35, 0.75 if audio.size / sample_rate < 2 else 0, 0.65 if abs(lags[best]) == max_lag else 0)
        finding = f"Best envelope alignment has a {round(lag_sec * 1000)} ms mouth delay relative to audio."
    return result("cross_modal_sync", start, score, uncertainty, [finding,
        "Envelope correlation is a coarse timing cue; network drift, editing and speaking dynamics can explain offsets."
    ], {
        "evaluated": True, "correlation": round(correlation, 6),
        "zeroLagCorrelation": round(zero_correlation, 6),
        "lagMs": round(lag_sec * 1000, 3), "lagFrames": int(lags[best]),
        "sampleRate": sample_rate, "sampleCount": int(audio.size),
        "searchBoundaryReached": bool(abs(lags[best]) == max_lag),
    })
