"""Controlled decay and color traces test conditional environmental measurements."""

from dataclasses import asdict
import json
from time import perf_counter

import numpy as np
import pytest

from backend.app.forensics import environmental_acoustic, rppg


def _impulse(rt60=0.55, duration=1.0):
    time_axis = np.arange(int(16000 * duration)) / 16000
    # Squared amplitude decays by 60dB at rt60; deterministic dense reflections.
    return np.exp(-3 * np.log(10) * time_axis / rt60) * np.cos(time_axis * 2 * np.pi * 1337)


def _rgb(duration=12, frequency=1.2):
    t = np.arange(int(duration * 25)) / 25
    pulse = np.sin(2 * np.pi * frequency * t)
    return np.column_stack([np.full(len(t), 145.0), 105 + pulse, np.full(len(t), 80.0)])


def test_schroeder_rt60_recovers_known_exponential_decay():
    measured = environmental_acoustic.analyze(_impulse(), claimed_environment="office")
    assert measured.metrics["evaluated"]
    assert abs(measured.metrics["rt60Sec"] - 0.55) < 0.025
    assert measured.metrics["decayFitR2"] > 0.98
    assert measured.metrics["matchScore"] == 1
    assert measured.uncertainty >= 0.55
    assert "cannot establish dubbing" in " ".join(measured.findings)


def test_room_mismatch_is_a_bounded_conditional_cue():
    measured = environmental_acoustic.analyze(_impulse(rt60=0.12), claimed_environment="airport")
    assert measured.metrics["evaluated"]
    assert measured.metrics["matchScore"] < 0.3
    assert 0 < measured.score <= 0.6
    outdoors = environmental_acoustic.analyze(_impulse(), claimed_environment="outdoors")
    assert outdoors.metrics["rt60Sec"] is not None
    assert outdoors.metrics["matchScore"] is None


@pytest.mark.parametrize("signal", [[], np.zeros(16000), np.ones(16000), np.r_[1, np.zeros(15999)], np.random.default_rng(5).uniform(-0.5, 0.5, 16000)])
def test_inadequate_room_decay_abstains(signal):
    measured = environmental_acoustic.analyze(signal)
    assert not measured.metrics["evaluated"]
    assert measured.metrics["rt60Sec"] is None
    assert measured.uncertainty == 1


def test_periodic_chrominance_is_reported_without_liveness_claim():
    measured = rppg.analyze(_rgb())
    assert measured.metrics["evaluated"]
    assert abs(measured.metrics["pulseFrequencyHz"] - 1.2) < 0.1
    assert measured.metrics["pulseRegularity"] > 0.7
    assert measured.metrics["biologicalLivenessEstablished"] is False
    assert measured.score == 0
    assert measured.uncertainty >= 0.65


@pytest.mark.parametrize("trace", [[], np.ones((300, 3)), _rgb(duration=4), np.random.default_rng(4).uniform(80, 160, (1500, 3))])
def test_missing_short_constant_and_noise_roi_traces_abstain(trace):
    measured = rppg.analyze(trace)
    assert not measured.metrics["evaluated"]
    assert measured.uncertainty == 1
    assert measured.score == 0


def test_global_illumination_and_shifting_frequency_do_not_pass_pulse_check():
    t = np.arange(400) / 25
    light = 1 + 0.01 * np.sin(2 * np.pi * 1.2 * t)
    shared = light[:, None] * np.array([140, 110, 80])[None, :]
    assert not rppg.analyze(shared).metrics["evaluated"]
    varying = np.concatenate([_rgb(8, 0.8), _rgb(8, 2.5)])
    assert not rppg.analyze(varying).metrics["evaluated"]


@pytest.mark.parametrize("call", [
    lambda: environmental_acoustic.analyze([float("nan")] * 16000),
    lambda: environmental_acoustic.analyze([2] * 16000),
    lambda: environmental_acoustic.analyze([0] * 96001),
    lambda: environmental_acoustic.analyze(_impulse(), sample_rate=0),
    lambda: rppg.analyze([[1, 2]] * 300),
    lambda: rppg.analyze([[1, 2, float("inf")]] * 300),
    lambda: rppg.analyze([[1, 2, 256]] * 300),
    lambda: rppg.analyze(_rgb(), sample_rate=0),
])
def test_invalid_environmental_inputs_rejected(call):
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize("name,call", [
    ("environmental_acoustic", lambda: environmental_acoustic.analyze(_impulse(duration=6).tolist())),
    ("rppg", lambda: rppg.analyze(_rgb(duration=60).tolist())),
])
@pytest.mark.performance
def test_optional_measurements_are_json_safe_and_bounded_under_150ms(name, call):
    call()
    elapsed = []
    for _ in range(8):
        start = perf_counter()
        measured = call()
        elapsed.append((perf_counter() - start) * 1000)
        json.dumps(asdict(measured), allow_nan=False)
    print(f"{name}: max={max(elapsed):.2f}ms")
    assert max(elapsed) < 150
