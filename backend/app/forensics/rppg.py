"""Chrominance periodicity from caller-supplied facial ROI mean RGB traces.

No face detector or biological identity model is present. A periodic component
can be replayed or synthesized; its absence can reflect lighting or motion.
Consequently neither outcome authenticates a living person or identifies a fake.
"""

from time import perf_counter

import numpy as np

from .common import finite_array, result


def _peak(signal, sample_rate):
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(signal.size))) ** 2
    frequencies = np.fft.rfftfreq(signal.size, 1 / sample_rate)
    band = (frequencies >= 0.7) & (frequencies <= min(3.0, sample_rate * 0.45))
    indexes = np.flatnonzero(band)
    if indexes.size < 3 or float(spectrum[band].sum()) < 1e-16:
        return 0.0, 0.0
    peak = int(indexes[np.argmax(spectrum[band])])
    neighbors = np.arange(max(0, peak - 1), min(spectrum.size, peak + 2))
    # Include all non-DC frequencies in the denominator: out-of-band motion
    # should lower the apparent regularity instead of vanishing in a bandpass.
    concentration = float(spectrum[neighbors].sum() / max(float(spectrum[1:].sum()), 1e-30))
    return float(frequencies[peak]), concentration


def analyze(rgb_trace, sample_rate=25):
    """Measure >=8 seconds and <=1500 ROI means, each [R,G,B] in [0,255]."""
    start = perf_counter()
    rgb = finite_array(rgb_trace, "rgb_trace", limit=1500 * 3)
    if not isinstance(sample_rate, (int, float)) or not np.isfinite(sample_rate) or not 5 <= sample_rate <= 120:
        raise ValueError("sample_rate must be between 5 and 120 samples/second")
    if rgb.size and (rgb.ndim != 2 or rgb.shape[1] != 3 or rgb.shape[0] > 1500):
        raise ValueError("rgb_trace must contain at most 1500 three-channel RGB means")
    if (rgb < 0).any() or (rgb > 255).any():
        raise ValueError("rgb_trace must be within [0,255]")
    base = {"evaluated": False, "pulseRegularity": None, "pulseFrequencyHz": None,
        "inputKind": "caller_supplied_facial_roi_mean_rgb", "biologicalLivenessEstablished": False}

    def abstain(reason):
        return result("rppg", start, findings=[reason,
            "Absence of measurable chrominance periodicity is not evidence of synthetic media."
        ], metrics=base.copy())

    if not rgb.size or rgb.shape[0] / sample_rate < 8:
        return abstain("At least eight seconds of consistently tracked facial ROI means are required.")
    channel_means = rgb.mean(axis=0)
    if float(channel_means.min()) < 1e-3 or float(rgb.std(axis=0).max()) < 1e-7:
        return abstain("The ROI trace has too little color variation or too little signal.")
    normalized = rgb / channel_means - 1
    # Linear detrending of illumination drift, then the CHROM projection.
    time_axis = np.linspace(-1, 1, rgb.shape[0])
    normalized -= time_axis[:, None] * np.sum(time_axis[:, None] * normalized, axis=0) / np.sum(time_axis ** 2)
    x = 3 * normalized[:, 0] - 2 * normalized[:, 1]
    y = 1.5 * normalized[:, 0] + normalized[:, 1] - 1.5 * normalized[:, 2]
    alpha = float(x.std() / max(float(y.std()), 1e-12))
    chrominance = x - alpha * y
    if float(chrominance.std()) < 1e-6:
        return abstain("Color variation is dominated by shared illumination; no stable chrominance component remains.")
    frequency, concentration = _peak(chrominance, sample_rate)
    mid = len(chrominance) // 2
    first_frequency, first_concentration = _peak(chrominance[:mid], sample_rate)
    last_frequency, last_concentration = _peak(chrominance[mid:], sample_rate)
    disagreement = abs(first_frequency - last_frequency)
    duration = rgb.shape[0] / sample_rate
    if concentration < 0.55 or min(first_concentration, last_concentration) < 0.5 or disagreement > max(0.2, 2 / duration):
        return abstain("No stable physiological-band chrominance peak persists across both halves of the trace.")
    regularity = float(np.clip(np.sqrt(concentration * min(first_concentration, last_concentration)) * np.exp(-disagreement / 0.3), 0, 1))
    return result("rppg", start, 0.0, 0.8 if sample_rate < 8 else 0.65, [
        f"The supplied ROI has a stable {frequency:.2f} Hz chrominance component across two time windows.",
        "Periodicity may reflect pulse, motion, lighting, replay or synthesis; it is not a biological liveness probability or proof of authenticity.",
    ], {**base, "evaluated": True, "pulseRegularity": round(regularity, 6),
        "pulseFrequencyHz": round(frequency, 6), "windowFrequencyDisagreementHz": round(disagreement, 6),
        "spectralConcentration": round(concentration, 6), "durationSec": round(duration, 6)})
