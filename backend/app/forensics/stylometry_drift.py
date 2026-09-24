"""Interpretable English lexical features; no authorship or LLM attribution."""

from collections import Counter
import re
from time import perf_counter

import numpy as np

from .common import bounded_text, result

FUNCTION_WORDS = frozenset("a an the and or but if then of to in on at for from by with as is are was were be been being it its this that these those i me my we our you your he she they their not do does did can will would should".split())
URGENCY_PATTERNS = {
    "urgency": r"\b(?:urgent|urgently|immediately|asap|right now|within \d+ minutes|today only)\b",
    "payment": r"\b(?:wire|transfer|payment|bank account|gift card|crypto|send money)\b",
    "secrecy": r"\b(?:confidential|secret|do not tell|don't tell|keep this between|discreet)\b",
    "verification_bypass": r"\b(?:don't call|do not call|skip approval|bypass|no time to verify|ignore (?:the )?policy)\b",
}


def _features(text):
    words = re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", text.casefold(), flags=re.UNICODE)
    counts = Counter(words)
    total = len(words)
    # K = 10^4 * (sum_i i^2 V_i - N) / N^2, with V_i frequency-of-frequency.
    yules_k = 10000 * (sum(count * count for count in counts.values()) - total) / (total * total) if total else 0.0
    function = {word: counts[word] / total for word in sorted(FUNCTION_WORDS)} if total else {}
    sentences = [part for part in re.split(r"[.!?]+", text) if part.strip()]
    return total, yules_k, function, total / max(1, len(sentences))


def analyze(text, baseline_text=None):
    """Compare supplied writing only; sparse text and language mismatch abstain."""
    start = perf_counter()
    text = bounded_text(text)
    if baseline_text is not None:
        bounded_text(baseline_text, "baseline_text")
    total, yules, function, sentence_length = _features(text)
    if total == 0:
        return result("stylometry_drift", start, findings=["No words were available for lexical analysis."], metrics={"evaluated": False, "tokenCount": 0})
    categories = [name for name, pattern in URGENCY_PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]
    urgency = min(1.0, 0.2 * len(categories) + 0.2 * ("payment" in categories and "verification_bypass" in categories))
    drift = None
    baseline_count = 0
    if baseline_text is not None:
        baseline_count, base_yules, base_function, _ = _features(baseline_text)
        if total >= 30 and baseline_count >= 30:
            frequency_delta = sum(abs(function[word] - base_function[word]) for word in FUNCTION_WORDS) / 2
            k_delta = abs(yules - base_yules) / max(100, abs(base_yules), abs(yules))
            drift = float(np.clip(0.65 * frequency_delta + 0.35 * k_delta, 0, 1))
    ascii_words = re.findall(r"\b[a-zA-Z]+\b", text)
    english_coverage = min(1.0, len(ascii_words) / total)
    uncertainty = max(0.35, 1 - min(total, 120) / 160, 1 - english_coverage)
    if baseline_text is not None and drift is None:
        uncertainty = max(uncertainty, 0.8)
    score = max(urgency * 0.85, drift or 0)
    findings = [
        "Payment pressure and verification bypass language require an independent callback." if "payment" in categories and "verification_bypass" in categories
        else "Urgency and coercion vocabulary were measured as context, not authorship evidence.",
        "Writing style comparison requires an adequate, language-matched baseline; edits and topic shifts can cause drift.",
    ]
    if english_coverage < 0.5:
        findings.append("English function-word and urgency rules have limited coverage for this text's language.")
    return result("stylometry_drift", start, score, uncertainty, findings, {
        "evaluated": True, "tokenCount": total, "yulesK": round(yules, 6),
        "functionWordFrequencies": {word: round(freq, 6) for word, freq in function.items()},
        "meanSentenceLength": round(sentence_length, 6), "urgencyScore": round(urgency, 6),
        "urgencyCategories": categories, "baselineTokenCount": baseline_count,
        "baselineCompared": drift is not None, "styleDrift": None if drift is None else round(drift, 6),
    })
