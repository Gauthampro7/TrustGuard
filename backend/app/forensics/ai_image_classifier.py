"""Pretrained AI-generated-image classifier (Swin-v2); an uncalibrated cue, never provenance proof.

Model: haywoodsloan/ai-image-detector-deploy (Apache-2.0), loaded locally by
model_store. Screenshots, graphics, heavy filters and unseen generators can be
misclassified. The API currently sends reduced grayscale frames; colour input
(HxWx3) is used when supplied and was markedly more accurate in validation.
"""

from time import perf_counter

import numpy as np

from . import model_store
from .common import finite_array, grayscale, result

MIN_SIDE = 32


def _rgb(image_pixels):
    """Return uint8 HxWx3, whether colour was supplied, and the validated grayscale frame."""
    gray = grayscale(image_pixels)  # shared validation: shape, <=256x256, value range
    pixels = finite_array(image_pixels, "image_pixels", limit=256 * 256 * 4)
    if pixels.ndim == 3:
        rgb = pixels[:, :, :3] * (255 if pixels.max() <= 1 else 1)
        return np.clip(rgb, 0, 255).astype(np.uint8), True, gray
    return np.repeat((gray * 255)[:, :, None], 3, axis=2).astype(np.uint8), False, gray


def _tensor(rgb, config):
    """Apply the model's own ViT preprocessing (resize, rescale, normalize) without torchvision."""
    import torch
    from PIL import Image

    size = config["size"]
    resample = {2: Image.Resampling.BILINEAR, 3: Image.Resampling.BICUBIC}.get(config.get("resample"), Image.Resampling.BICUBIC)
    resized = np.asarray(Image.fromarray(rgb).resize((size["width"], size["height"]), resample), dtype=np.float32)
    normalized = (resized * config["rescale_factor"] - np.asarray(config["image_mean"], dtype=np.float32)) / np.asarray(config["image_std"], dtype=np.float32)
    return torch.from_numpy(np.ascontiguousarray(normalized.transpose(2, 0, 1)[None]))


def analyze(image_pixels):
    """Score one <=256x256 frame; abstain when unavailable, tiny or constant."""
    start = perf_counter()
    rgb, colour, gray = _rgb(image_pixels)
    base = {"evaluated": False, "model": model_store.MODELS["ai_image"]["repo"], "colourAvailable": colour,
            "width": int(gray.shape[1]) if gray.ndim == 2 else 0, "height": int(gray.shape[0]) if gray.ndim == 2 else 0}
    if gray.size == 0 or min(gray.shape) < MIN_SIDE or float(gray.std()) < 1e-3:
        return result("ai_image_classifier", start, findings=[
            "The frame is too small or too uniform for the image classifier."], metrics=base)
    try:
        config, model = model_store.load("ai_image")
    except LookupError as error:
        return result("ai_image_classifier", start, findings=[str(error)], metrics={**base, "modelAvailable": False})
    import torch

    with torch.inference_mode():  # per call: API requests run on worker threads
        probabilities = torch.softmax(model(pixel_values=_tensor(rgb, config)).logits, dim=-1)[0]
    artificial = float(probabilities[model.config.label2id["artificial"]])
    # Validation: colour frames were far more reliable than grayscale; mid-range outputs are least usable.
    decisive = artificial >= 0.9 or artificial <= 0.1
    uncertainty = min(0.9, (0.4 if decisive else 0.6) + (0.25 if not colour else 0) + (0.1 if min(gray.shape) < 96 else 0))
    findings = [
        f"A pretrained AI-image classifier {'leans generated' if artificial >= 0.5 else 'leans camera-captured'} "
        f"for this {gray.shape[1]}x{gray.shape[0]} frame.",
        "Screenshots, graphics, strong filters and unseen generators can be misclassified; a generated image is not proof of deception.",
    ]
    if not colour:
        findings.append("Only grayscale pixels were supplied; colour cues were unavailable, which lowered accuracy in validation.")
    return result("ai_image_classifier", start, artificial, uncertainty, findings,
                  {**base, "evaluated": True, "modelAvailable": True, "aiImageModelScore": round(artificial, 6)})
