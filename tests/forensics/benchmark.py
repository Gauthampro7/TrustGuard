"""AK-3 bounded laptop benchmark for every forensic extractor.

Each workload is the largest input the v1 extractor accepts, shaped so the
extractor fully evaluates instead of abstaining early. Inputs are Python lists,
as the API delivers them, so list-to-array conversion counts as extractor time.
Fixture construction happens before timing.

Warmed timings run in this process. Cold costs are measured in a fresh
subprocess per workload and split into: shared NumPy import, detector module
import, fixture construction and the first call (which fills lazy caches such
as the Unicode confusables table).

    python -m tests.forensics.benchmark                 # markdown tables
    python -m tests.forensics.benchmark --repeats 100 --json
"""

import argparse
import gc
import importlib
import json
import os
import platform
import statistics
import subprocess
import sys
from time import perf_counter

TARGET_MS = 150
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _np():
    import numpy
    return numpy


def _speech(rate, samples):
    np = _np()
    t = np.arange(samples) / rate
    phase = 2 * np.pi * np.cumsum(120 + 20 * np.sin(2 * np.pi * 0.7 * t)) / rate
    voiced = sum(np.sin(k * phase) / k for k in range(1, 9))
    signal = voiced * (0.55 + 0.45 * np.sin(2 * np.pi * 4 * t)) + np.random.default_rng(1).normal(0, 0.02, samples)
    return (signal / np.max(np.abs(signal)) * 0.8).tolist()


def _envelopes(rate):
    np = _np()
    rng = np.random.default_rng(3)
    bursts = np.zeros(1500)
    positions = np.cumsum(rng.integers(3, 9, size=1500))
    bursts[positions[positions < 1500]] = 1.0
    audio = np.convolve(bursts, np.exp(-np.arange(6) / 1.5))[:1500] + 0.02
    return audio.tolist(), np.roll(audio, 5).tolist(), rate


def _impulse():
    np = _np()
    t = np.arange(96000) / 16000
    decay = np.random.default_rng(4).normal(0, 1, t.size) * 10 ** (-3 * t / 1.5)
    decay[0] = 1.0
    return (decay / np.max(np.abs(decay))).tolist(), 16000, "conference hall"


def _roi(rate):
    np = _np()
    t = np.arange(1500) / rate
    wave = np.sin(2 * np.pi * 1.2 * t)
    trace = np.array([150.0, 110.0, 90.0]) + 0.6 * wave[:, None] * np.array([0.3, 1.0, 0.2])
    return (trace + np.random.default_rng(5).normal(0, 0.15, trace.shape)).tolist(), rate


def _rgba():
    return _np().random.default_rng(6).integers(0, 256, (256, 256, 4)).astype(float).tolist()


def _text():
    return ("The report is with our team and we will review the evidence. " * 400)[:20000]


def _canary_text():
    module = importlib.import_module("backend.app.forensics.canary_tripwire")
    marked = module.generate("A" * (20000 - 160), "benchmark-token-0001")
    return marked["text"], "benchmark-token-0001"


# name -> (module, function, fixture builder returning positional args, bound description)
WORKLOADS = {
    "spatial_fft": ("spatial_fft", "analyze", lambda: (_rgba(),), "256x256 RGBA list"),
    "audio_vocoder@16k": ("audio_vocoder", "analyze", lambda: (_speech(16000, 96000), 16000), "96,000 samples, 16 kHz"),
    "audio_vocoder@48k": ("audio_vocoder", "analyze", lambda: (_speech(48000, 96000), 48000), "96,000 samples, 48 kHz"),
    "stylometry_drift": ("stylometry_drift", "analyze", lambda: (_text(), _text()), "20,000 chars + 20,000-char baseline"),
    "cross_modal_sync@25": ("cross_modal_sync", "analyze", lambda: _envelopes(25), "1,500 paired samples, 25/s"),
    "cross_modal_sync@120": ("cross_modal_sync", "analyze", lambda: _envelopes(120), "1,500 paired samples, 120/s (widest lag search)"),
    "homoglyph_hunter": ("homoglyph_hunter", "analyze", lambda: (("aа́ " * 5000)[:20000], ("aа́ " * 5000)[:20000]),
                         "20,000 adversarial chars + reference"),
    "perceptual_hash": ("perceptual_hash", "analyze", lambda: (_rgba(), _rgba()), "two 256x256 RGBA lists"),
    "canary_tripwire.detect": ("canary_tripwire", "detect", _canary_text, "20,000 chars"),
    "canary_tripwire.generate": ("canary_tripwire", "generate", lambda: ("A" * 19800, "benchmark-token-0001"), "19,800 chars"),
    "environmental_acoustic": ("environmental_acoustic", "analyze", _impulse, "96,000-sample measured IR, 16 kHz"),
    "rppg@25": ("rppg", "analyze", lambda: _roi(25), "1,500 RGB means, 25/s (60 s)"),
    "rppg@120": ("rppg", "analyze", lambda: _roi(120), "1,500 RGB means, 120/s (12.5 s)"),
}


def _evaluated(outcome):
    metrics = getattr(outcome, "metrics", None)
    return True if metrics is None else bool(metrics.get("evaluated", True))


def call_for(name):
    """Return (zero-argument call, bound description); fixtures are built here, outside timing."""
    module, function, build, bound = WORKLOADS[name]
    target = getattr(importlib.import_module(f"backend.app.forensics.{module}"), function)
    args = build()
    return (lambda: target(*args)), bound


def warmed(name, repeats=50, warmups=3):
    call, bound = call_for(name)
    for _ in range(warmups):
        outcome = call()
    if not _evaluated(outcome):
        raise AssertionError(f"{name} abstained; the workload does not exercise the full extractor")
    durations = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(repeats):
            start = perf_counter()
            call()
            durations.append((perf_counter() - start) * 1000)
    finally:
        if gc_was_enabled:
            gc.enable()
    durations.sort()
    return {"name": name, "bound": bound, "repeats": repeats, "medianMs": statistics.median(durations),
            "p95Ms": durations[max(0, round(0.95 * repeats) - 1)], "maxMs": durations[-1]}


def _cold_child(name):
    start = perf_counter()
    _np()
    numpy_ms = (perf_counter() - start) * 1000
    module, function, build, _ = WORKLOADS[name]
    start = perf_counter()
    target = getattr(importlib.import_module(f"backend.app.forensics.{module}"), function)
    import_ms = (perf_counter() - start) * 1000
    start = perf_counter()
    args = build()
    fixture_ms = (perf_counter() - start) * 1000
    start = perf_counter()
    target(*args)
    first_ms = (perf_counter() - start) * 1000
    print(json.dumps({"name": name, "numpyImportMs": numpy_ms, "moduleImportMs": import_ms,
                      "fixtureMs": fixture_ms, "firstCallMs": first_ms}))


def cold(name):
    output = subprocess.run([sys.executable, "-m", "tests.forensics.benchmark", "--cold-child", name],
                            cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return json.loads(output.strip().splitlines()[-1])


def host():
    np = _np()
    cpu = platform.processor() or platform.machine()
    if sys.platform == "darwin":
        try:
            cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    return {"cpu": cpu, "platform": platform.platform(), "python": platform.python_version(), "numpy": np.__version__}


def markdown(report):
    info = report["host"]
    lines = [f"Host: {info['cpu']} · {info['platform']} · Python {info['python']} · NumPy {info['numpy']} · "
             f"{report['repeats']} warmed calls after 3 warm-ups, GC paused during timing.", "",
             "| Extractor workload | Bound exercised | Median ms | p95 ms | Max ms | < 150 ms |",
             "| --- | --- | ---: | ---: | ---: | :---: |"]
    for row in report["warmed"]:
        lines.append(f"| {row['name']} | {row['bound']} | {row['medianMs']:.2f} | {row['p95Ms']:.2f} | {row['maxMs']:.2f} | "
                     f"{'yes' if row['maxMs'] < TARGET_MS else 'NO'} |")
    lines += ["", "| Extractor workload | NumPy import ms | Module import ms | Fixture build ms | First call ms |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for row in report["cold"]:
        lines.append(f"| {row['name']} | {row['numpyImportMs']:.1f} | {row['moduleImportMs']:.1f} | "
                     f"{row['fixtureMs']:.1f} | {row['firstCallMs']:.1f} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--cold-child", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.cold_child:
        _cold_child(args.cold_child)
        return
    report = {"host": host(), "repeats": args.repeats,
              "warmed": [warmed(name, args.repeats) for name in WORKLOADS],
              "cold": [cold(name) for name in WORKLOADS]}
    print(json.dumps(report, indent=2) if args.json else markdown(report))


if __name__ == "__main__":
    main()
