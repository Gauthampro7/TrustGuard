"""Seeded benign and perturbed synthetic controls for every forensic module.

These are generated signals, not a labeled real-world corpus. They show how each
heuristic responds to a known transformation (resampling, quantization, phase
edits, text scarcity, lag sign, multilingual names, authorized reuse, decay-tail
noise, shared illumination) and whether it abstains. They do not measure
deepfake detection accuracy.

Print the distribution tables recorded in backend/app/forensics/VALIDATION.md:

    python -m tests.forensics.fixtures.controls --seeds 20
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

import numpy as np

from backend.app.forensics import (
    audio_vocoder, canary_tripwire, cross_modal_sync, environmental_acoustic,
    homoglyph_hunter, perceptual_hash, rppg, spatial_fft, stylometry_drift,
)

RATE = 16000
TRACE_RATE = 25


# ---------------------------------------------------------------- images

def natural_image(rng, size=128):
    """Smooth 1/f-like texture: summed octaves of bilinearly upsampled noise."""
    image = np.zeros((size, size))
    for octave in range(2, 7):
        cells = 2 ** octave
        coarse = rng.random((cells + 1, cells + 1))
        axis = np.linspace(0, cells, size)
        i0 = np.minimum(axis.astype(int), cells - 1)
        frac = axis - i0
        rows = coarse[i0] * (1 - frac)[:, None] + coarse[i0 + 1] * frac[:, None]
        image += (rows[:, i0] * (1 - frac) + rows[:, i0 + 1] * frac) / cells ** 0.8
    image -= image.min()
    return image / image.max() * 200 + 25


def nearest_upsample(image, factor=2):
    """Downsample by striding, then nearest-neighbour upsample back (resampling)."""
    small = image[::factor, ::factor]
    return np.repeat(np.repeat(small, factor, axis=0), factor, axis=1)[:image.shape[0], :image.shape[1]]


def quantize(values, levels, low=0.0, high=255.0):
    step = (high - low) / (levels - 1)
    return np.round((np.asarray(values) - low) / step) * step + low


def block_quantize(image, block=8, keep=0.35):
    """JPEG-like: flatten each 8x8 block toward its mean (coarse DC-dominant coding)."""
    out = image.copy()
    for y in range(0, image.shape[0], block):
        for x in range(0, image.shape[1], block):
            tile = out[y:y + block, x:x + block]
            tile[:] = tile.mean() + keep * (tile - tile.mean())
    return out


def checkerboard(image, amplitude=12):
    """Periodic upsampling-like pixel grid added to a natural texture."""
    grid = (np.indices(image.shape).sum(axis=0) % 2) * 2 - 1
    return np.clip(image + amplitude * grid, 0, 255)


# ---------------------------------------------------------------- audio

def speech_like(rng, seconds=3.0, rate=RATE):
    """Harmonic voiced tone with syllabic amplitude modulation and a noise floor."""
    t = np.arange(int(seconds * rate)) / rate
    f0 = 120 + 20 * np.sin(2 * np.pi * 0.7 * t + rng.uniform(0, 2 * np.pi))
    phase = 2 * np.pi * np.cumsum(f0) / rate
    voiced = sum(np.sin(k * phase + rng.uniform(0, 2 * np.pi)) / k for k in range(1, 9))
    envelope = 0.55 + 0.45 * np.sin(2 * np.pi * rng.uniform(3, 5) * t + rng.uniform(0, 2 * np.pi))
    signal = voiced * envelope + rng.normal(0, 0.02, t.size)
    return signal / np.max(np.abs(signal)) * 0.8


def resample(signal, source_rate, target_rate):
    positions = np.linspace(0, signal.size - 1, int(round(signal.size * target_rate / source_rate)))
    return np.interp(positions, np.arange(signal.size), signal)


def phase_scramble_frames(rng, signal, frame=512):
    """Randomize STFT-frame phases while keeping magnitudes (vocoder-like phase edits)."""
    out = signal.copy()
    for start in range(0, signal.size - frame, frame):
        spectrum = np.fft.rfft(signal[start:start + frame])
        spectrum = np.abs(spectrum) * np.exp(1j * rng.uniform(-np.pi, np.pi, spectrum.size))
        out[start:start + frame] = np.fft.irfft(spectrum, frame)
    return out / max(np.max(np.abs(out)), 1e-12) * 0.8


def gate(signal, starts, length, value=0.0, rng=None, noise=0.0):
    """Insert exact digital silence (valid noise gates also do this) or a low noise floor."""
    out = signal.copy()
    for start in starts:
        out[start:start + length] = value if not noise else rng.normal(0, noise, length)
    return out


# ---------------------------------------------------------------- text

BUSINESS = (
    "Thanks for the update on the quarterly review. I have read the draft and the numbers look "
    "consistent with what we saw last month. Could you share the supplier figures with the team "
    "before Thursday so that we can discuss them in the planning meeting? I will be in the office "
    "all week and we can also talk about the hiring plan. Let me know if anything in the report "
    "needs a second look, and thanks again for pulling it together so carefully."
)
TOPIC_SHIFT = (
    "The garden was quiet after the rain and the birds came back to the feeder by the window. "
    "We walked along the river in the evening and watched the light fade over the hills. My "
    "sister brought a basket of apples from the orchard and we baked a pie with cinnamon and "
    "butter. The children played in the grass until it was dark and then we read stories by the fire."
)
URGENT = " This is urgent and confidential. Wire the payment to the new bank account immediately and do not call anyone to verify."
HINDI = "कृपया रिपोर्ट को गुरुवार से पहले टीम के साथ साझा करें ताकि हम योजना बैठक में इस पर चर्चा कर सकें और आगे का निर्णय ले सकें।"


def words(text, count):
    return " ".join(text.split()[:count])


# ---------------------------------------------------------------- synchrony traces

def speech_envelope(rng, seconds=8.0, rate=TRACE_RATE):
    """Irregular syllable bursts, so the cross-correlation has one clear peak."""
    n = int(seconds * rate)
    bursts = np.zeros(n)
    positions = np.cumsum(rng.integers(3, 9, size=n))
    bursts[positions[positions < n]] = rng.uniform(0.4, 1.0, np.sum(positions < n))
    kernel = np.exp(-np.arange(6) / 1.5)
    return np.convolve(bursts, kernel)[:n] + 0.02


def delayed(trace, frames, rng, noise=0.03):
    """Positive frames: mouth trails audio (the v1 lag convention)."""
    shifted = np.roll(trace, frames)
    if frames > 0:
        shifted[:frames] = trace[0]
    elif frames < 0:
        shifted[frames:] = trace[-1]
    return np.clip(shifted + rng.normal(0, noise, trace.size), 0, None)


# ---------------------------------------------------------------- room responses

def impulse_response(rng, rt60, seconds=1.2, rate=RATE, noise_db=None):
    """Exponential decay with RT60 seconds; optional stationary tail noise (dB re peak energy)."""
    t = np.arange(int(seconds * rate)) / rate
    decay = rng.normal(0, 1, t.size) * 10 ** (-3 * t / rt60)
    decay[0] = 1.0
    if noise_db is not None:
        decay += rng.normal(0, 10 ** (noise_db / 20), t.size)
    return decay / np.max(np.abs(decay))


# ---------------------------------------------------------------- ROI chrominance

def roi_trace(rng, seconds=12.0, rate=TRACE_RATE, pulse_hz=1.2, pulse=0.6, illumination=0.0, noise=0.15):
    """Mean skin RGB with a small pulse mostly in green, and optional shared flicker."""
    t = np.arange(int(seconds * rate)) / rate
    base = np.array([150.0, 110.0, 90.0])
    wave = np.sin(2 * np.pi * pulse_hz * t + rng.uniform(0, 2 * np.pi))
    pulse_rgb = pulse * wave[:, None] * np.array([0.3, 1.0, 0.2])
    shared = illumination * np.sin(2 * np.pi * rng.uniform(0.8, 2.5) * t)[:, None] * base / 100
    trace = base + pulse_rgb + shared + rng.normal(0, noise, (t.size, 3))
    return np.clip(trace, 0, 255)


# ---------------------------------------------------------------- the bench

@dataclass(frozen=True)
class Control:
    module: str
    name: str
    kind: str  # benign | perturbed | abstain
    run: Callable


def _hamming(left, right):
    return {"hammingDistance": perceptual_hash.analyze(left, right).metrics.get("hammingDistance")}


def controls():
    """Every control takes a seeded Generator and returns a ForensicResult (or dict for canaries)."""
    c = []
    add = lambda module, name, kind, run: c.append(Control(module, name, kind, run))

    # spatial_fft
    add("spatial_fft", "natural texture", "benign", lambda r: spatial_fft.analyze(natural_image(r)))
    add("spatial_fft", "natural texture, normalized 0-1 input", "benign", lambda r: spatial_fft.analyze(natural_image(r) / 255))
    add("spatial_fft", "quantized to 16 levels", "perturbed", lambda r: spatial_fft.analyze(quantize(natural_image(r), 16)))
    add("spatial_fft", "2x stride + nearest upsample", "perturbed", lambda r: spatial_fft.analyze(nearest_upsample(natural_image(r))))
    add("spatial_fft", "8x8 block flattening", "perturbed", lambda r: spatial_fft.analyze(block_quantize(natural_image(r))))
    add("spatial_fft", "additive sensor noise sd 8", "perturbed", lambda r: spatial_fft.analyze(np.clip(natural_image(r) + r.normal(0, 8, (128, 128)), 0, 255)))
    add("spatial_fft", "checkerboard amplitude 12", "perturbed", lambda r: spatial_fft.analyze(checkerboard(natural_image(r))))
    add("spatial_fft", "near-constant frame, +/-1 level dither", "perturbed", lambda r: spatial_fft.analyze(128 + r.integers(-1, 2, (128, 128))))
    add("spatial_fft", "constant frame", "abstain", lambda r: spatial_fft.analyze(np.full((64, 64), r.uniform(0, 255))))
    add("spatial_fft", "12x12 frame", "abstain", lambda r: spatial_fft.analyze(r.random((12, 12)) * 255))

    # audio_vocoder
    add("audio_vocoder", "speech-like tone", "benign", lambda r: audio_vocoder.analyze(speech_like(r)))
    add("audio_vocoder", "speech-like tone, scaled x0.05", "benign", lambda r: audio_vocoder.analyze(speech_like(r) * 0.05))
    add("audio_vocoder", "resampled 16k->8k->16k", "perturbed", lambda r: audio_vocoder.analyze(resample(resample(speech_like(r), RATE, 8000), 8000, RATE)))
    add("audio_vocoder", "native 8 kHz", "perturbed", lambda r: audio_vocoder.analyze(speech_like(r, rate=8000), 8000))
    add("audio_vocoder", "8-bit quantization", "perturbed", lambda r: audio_vocoder.analyze(quantize(speech_like(r), 256, -1, 1)))
    add("audio_vocoder", "STFT phase scrambled", "perturbed", lambda r: audio_vocoder.analyze(phase_scramble_frames(r, speech_like(r))))
    add("audio_vocoder", "three 100 ms exact-zero gates", "perturbed", lambda r: audio_vocoder.analyze(gate(speech_like(r), (8000, 20000, 32000), 1600)))
    add("audio_vocoder", "three 100 ms low-noise gates", "perturbed", lambda r: audio_vocoder.analyze(gate(speech_like(r), (8000, 20000, 32000), 1600, rng=r, noise=1e-4)))
    add("audio_vocoder", "near-silent dither 1e-5", "perturbed", lambda r: audio_vocoder.analyze(r.normal(0, 1e-5, 3 * RATE)))
    add("audio_vocoder", "digital silence", "abstain", lambda r: audio_vocoder.analyze(np.zeros(RATE)))
    add("audio_vocoder", "0.05 s clip", "abstain", lambda r: audio_vocoder.analyze(speech_like(r, seconds=0.05)))

    # stylometry_drift
    add("stylometry_drift", "business text", "benign", lambda r: stylometry_drift.analyze(BUSINESS))
    add("stylometry_drift", "business text vs same baseline", "benign", lambda r: stylometry_drift.analyze(BUSINESS, BUSINESS))
    add("stylometry_drift", "topic shift vs baseline", "perturbed", lambda r: stylometry_drift.analyze(TOPIC_SHIFT, BUSINESS))
    for count in (5, 15, 40):
        add("stylometry_drift", f"first {count} words", "perturbed", lambda r, n=count: stylometry_drift.analyze(words(BUSINESS, n)))
    add("stylometry_drift", "20 words vs baseline (too short)", "perturbed", lambda r: stylometry_drift.analyze(words(BUSINESS, 20), BUSINESS))
    add("stylometry_drift", "urgency + payment + bypass", "perturbed", lambda r: stylometry_drift.analyze(BUSINESS + URGENT))
    add("stylometry_drift", "Hindi request", "perturbed", lambda r: stylometry_drift.analyze(HINDI))
    add("stylometry_drift", "digits and punctuation only", "abstain", lambda r: stylometry_drift.analyze("12345 !!! 67.89 ---"))

    # cross_modal_sync
    for frames in (0, 5, -5):
        kind = "benign" if frames == 0 else "perturbed"
        add("cross_modal_sync", f"mouth lag {frames * 40:+d} ms", kind,
            lambda r, f=frames: (lambda a: cross_modal_sync.analyze(a, delayed(a, f, r)))(speech_envelope(r)))
    add("cross_modal_sync", "periodic 2 Hz traces, 120 ms lag", "perturbed", lambda r: cross_modal_sync.analyze(
        1 + np.sin(2 * np.pi * 2 * np.arange(200) / TRACE_RATE), 1 + np.sin(2 * np.pi * 2 * (np.arange(200) - 3) / TRACE_RATE)))
    add("cross_modal_sync", "periodic 2 Hz traces, 300 ms lag", "perturbed", lambda r: cross_modal_sync.analyze(
        1 + np.sin(2 * np.pi * 2 * np.arange(200) / TRACE_RATE), 1 + np.sin(2 * np.pi * 2 * (np.arange(200) - 7.5) / TRACE_RATE)))
    add("cross_modal_sync", "lag beyond +/-600 ms search", "perturbed",
        lambda r: (lambda a: cross_modal_sync.analyze(a, delayed(a, 20, r)))(speech_envelope(r)))
    add("cross_modal_sync", "independent noise traces", "perturbed", lambda r: cross_modal_sync.analyze(r.random(200), r.random(200)))
    add("cross_modal_sync", "constant mouth", "abstain", lambda r: cross_modal_sync.analyze(speech_envelope(r), np.ones(200)))
    add("cross_modal_sync", "0.4 s traces", "abstain", lambda r: cross_modal_sync.analyze(r.random(10), r.random(10)))

    # homoglyph_hunter
    for name, text in {"Latin handle": "rajesh_verma", "Cyrillic name": "Дмитрий Иванов", "Greek name": "Αλέξανδρος",
                       "Devanagari name": "प्रिया शर्मा", "separate-language tokens": "Priya Дмитрий",
                       "Latin with combining acute": "José García"}.items():
        add("homoglyph_hunter", name, "benign", lambda r, t=text: homoglyph_hunter.analyze(t))
    add("homoglyph_hunter", "same handle as reference", "benign", lambda r: homoglyph_hunter.analyze("rajesh_verma", "rajesh_verma"))
    add("homoglyph_hunter", "Cyrillic a in Latin handle", "perturbed", lambda r: homoglyph_hunter.analyze("rаjesh_verma"))
    add("homoglyph_hunter", "Cyrillic a vs reference", "perturbed", lambda r: homoglyph_hunter.analyze("rаjesh_verma", "rajesh_verma"))
    add("homoglyph_hunter", "l->1 digit swap vs reference", "perturbed", lambda r: homoglyph_hunter.analyze("pau1_smith", "paul_smith"))
    add("homoglyph_hunter", "Cyrillic o + combining acute in Latin handle", "perturbed", lambda r: homoglyph_hunter.analyze("pо́stmaster"))
    add("homoglyph_hunter", "combining acute after leading Cyrillic a", "perturbed", lambda r: homoglyph_hunter.analyze("а́pple"))
    add("homoglyph_hunter", "combining acute vs plain reference", "perturbed", lambda r: homoglyph_hunter.analyze("josé", "jose"))
    add("homoglyph_hunter", "bidi override", "perturbed", lambda r: homoglyph_hunter.analyze("admin‮gnp.exe"))
    add("homoglyph_hunter", "empty identifier", "abstain", lambda r: homoglyph_hunter.analyze(""))

    # perceptual_hash
    add("perceptual_hash", "authorized reuse, identical", "benign", lambda r: (lambda i: perceptual_hash.analyze(i, i))(natural_image(r)))
    add("perceptual_hash", "reuse, brightness +20", "perturbed", lambda r: (lambda i: perceptual_hash.analyze(np.clip(i + 20, 0, 255), i))(natural_image(r)))
    add("perceptual_hash", "reuse, 16-level quantization", "perturbed", lambda r: (lambda i: perceptual_hash.analyze(quantize(i, 16), i))(natural_image(r)))
    add("perceptual_hash", "reuse, 8x8 block flattening", "perturbed", lambda r: (lambda i: perceptual_hash.analyze(block_quantize(i), i))(natural_image(r)))
    add("perceptual_hash", "reuse, 2x resampled", "perturbed", lambda r: (lambda i: perceptual_hash.analyze(nearest_upsample(i), i))(natural_image(r)))
    add("perceptual_hash", "reuse, 5% border crop", "perturbed", lambda r: (lambda i: perceptual_hash.analyze(i[6:-6, 6:-6], i))(natural_image(r)))
    add("perceptual_hash", "reuse, noise sd 8", "perturbed", lambda r: (lambda i: perceptual_hash.analyze(np.clip(i + r.normal(0, 8, i.shape), 0, 255), i))(natural_image(r)))
    add("perceptual_hash", "unrelated images", "perturbed", lambda r: perceptual_hash.analyze(natural_image(r), natural_image(r)))
    add("perceptual_hash", "no reference", "abstain", lambda r: perceptual_hash.analyze(natural_image(r)))
    add("perceptual_hash", "constant reference", "abstain", lambda r: perceptual_hash.analyze(natural_image(r), np.full((64, 64), 128.0)))

    # canary_tripwire (dictionary interface)
    def canary(r, transform):
        token = r.bytes(16).hex()
        marked = canary_tripwire.generate(BUSINESS[:200], token)
        return canary_tripwire.detect(transform(marked["text"]), token)
    zero_width = dict.fromkeys(map(ord, "​‌‍⁣"))
    add("canary_tripwire", "unmarked text", "benign", lambda r: canary_tripwire.detect(BUSINESS, r.bytes(16).hex()))
    add("canary_tripwire", "verbatim copy", "perturbed", lambda r: canary(r, lambda t: t))
    add("canary_tripwire", "copy with edits around marker", "perturbed", lambda r: canary(r, lambda t: "Reposted: " + t.upper()[:50] + t[200:] + " #bio"))
    add("canary_tripwire", "platform strips zero-width", "perturbed", lambda r: canary(r, lambda t: t.translate(zero_width)))
    add("canary_tripwire", "marker truncated by length limit", "perturbed", lambda r: canary(r, lambda t: t[:-40]))

    # environmental_acoustic
    for rt60, room in ((0.3, "office"), (0.8, "conference hall"), (1.5, "studio")):
        kind = "perturbed" if room == "studio" else "benign"
        add("environmental_acoustic", f"RT60 {rt60} s declared {room}", kind,
            lambda r, t=rt60, room=room: environmental_acoustic.analyze(impulse_response(r, t), RATE, room))
    for noise_db in (-60, -45, -30):
        add("environmental_acoustic", f"RT60 0.8 s, tail noise {noise_db} dB", "perturbed",
            lambda r, n=noise_db: environmental_acoustic.analyze(impulse_response(r, 0.8, noise_db=n), RATE, "conference hall"))
    add("environmental_acoustic", "RT60 0.8 s truncated at 0.25 s", "perturbed",
        lambda r: environmental_acoustic.analyze(impulse_response(r, 0.8)[:4000], RATE, "conference hall"))
    add("environmental_acoustic", "speech submitted as IR", "abstain", lambda r: environmental_acoustic.analyze(speech_like(r), RATE, "office"))
    add("environmental_acoustic", "silent response", "abstain", lambda r: environmental_acoustic.analyze(np.zeros(RATE), RATE))

    # rppg
    add("rppg", "1.2 Hz pulse", "benign", lambda r: rppg.analyze(roi_trace(r)))
    add("rppg", "1.2 Hz pulse at 10 samples/s", "perturbed", lambda r: rppg.analyze(roi_trace(r, rate=10), 10))
    add("rppg", "pulse + strong shared illumination", "perturbed", lambda r: rppg.analyze(roi_trace(r, illumination=3.0)))
    add("rppg", "shared illumination only", "perturbed", lambda r: rppg.analyze(roi_trace(r, pulse=0.0, illumination=3.0)))
    add("rppg", "pulse drifts 1.0 -> 1.8 Hz", "perturbed", lambda r: rppg.analyze(np.vstack([
        roi_trace(r, seconds=6, pulse_hz=1.0), roi_trace(r, seconds=6, pulse_hz=1.8)])))
    add("rppg", "noise only", "perturbed", lambda r: rppg.analyze(roi_trace(r, pulse=0.0)))
    add("rppg", "6 s trace", "abstain", lambda r: rppg.analyze(roi_trace(r, seconds=6)))
    return c


def observe(control, seed):
    """Run one control on one seed and flatten the result into a comparable record."""
    outcome = control.run(np.random.default_rng(seed))
    if isinstance(outcome, dict):  # canary dictionary interface
        return {"score": float(outcome["tripwireTriggered"]), "uncertainty": 0.0, "evaluated": True, "metrics": outcome}
    return {"score": outcome.score, "uncertainty": outcome.uncertainty,
            "evaluated": bool(outcome.metrics.get("evaluated", True)), "metrics": outcome.metrics,
            "findings": outcome.findings}


def bench(seeds=range(20)):
    records = defaultdict(list)
    for control in controls():
        for seed in seeds:
            records[control].append(observe(control, seed))
    return records


def markdown(records):
    lines = ["| Module | Control | Kind | Evaluated | Score min / median / max | Uncertainty median |",
             "| --- | --- | --- | ---: | --- | ---: |"]
    for control, runs in records.items():
        scores = np.array([run["score"] for run in runs])
        evaluated = sum(run["evaluated"] for run in runs)
        uncertainty = float(np.median([run["uncertainty"] for run in runs]))
        lines.append(f"| {control.module} | {control.name} | {control.kind} | {evaluated}/{len(runs)} | "
                     f"{scores.min():.2f} / {np.median(scores):.2f} / {scores.max():.2f} | {uncertainty:.2f} |")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=20)
    print(markdown(bench(range(parser.parse_args().seeds))))
