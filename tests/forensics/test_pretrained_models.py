"""Optional pretrained-model extractors: contract, abstention and (when installed) behaviour.

The unavailable path runs everywhere. Model-backed checks skip unless PyTorch,
transformers and the pinned weights are installed locally; they assert JSON
safety, bounds and direction, not accuracy (see VALIDATION.md for the labelled
comparison).
"""

from dataclasses import asdict
import json

import numpy as np
import pytest

from backend.app.forensics import ai_image_classifier, ai_text_classifier, model_store

AI_EMAIL = ("Hi Priya, I hope this message finds you well. I wanted to follow up on our conversation from last week "
            "regarding the quarterly budget review. As discussed, the finance team has identified several areas where we "
            "can streamline operational costs without compromising on quality. I have attached a detailed breakdown of the "
            "proposed adjustments for your review. Please let me know if you have any questions or would like to schedule "
            "a call to discuss the next steps. I look forward to hearing from you. Best regards, Arjun")
HUMAN_NOTE = ("ok so the meeting got pushed again lol. dave says thursday but i think he means friday?? anyway i grabbed "
              "the slides from last time, the numbers on page 4 are still wrong btw, somebody needs to fix that before "
              "the client sees it. also who took my charger from the desk, not cool. call me if anything changes, i'm "
              "stuck in traffic for another 20 min at least")


def _json_safe(measured):
    json.dumps(asdict(measured), allow_nan=False)
    assert 0 <= measured.score <= 1 and 0 <= measured.uncertainty <= 1


@pytest.fixture
def disabled(monkeypatch):
    monkeypatch.setenv("TRUSTGUARD_ML", "0")
    model_store.load.cache_clear()
    yield
    model_store.load.cache_clear()


def test_disabled_models_abstain_without_scoring(disabled):
    for measured in (ai_text_classifier.analyze(AI_EMAIL), ai_image_classifier.analyze(np.random.default_rng(0).random((64, 64)) * 255)):
        _json_safe(measured)
        assert not measured.metrics["evaluated"] and measured.metrics["modelAvailable"] is False
        assert measured.score == 0 and measured.uncertainty == 1
        assert "TRUSTGUARD_ML=0" in measured.findings[0]


@pytest.mark.parametrize("text", ["", "Send the money now.", "one two three " * 7])
def test_text_under_25_words_abstains_before_loading_a_model(text):
    measured = ai_text_classifier.analyze(text)
    assert not measured.metrics["evaluated"] and measured.uncertainty == 1


def test_non_english_text_abstains():
    measured = ai_text_classifier.analyze("कृपया रिपोर्ट को गुरुवार से पहले टीम के साथ साझा करें ताकि हम योजना बैठक में इस पर चर्चा कर सकें " * 3)
    assert not measured.metrics["evaluated"] and "English" in measured.findings[0]


@pytest.mark.parametrize("pixels", [np.full((64, 64), 128.0), np.random.default_rng(1).random((20, 20)) * 255])
def test_constant_or_tiny_frames_abstain(pixels):
    measured = ai_image_classifier.analyze(pixels)
    assert not measured.metrics["evaluated"] and measured.uncertainty == 1


@pytest.mark.parametrize("call", [
    lambda: ai_text_classifier.analyze("x" * 20001),
    lambda: ai_image_classifier.analyze(np.zeros((300, 300))),
    lambda: ai_image_classifier.analyze([[float("nan")] * 64] * 64),
    lambda: ai_image_classifier.analyze(np.full((64, 64), 300.0)),
])
def test_unbounded_or_invalid_inputs_are_rejected(call):
    with pytest.raises(ValueError):
        call()


text_model = pytest.mark.skipif(not model_store.available("ai_text"), reason="AI-text model not installed locally")
image_model = pytest.mark.skipif(not model_store.available("ai_image"), reason="AI-image model not installed locally")


@text_model
def test_text_model_separates_a_templated_ai_email_from_a_casual_human_note():
    ai, human = ai_text_classifier.analyze(AI_EMAIL), ai_text_classifier.analyze(HUMAN_NOTE)
    for measured in (ai, human):
        _json_safe(measured)
        assert measured.metrics["evaluated"] and "not deception" in measured.findings[1]
    assert ai.score > human.score


@text_model
def test_text_mid_range_or_mid_length_output_stays_low_confidence():
    measured = ai_text_classifier.analyze(" ".join(AI_EMAIL.split()[:30]))
    assert measured.metrics["evaluated"] and measured.uncertainty >= 0.7


@image_model
def test_image_model_scores_colour_and_grayscale_with_higher_grayscale_uncertainty():
    rng = np.random.default_rng(2)
    base = np.clip(np.cumsum(rng.normal(0, 6, (128, 128, 3)), axis=0) + 128, 0, 255)
    colour, gray = ai_image_classifier.analyze(base), ai_image_classifier.analyze(base.mean(axis=2))
    for measured in (colour, gray):
        _json_safe(measured)
        assert measured.metrics["evaluated"]
    assert colour.metrics["colourAvailable"] and not gray.metrics["colourAvailable"]
    # At 128 px, colour uncertainty is at most 0.6 while grayscale is at least 0.65.
    assert gray.uncertainty > colour.uncertainty
    assert "grayscale" in " ".join(gray.findings).lower()


def _p95_ms(call, repeats=30):
    from time import perf_counter
    for _ in range(2):
        call()
    durations = []
    for _ in range(repeats):
        start = perf_counter()
        call()
        durations.append((perf_counter() - start) * 1000)
    return float(np.percentile(durations, 95)), max(durations)


@pytest.mark.performance
@text_model
def test_text_model_meets_the_150ms_extractor_target_at_512_tokens():
    p95, peak = _p95_ms(lambda: ai_text_classifier.analyze(AI_EMAIL * 6))
    print(f"ai_text_classifier: p95={p95:.1f}ms max={peak:.1f}ms")
    assert p95 < 150


@pytest.mark.performance
@image_model
def test_image_model_meets_its_separate_250ms_model_budget():
    # The Swin-v2 model measured median ~161 ms, p95 <=184 ms over five runs on an Apple M4 CPU; smaller inputs, int8 and half
    # precision were slower or less accurate (VALIDATION.md). Proposal ML-1 records this budget.
    frame = np.random.default_rng(3).random((256, 256, 3)) * 255
    p95, peak = _p95_ms(lambda: ai_image_classifier.analyze(frame))
    print(f"ai_image_classifier: p95={p95:.1f}ms max={peak:.1f}ms")
    assert p95 < 250


@image_model
@text_model
def test_concurrent_first_requests_load_each_model_once_without_errors():
    # Reproduces a live failure: the Chrome extension and the dashboard hit the API at start-up,
    # two threads raced transformers' lazy imports and one request returned HTTP 500.
    from concurrent.futures import ThreadPoolExecutor
    model_store.load.cache_clear()
    frame = np.random.default_rng(4).random((96, 96, 3)) * 255
    calls = [lambda: ai_image_classifier.analyze(frame), lambda: ai_text_classifier.analyze(AI_EMAIL)] * 4
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda call: call(), calls))
    assert all(r.metrics["evaluated"] for r in results)
    assert model_store.load("ai_text") is model_store.load("ai_text")


def test_unexpected_load_errors_abstain_instead_of_raising(monkeypatch):
    model_store.load.cache_clear()
    monkeypatch.setattr(model_store, "dependencies_installed", lambda: True)
    monkeypatch.setattr(model_store, "_load", lambda kind: (_ for _ in ()).throw(AttributeError("lazy import race")))
    measured = ai_image_classifier.analyze(np.random.default_rng(5).random((64, 64)) * 255)
    assert not measured.metrics["evaluated"] and measured.metrics["modelAvailable"] is False
    assert "AttributeError" in measured.findings[0]
    model_store.load.cache_clear()
