"""AK-1 perturbation bench: seeded synthetic controls, observed invariants and known gaps.

The controls live in tests/forensics/fixtures/controls.py; distributions are recorded
in backend/app/forensics/VALIDATION.md. Strict xfail tests are reproduced AK-2 issues:
they fail loudly once fixed so the marker is removed with the fix.
"""

from dataclasses import asdict
import json

import numpy as np
import pytest

from backend.app.forensics import (
    audio_vocoder, cross_modal_sync, homoglyph_hunter, spatial_fft, stylometry_drift,
)
from backend.app.forensics.common import ForensicResult
from tests.forensics.fixtures import controls as bench

SEEDS = range(8)
CONTROLS = {(c.module, c.name): c for c in bench.controls()}
MODULES = {"spatial_fft", "audio_vocoder", "stylometry_drift", "cross_modal_sync", "homoglyph_hunter",
           "perceptual_hash", "canary_tripwire", "environmental_acoustic", "rppg"}


def runs(module, name, seeds=SEEDS):
    return [bench.observe(CONTROLS[module, name], seed) for seed in seeds]


def raw(module, name, seed=0):
    return CONTROLS[module, name].run(np.random.default_rng(seed))


def test_bench_covers_all_nine_modules_with_benign_perturbed_and_abstaining_controls():
    kinds = {}
    for control in CONTROLS.values():
        kinds.setdefault(control.module, set()).add(control.kind)
    assert set(kinds) == MODULES
    for module, present in kinds.items():
        expected = {"benign", "perturbed"} if module == "canary_tripwire" else {"benign", "perturbed", "abstain"}
        assert expected <= present, module


@pytest.mark.parametrize("key", list(CONTROLS), ids=" / ".join)
def test_every_control_is_bounded_json_safe_and_seed_deterministic(key):
    control = CONTROLS[key]
    first, again = control.run(np.random.default_rng(3)), control.run(np.random.default_rng(3))
    if isinstance(first, ForensicResult):
        assert 0 <= first.score <= 1 and 0 <= first.uncertainty <= 1
        json.dumps(asdict(first), allow_nan=False)
        assert {**asdict(first), "elapsed_ms": 0} == {**asdict(again), "elapsed_ms": 0}
        if first.metrics.get("evaluated", True):
            # A measurement always carries its limitation / benign explanation.
            assert len(first.findings) >= 2
    else:
        json.dumps(first, allow_nan=False)
        assert first == again


@pytest.mark.parametrize("key", [k for k, c in CONTROLS.items() if c.kind == "abstain"], ids=" / ".join)
def test_abstaining_controls_never_score(key):
    for run in runs(*key):
        assert not run["evaluated"]
        assert run["score"] == 0 and run["uncertainty"] == 1


# ------------------------------------------------------------------ spatial_fft

def test_spatial_input_scale_does_not_change_the_measurement():
    for seed in SEEDS:
        a, b = raw("spatial_fft", "natural texture", seed), raw("spatial_fft", "natural texture, normalized 0-1 input", seed)
        assert a.score == b.score and a.metrics["spectralPeakRatio"] == b.metrics["spectralPeakRatio"]


@pytest.mark.parametrize("name", ["natural texture", "quantized to 16 levels", "2x stride + nearest upsample",
                                  "8x8 block flattening", "additive sensor noise sd 8"])
def test_spatial_ordinary_processing_stays_below_the_review_finding(name):
    assert max(run["score"] for run in runs("spatial_fft", name)) < 0.35


def test_spatial_periodic_grid_is_flagged_with_benign_alternatives():
    for seed in SEEDS:
        measured = raw("spatial_fft", "checkerboard amplitude 12", seed)
        assert measured.score >= 0.35
        assert "resampling and compression" in " ".join(measured.findings)


def test_spatial_near_constant_dither_is_low_confidence():
    # Scores reach ~0.37 on some seeds; the low-contrast uncertainty is what keeps it neutral.
    for run in runs("spatial_fft", "near-constant frame, +/-1 level dither", range(20)):
        assert run["uncertainty"] >= 0.75 and run["score"] < 0.45


# ------------------------------------------------------------------ audio_vocoder

def test_audio_amplitude_scale_does_not_change_the_measurement():
    for seed in SEEDS:
        a, b = raw("audio_vocoder", "speech-like tone", seed), raw("audio_vocoder", "speech-like tone, scaled x0.05", seed)
        assert a.score == b.score and a.metrics["phaseDiscontinuityRate"] == b.metrics["phaseDiscontinuityRate"]


@pytest.mark.parametrize("name", ["speech-like tone", "resampled 16k->8k->16k", "native 8 kHz", "8-bit quantization",
                                  "three 100 ms low-noise gates"])
def test_audio_resampling_quantization_and_noise_floors_are_not_flagged(name):
    for run in runs("audio_vocoder", name):
        assert run["score"] < 0.3
        assert run["metrics"]["briefDigitalSilenceGaps"] == 0


def test_audio_exact_zero_gates_are_counted_but_valid_gating_remains_an_explanation():
    for run in runs("audio_vocoder", "three 100 ms exact-zero gates"):
        assert run["metrics"]["briefDigitalSilenceGaps"] == 3
        assert run["score"] >= 0.3 and run["uncertainty"] >= 0.45
        assert "codecs and edits" in " ".join(run["findings"])


def test_audio_phase_scrambling_raises_the_phase_rate_directionally():
    for seed in SEEDS:
        clean = raw("audio_vocoder", "speech-like tone", seed).metrics["phaseDiscontinuityRate"]
        scrambled = raw("audio_vocoder", "STFT phase scrambled", seed).metrics["phaseDiscontinuityRate"]
        assert scrambled > clean


@pytest.mark.xfail(strict=True, reason="AK-2: near-silent dither is peak-normalized and evaluated as ordinary audio")
def test_audio_near_silent_dither_is_not_treated_as_ordinary_audio():
    measured = audio_vocoder.analyze(np.random.default_rng(0).normal(0, 1e-5, 3 * bench.RATE))
    assert not measured.metrics["evaluated"] or measured.uncertainty >= 0.7


# ------------------------------------------------------------------ stylometry_drift

def test_stylometry_uncertainty_falls_as_text_grows():
    uncertainty = [raw("stylometry_drift", f"first {n} words").uncertainty for n in (5, 15, 40)]
    uncertainty.append(raw("stylometry_drift", "business text").uncertainty)
    assert uncertainty == sorted(uncertainty, reverse=True) and uncertainty[0] > uncertainty[-1]


def test_stylometry_short_text_skips_baseline_comparison():
    measured = raw("stylometry_drift", "20 words vs baseline (too short)")
    assert not measured.metrics["baselineCompared"] and measured.uncertainty >= 0.8


def test_stylometry_topic_shift_drifts_more_than_same_author_but_stays_context():
    same = raw("stylometry_drift", "business text vs same baseline").metrics["styleDrift"]
    shifted = raw("stylometry_drift", "topic shift vs baseline")
    assert shifted.metrics["styleDrift"] > same
    assert "topic shifts" in " ".join(shifted.findings)


def test_stylometry_coercion_cues_and_non_english_coverage():
    urgent = raw("stylometry_drift", "urgency + payment + bypass")
    assert {"urgency", "payment", "verification_bypass"} <= set(urgent.metrics["urgencyCategories"])
    hindi = raw("stylometry_drift", "Hindi request")
    assert hindi.score == 0 and hindi.uncertainty == 1
    assert "limited coverage" in " ".join(hindi.findings)


# ------------------------------------------------------------------ cross_modal_sync

@pytest.mark.parametrize("name,lag", [("mouth lag +0 ms", 0), ("mouth lag +200 ms", 200), ("mouth lag -200 ms", -200)])
def test_sync_recovers_lag_sign_under_noise(name, lag):
    for run in runs("cross_modal_sync", name):
        assert run["metrics"]["lagMs"] == lag
        assert run["metrics"]["correlation"] > 0.9


@pytest.mark.parametrize("name", ["lag beyond +/-600 ms search", "independent noise traces"])
def test_sync_unrecoverable_offsets_do_not_score(name):
    for run in runs("cross_modal_sync", name):
        assert run["score"] == 0 and run["uncertainty"] >= 0.9


@pytest.mark.xfail(strict=True, reason="AK-2: a periodic trace's +300 ms lag is reported as a confident -200 ms")
def test_sync_ambiguous_periodic_peaks_are_not_reported_confidently():
    measured = raw("cross_modal_sync", "periodic 2 Hz traces, 300 ms lag")
    assert measured.metrics["lagMs"] > 0 or measured.uncertainty >= 0.65


# ------------------------------------------------------------------ homoglyph_hunter

@pytest.mark.parametrize("name", ["Latin handle", "Cyrillic name", "Greek name", "Devanagari name",
                                  "separate-language tokens", "Latin with combining acute", "same handle as reference",
                                  "combining acute vs plain reference"])
def test_homoglyph_multilingual_and_accented_names_are_not_flagged(name):
    assert raw("homoglyph_hunter", name).score == 0


@pytest.mark.parametrize("name,minimum", [("Cyrillic a in Latin handle", 0.65), ("Cyrillic a vs reference", 0.9),
                                          ("l->1 digit swap vs reference", 0.9), ("bidi override", 0.45),
                                          ("Cyrillic o + combining acute in Latin handle", 0.65)])
def test_homoglyph_lookalikes_are_flagged(name, minimum):
    assert raw("homoglyph_hunter", name).score >= minimum


@pytest.mark.xfail(strict=True, reason="AK-2: a combining mark after a Cyrillic lookalike splits the identifier token")
def test_homoglyph_combining_mark_does_not_hide_a_mixed_script_token():
    assert homoglyph_hunter.analyze("а́pple").score >= 0.65


# ------------------------------------------------------------------ perceptual_hash

@pytest.mark.parametrize("name", ["authorized reuse, identical", "reuse, brightness +20", "reuse, 16-level quantization",
                                  "reuse, 8x8 block flattening", "reuse, 2x resampled", "reuse, noise sd 8"])
def test_phash_survives_photometric_and_resampling_edits(name):
    for run in runs("perceptual_hash", name):
        assert run["metrics"]["matched"] and run["metrics"]["hammingDistance"] <= 6
        assert "may be authorized" in " ".join(run["findings"])


def test_phash_unrelated_images_are_well_separated():
    assert min(run["metrics"]["hammingDistance"] for run in runs("perceptual_hash", "unrelated images")) > 12


def test_phash_border_crop_is_a_documented_miss():
    distances = [run["metrics"]["hammingDistance"] for run in runs("perceptual_hash", "reuse, 5% border crop")]
    assert max(distances) > 6  # recorded limitation: cropping defeats a global DCT hash


# ------------------------------------------------------------------ canary_tripwire

@pytest.mark.parametrize("name,triggered", [("unmarked text", False), ("verbatim copy", True),
                                            ("copy with edits around marker", True),
                                            ("platform strips zero-width", False),
                                            ("marker truncated by length limit", False)])
def test_canary_survives_surrounding_edits_but_not_stripping(name, triggered):
    for run in runs("canary_tripwire", name):
        assert run["metrics"]["tripwireTriggered"] is triggered
        if not triggered:
            assert "absence does not rule out copying" in run["metrics"]["explanation"]


# ------------------------------------------------------------------ environmental_acoustic

@pytest.mark.parametrize("name,rt60,tolerance", [("RT60 0.3 s declared office", 0.3, 0.05),
                                                 ("RT60 0.8 s declared conference hall", 0.8, 0.05),
                                                 ("RT60 1.5 s declared studio", 1.5, 0.05),
                                                 ("RT60 0.8 s, tail noise -60 dB", 0.8, 0.05),
                                                 ("RT60 0.8 s, tail noise -45 dB", 0.8, 0.10)])
def test_rt60_recovers_known_decay_until_tail_noise_dominates(name, rt60, tolerance):
    for run in runs("environmental_acoustic", name):
        assert abs(run["metrics"]["rt60Sec"] - rt60) <= rt60 * tolerance


@pytest.mark.parametrize("name", ["RT60 0.8 s, tail noise -30 dB", "RT60 0.8 s truncated at 0.25 s"])
def test_rt60_noisy_or_truncated_tails_abstain(name):
    assert not any(run["evaluated"] for run in runs("environmental_acoustic", name))


def test_rt60_room_mismatch_is_bounded_context():
    for run in runs("environmental_acoustic", "RT60 1.5 s declared studio"):
        assert run["score"] <= 0.6 and run["uncertainty"] >= 0.55
        assert "cannot establish dubbing" in " ".join(run["findings"])


# ------------------------------------------------------------------ rppg

@pytest.mark.parametrize("name", ["1.2 Hz pulse", "1.2 Hz pulse at 10 samples/s"])
def test_rppg_recovers_pulse_frequency_without_liveness_claim(name):
    for run in runs("rppg", name):
        assert abs(run["metrics"]["pulseFrequencyHz"] - 1.2) <= 0.1
        assert run["score"] == 0 and run["metrics"]["biologicalLivenessEstablished"] is False


@pytest.mark.parametrize("name", ["shared illumination only", "pulse drifts 1.0 -> 1.8 Hz", "noise only"])
def test_rppg_illumination_drift_and_noise_abstain(name):
    assert not any(run["evaluated"] for run in runs("rppg", name))


def test_rppg_shared_illumination_rarely_masks_a_real_component():
    evaluated = [run["evaluated"] for run in runs("rppg", "pulse + strong shared illumination", range(20))]
    assert sum(evaluated) >= 18
