"""Warmed bounded-input CPU latency target; timings describe this host only."""

from time import perf_counter

import numpy as np
import pytest

from backend.app.forensics import (
    audio_vocoder, canary_tripwire, cross_modal_sync, homoglyph_hunter,
    perceptual_hash, spatial_fft, stylometry_drift,
)


def _workloads():
    rng = np.random.default_rng(52)
    image = rng.random((256, 256, 3)).tolist()
    audio = rng.normal(0, 0.1, 96000).tolist()
    trace = rng.random(1500).tolist()
    text = ("The report is with our team and we will review the evidence. " * 400)[:20000]
    identifier = ("a\u0430 " * 6666)[:20000]
    marked = canary_tripwire.generate("A" * 19800)
    return {
        "spatial_fft": lambda: spatial_fft.analyze(image),
        "audio_vocoder": lambda: audio_vocoder.analyze(audio),
        "stylometry_drift": lambda: stylometry_drift.analyze(text, text),
        "cross_modal_sync": lambda: cross_modal_sync.analyze(trace, trace),
        "homoglyph_hunter": lambda: homoglyph_hunter.analyze(identifier, identifier),
        "perceptual_hash": lambda: perceptual_hash.analyze(image, image),
        "canary_tripwire": lambda: canary_tripwire.detect(marked["text"], marked["token"]),
    }


@pytest.mark.parametrize("name", list(_workloads()))
def test_warmed_extractor_under_150ms(name):
    workload = _workloads()[name]
    workload()
    durations = []
    for _ in range(8):
        start = perf_counter()
        workload()
        durations.append((perf_counter() - start) * 1000)
    p95 = float(np.percentile(durations, 95))
    print(f"{name}: median={np.median(durations):.2f}ms p95={p95:.2f}ms max={max(durations):.2f}ms")
    assert p95 < 150, f"{name} warm p95 {p95:.1f}ms exceeded 150ms on bounded inputs"
