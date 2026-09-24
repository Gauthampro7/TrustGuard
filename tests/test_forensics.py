"""Scientific edge cases and explicit limitations for local forensic heuristics."""

from dataclasses import asdict
import json

import numpy as np
import pytest

from backend.app.forensics import (
    audio_vocoder, canary_tripwire, cross_modal_sync, homoglyph_hunter,
    perceptual_hash, spatial_fft, stylometry_drift,
)


@pytest.mark.parametrize("values", [[], np.zeros((32, 32)), np.ones((32, 32, 3)), np.ones((8, 8))])
def test_spatial_insufficient_data_abstains(values):
    measured = spatial_fft.analyze(values)
    assert measured.score == 0
    assert measured.uncertainty == 1
    assert not measured.metrics["evaluated"]


def test_spatial_periodic_texture_is_detected_but_not_called_synthetic():
    periodic = np.indices((128, 128)).sum(axis=0) % 2
    natural_noise = np.random.default_rng(10).random((128, 128))
    artifact = spatial_fft.analyze(periodic)
    control = spatial_fft.analyze(natural_noise)
    assert artifact.score > control.score + 0.4
    assert artifact.metrics["highFrequencyPowerRatio"] > 0.9
    assert "does not identify AI generation" in " ".join(artifact.findings)
    assert artifact.uncertainty >= 0.3


@pytest.mark.parametrize("values", [[], [0] * 16000, [1] * 16000, [0.5] * 100])
def test_audio_silence_constant_and_short_clips_abstain(values):
    measured = audio_vocoder.analyze(values)
    assert measured.score == 0
    assert measured.uncertainty == 1
    assert not measured.metrics["evaluated"]


def test_audio_exact_gating_has_more_silence_evidence_than_continuous_signal():
    samples = np.sin(np.arange(48000) * 2 * np.pi * 440 / 16000)
    gated = samples.copy()
    for start in (8000, 16000, 24000):
        gated[start:start + 1600] = 0
    clean = audio_vocoder.analyze(samples)
    measured = audio_vocoder.analyze(gated)
    assert measured.metrics["briefDigitalSilenceGaps"] == 3
    assert measured.score > clean.score
    assert measured.uncertainty >= 0.4
    assert "codecs" in " ".join(measured.findings)


def test_yules_k_and_baseline_comparison_have_expected_math():
    assert stylometry_drift.analyze("cat cat dog dog").metrics["yulesK"] == 2500
    baseline = "The report is in the archive and we will review it with the team. " * 12
    same = stylometry_drift.analyze(baseline, baseline)
    assert same.metrics["baselineCompared"]
    assert same.metrics["styleDrift"] == 0
    short = stylometry_drift.analyze("Please review.", baseline)
    assert short.metrics["styleDrift"] is None
    assert short.uncertainty >= 0.8


def test_urgency_is_context_and_never_authorship_proof():
    message = "Urgent wire transfer immediately. Do not call. Keep this confidential."
    measured = stylometry_drift.analyze(message)
    assert measured.metrics["urgencyScore"] == 1
    assert set(measured.metrics["urgencyCategories"]) == {"urgency", "payment", "secrecy", "verification_bypass"}
    assert measured.metrics["styleDrift"] is None
    assert measured.uncertainty > 0.8
    assert stylometry_drift.analyze("").uncertainty == 1


def test_sync_recovers_known_lag_with_correct_sign():
    audio = np.random.default_rng(30).random(250)
    aligned = cross_modal_sync.analyze(audio, audio)
    lagged = cross_modal_sync.analyze(audio, np.r_[np.zeros(8), audio[:-8]])
    ahead = cross_modal_sync.analyze(audio, np.r_[audio[5:], np.zeros(5)])
    assert aligned.metrics["lagMs"] == 0
    assert aligned.score == 0
    assert lagged.metrics["lagMs"] == 320
    assert ahead.metrics["lagMs"] == -200
    assert lagged.metrics["correlation"] > 0.99
    assert lagged.score > aligned.score


@pytest.mark.parametrize("left,right", [([], []), ([1] * 100, [1] * 100), ([1, 2], [2, 1])])
def test_sync_constant_or_short_traces_abstain(left, right):
    assert cross_modal_sync.analyze(left, right).uncertainty == 1


def test_sync_independent_noise_does_not_prove_desynchronization():
    rng = np.random.default_rng(2)
    measured = cross_modal_sync.analyze(rng.random(1500), rng.random(1500))
    assert measured.score == 0
    assert measured.uncertainty >= 0.9


def test_tr39_cyrillic_collision_and_single_script_reference_collision():
    measured = homoglyph_hunter.analyze("r\u0430jesh_cfo", "rajesh_cfo")
    assert measured.metrics["referenceCollision"]
    assert measured.metrics["confusables"][0]["codePoint"] == "U+0430"
    assert measured.metrics["skeleton"] == "rajesh_cfo"
    assert homoglyph_hunter.analyze("\u0440\u0430\u0443", "pay").metrics["referenceCollision"]
    assert homoglyph_hunter.analyze("modern", "modem").metrics["referenceCollision"]


@pytest.mark.parametrize("text", ["rajesh_cfo", "\u041c\u0430\u0440\u0438\u044f", "\u0928\u092e\u0938\u094d\u0924\u0947", "Maria \u041c\u0430\u0440\u0438\u044f", "caf\u00e9", "\u03b1\u03b2\u03b3"])
def test_legitimate_scripts_and_separate_language_tokens_are_not_flagged(text):
    measured = homoglyph_hunter.analyze(text)
    assert measured.score == 0
    assert not measured.metrics["mixedScriptTokens"]


def test_same_reference_is_not_a_collision_and_normalization_is_canonical():
    assert not homoglyph_hunter.analyze("\u041c\u0430\u0440\u0438\u044f", "\u041c\u0430\u0440\u0438\u044f").metrics["referenceCollision"]
    assert not homoglyph_hunter.analyze("cafe\u0301", "caf\u00e9").metrics["referenceCollision"]


def test_canary_exact_registration_and_removal_semantics():
    generated = canary_tripwire.generate("Public biography", "registered-demo-token")
    assert generated["text"].startswith("Public biography")
    found = canary_tripwire.detect(generated["text"], generated["token"])
    assert found["tripwireTriggered"] and found["occurrenceCount"] == 1
    assert found["tokenId"] == generated["tokenId"]
    assert not canary_tripwire.detect(generated["text"], "different-demo-token")["tripwireTriggered"]
    assert not canary_tripwire.detect("Public biography", generated["token"])["tripwireTriggered"]
    assert "not who copied" in found["explanation"]
    assert canary_tripwire.generate("Bio")["token"] != canary_tripwire.generate("Bio")["token"]


def test_phash_matches_brightness_changes_without_claiming_biometric_identity():
    image = np.random.default_rng(11).random((64, 64)) * 0.5 + 0.1
    measured = perceptual_hash.analyze(image, image + 0.1)
    assert measured.metrics["matched"]
    assert measured.metrics["hammingDistance"] <= 2
    assert perceptual_hash.hamming_distance("0000000000000000", "ffffffffffffffff") == 64
    assert not perceptual_hash.analyze(np.ones((64, 64)), image).metrics["evaluated"]
    assert not perceptual_hash.analyze(image).metrics["evaluated"]
    assert "not face recognition" in " ".join(measured.findings)


@pytest.mark.parametrize("call", [
    lambda: spatial_fft.analyze([[float("nan")]]),
    lambda: spatial_fft.analyze(np.zeros((257, 16))),
    lambda: spatial_fft.analyze([[1, 2], [3]]),
    lambda: spatial_fft.analyze(np.full((32, 32), -1)),
    lambda: audio_vocoder.analyze([float("inf")] * 1024),
    lambda: audio_vocoder.analyze(np.zeros(96001)),
    lambda: audio_vocoder.analyze(np.zeros(1000), sample_rate=0),
    lambda: cross_modal_sync.analyze([0, 1], [0]),
    lambda: cross_modal_sync.analyze([-1] * 100, [1] * 100),
    lambda: cross_modal_sync.analyze([float("nan")] * 100, [1] * 100),
    lambda: stylometry_drift.analyze("x" * 20001),
    lambda: homoglyph_hunter.analyze(None),
    lambda: canary_tripwire.generate("Bio", ""),
    lambda: perceptual_hash.hamming_distance("invalid", "0000000000000000"),
])
def test_malformed_nonfinite_and_unbounded_inputs_rejected(call):
    with pytest.raises(ValueError):
        call()


def test_results_are_strict_json_serializable():
    image = np.random.default_rng(3).random((32, 32))
    trace = np.random.default_rng(4).random(100)
    results = [spatial_fft.analyze(image), audio_vocoder.analyze(np.sin(np.arange(16000) * 0.2)),
        stylometry_drift.analyze("Please review the report."), cross_modal_sync.analyze(trace, trace),
        homoglyph_hunter.analyze("r\u0430jesh"), perceptual_hash.analyze(image, image)]
    for measured in results:
        json.dumps(asdict(measured), allow_nan=False)
        assert 0 <= measured.score <= 1
        assert 0 <= measured.uncertainty <= 1
        assert measured.elapsed_ms >= 0
