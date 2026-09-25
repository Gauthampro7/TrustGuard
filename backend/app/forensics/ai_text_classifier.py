"""Pretrained AI-generated-text classifier (RoBERTa); an uncalibrated cue, never authorship proof.

Model: fakespot-ai/roberta-base-ai-text-detection-v1 (English, Apache-2.0), loaded
locally by model_store. Short or non-English text is out of scope and abstains or
carries high uncertainty. AI assistance is common in legitimate writing, so a
high score means "review the context", not "deceptive".
"""

import re
from time import perf_counter

from . import model_store
from .common import bounded_text, result

MIN_WORDS = 25
RELIABLE_WORDS = 40
MAX_TOKENS = 512


def _clean(text):
    # The model card's clean_text: collapse whitespace and drop markdown/HTML noise.
    text = re.sub(r"```.*?```|`[^`]*`|!\[.*?\]\(.*?\)|<.*?>", " ", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)
    return re.sub(r"\s+", " ", text).replace(" ,", ",").strip()


def analyze(text):
    """Score <=20,000 characters; abstain when unavailable, too short or not English."""
    start = perf_counter()
    text = bounded_text(text)
    words = re.findall(r"[^\W\d_]+", text)
    english = len(re.findall(r"\b[a-zA-Z]+\b", text)) / max(1, len(words))
    base = {"evaluated": False, "model": model_store.MODELS["ai_text"]["repo"], "wordCount": len(words)}
    if len(words) < MIN_WORDS:
        return result("ai_text_classifier", start, findings=[
            f"Fewer than {MIN_WORDS} words; AI-text classifiers are unreliable on short messages."], metrics=base)
    if english < 0.5:
        return result("ai_text_classifier", start, findings=[
            "The classifier was trained on English; this text is outside its scope."], metrics=base)
    try:
        tokenizer, model = model_store.load("ai_text")
    except LookupError as error:
        return result("ai_text_classifier", start, findings=[str(error)], metrics={**base, "modelAvailable": False})
    import torch

    encoded = tokenizer(_clean(text), truncation=True, max_length=MAX_TOKENS, return_tensors="pt", return_overflowing_tokens=False)
    truncated = int(encoded["input_ids"].shape[1]) >= MAX_TOKENS and len(words) > MAX_TOKENS // 2
    with torch.inference_mode():  # per call: API requests run on worker threads
        probabilities = torch.softmax(model(input_ids=encoded["input_ids"], attention_mask=encoded["attention_mask"]).logits, dim=-1)[0]
    ai = float(probabilities[model.config.label2id["AI"]])
    # Validation on everyday prose (VALIDATION.md): from 40 words up, outputs >=0.95 flagged no human
    # text while catching 8/10 AI texts, so only decisive outputs are usable; 25-39 words stay low-confidence.
    decisive = ai >= 0.95 or ai <= 0.05
    uncertainty = 0.4 if decisive and len(words) >= RELIABLE_WORDS else 0.7
    return result("ai_text_classifier", start, ai, uncertainty, [
        f"A pretrained AI-text classifier {'leans machine-generated' if ai >= 0.5 else 'leans human-written'} for this text "
        f"({len(words)} words{', first 512 tokens' if truncated else ''}).",
        "Editing tools, templates, translation and non-native writing can be misclassified; AI-assisted writing is not deception by itself.",
    ], {**base, "evaluated": True, "modelAvailable": True, "aiTextModelScore": round(ai, 6), "truncated": truncated})
