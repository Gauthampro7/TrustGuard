"""Bounded STFT phase and mel-band silence checks, without speaker inference."""

from functools import lru_cache
from time import perf_counter

import numpy as np

from .common import finite_array, result


@lru_cache(maxsize=16)
def _mel_filters(sample_rate, n_fft=512, bands=24):
    upper = 2595 * np.log10(1 + sample_rate / 1400)
    edges = 700 * (10 ** (np.linspace(0, upper, bands + 2) / 2595) - 1)
    frequencies = np.fft.rfftfreq(n_fft, 1 / sample_rate)
    rising = (frequencies[None, :] - edges[:-2, None]) / np.maximum(edges[1:-1, None] - edges[:-2, None], 1e-12)
    falling = (edges[2:, None] - frequencies[None, :]) / np.maximum(edges[2:, None] - edges[1:-1, None], 1e-12)
    filters = np.maximum(0, np.minimum(rising, falling))
    return filters / np.maximum(filters.sum(axis=1, keepdims=True), 1e-12)


def analyze(audio_samples, sample_rate=16000):
    """Inspect <=96000 mono PCM samples; digital pauses also occur in valid edits."""
    start = perf_counter()
    signal = finite_array(audio_samples, "audio_samples", limit=96000, ndim=1)
    if not isinstance(sample_rate, (int, float)) or not np.isfinite(sample_rate) or not 8000 <= sample_rate <= 48000:
        raise ValueError("sample_rate must be between 8000 and 48000 Hz")
    if signal.size < 1024 or float(np.max(signal)) == float(np.min(signal)):
        return result("audio_vocoder", start, findings=[
            "Silent, constant or very short audio cannot support a vocoder artifact assessment."
        ], metrics={"evaluated": False, "durationSec": round(signal.size / sample_rate, 6)})
    peak = float(np.max(np.abs(signal)))
    # Peak normalization would lift a bare noise floor to full scale; record the level first.
    near_silent = peak < 1e-3
    signal = signal / max(peak, 1e-12)
    n_fft, hop = 512, 128
    frames = np.lib.stride_tricks.sliding_window_view(signal, n_fft)[::hop]
    spectrum = np.fft.rfft(frames * np.hanning(n_fft), axis=1)
    power = np.abs(spectrum) ** 2
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    phase = np.angle(spectrum)
    expected = 2 * np.pi * np.arange(power.shape[1]) * hop / n_fft
    residual = np.angle(np.exp(1j * (np.diff(phase, axis=0) - expected)))
    energy_mask = (power[1:] > power.max() * 0.005) & (power[:-1] > power.max() * 0.005)
    phase_cut_rate = float(np.mean(np.abs(residual[energy_mask]) > 2.6)) if energy_mask.any() else 0.0
    # Einsum avoids a multithreaded BLAS startup cost on short laptop workloads.
    mel_power = np.einsum("ij,kj->ik", power, _mel_filters(sample_rate), optimize=False)
    digital_silence = (rms < 1e-7) & (mel_power.max(axis=1) < 1e-10)
    changes = np.diff(np.r_[False, digital_silence, False].astype(int))
    starts, ends = np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)
    interior = (starts > 0) & (ends < len(rms))
    gaps = (ends - starts) * hop / sample_rate
    brief_gaps = int(np.sum(interior & (gaps <= 0.20)))
    # Wide simultaneous power drops can reflect gating, packet loss or editing.
    log_mel = 10 * np.log10(mel_power + 1e-12)
    cuts = int(np.sum(np.mean(np.diff(log_mel, axis=0) < -35, axis=1) > 0.8))
    phase_signal = np.clip((phase_cut_rate - 0.18) / 0.3, 0, 1)
    silence_signal = min(1.0, brief_gaps / 3)
    score = float(min(0.8, 0.25 * phase_signal + 0.55 * silence_signal))
    duration = signal.size / sample_rate
    active_fraction = float(np.mean(rms >= max(1e-6, rms.max() * 0.02)))
    uncertainty = max(0.45, 0.8 if duration < 0.5 or near_silent else 0, 1 - active_fraction)
    findings = [
        "Brief digital silence and spectral transitions warrant listening to the unprocessed recording." if score >= 0.3
        else "No strong combination of phase and digital-silence anomalies was measured.",
        "Phase behavior and silence are not vocoder-specific; noise reduction, codecs and edits are plausible alternatives.",
    ]
    if near_silent:
        findings.append("Peak level is below -60 dBFS; the clip may contain only a noise floor, so these measurements have little support.")
    return result("audio_vocoder", start, score, uncertainty, findings, {
        "evaluated": True, "durationSec": round(duration, 6),
        "peakDbfs": round(20 * float(np.log10(max(peak, 1e-12))), 3),
        "phaseDiscontinuityRate": round(phase_cut_rate, 6),
        "briefDigitalSilenceGaps": brief_gaps, "melBandAbruptCuts": cuts,
        "digitalSilenceFraction": round(float(digital_silence.mean()), 6),
        "activeFrameFraction": round(active_fraction, 6),
    })
