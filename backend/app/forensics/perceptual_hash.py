"""Local DCT perceptual hashes for coarse image reuse, never face recognition."""

from time import perf_counter
import re

import numpy as np

from .common import grayscale, result

_POSITIONS = np.arange(32) + 0.5
_DCT_BASIS = np.cos(np.pi / 32 * np.arange(8)[:, None] * _POSITIONS)
_DCT_BASIS[0] *= 1 / np.sqrt(2)


def _hash(gray):
    y, x = np.linspace(0, gray.shape[0] - 1, 32), np.linspace(0, gray.shape[1] - 1, 32)
    y0, x0 = y.astype(int), x.astype(int)
    y1, x1 = np.minimum(y0 + 1, gray.shape[0] - 1), np.minimum(x0 + 1, gray.shape[1] - 1)
    dy, dx = (y - y0)[:, None], (x - x0)[None, :]
    resized = (gray[y0[:, None], x0] * (1-dy) * (1-dx) + gray[y1[:, None], x0] * dy * (1-dx)
        + gray[y0[:, None], x1] * (1-dy) * dx + gray[y1[:, None], x1] * dy * dx)
    # Center before DCT to make brightness shifts numerically stable.
    low = _DCT_BASIS @ (resized - resized.mean()) @ _DCT_BASIS.T
    coefficients = low.ravel()
    coefficients[0] = 0
    bits = coefficients > np.median(coefficients[1:])
    bits[0] = False
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def hash_image(image_pixels):
    gray = grayscale(image_pixels)
    if gray.size == 0 or min(gray.shape) < 8 or float(gray.std()) < 1e-5:
        raise ValueError("Perceptual hashing needs a nonconstant image at least 8x8")
    return _hash(gray)


def hamming_distance(left, right):
    if not all(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{16}", value) for value in (left, right)):
        raise ValueError("Hashes must contain exactly 16 hexadecimal characters")
    return (int(left, 16) ^ int(right, 16)).bit_count()


def analyze(image_pixels, reference_pixels=None):
    start = perf_counter()
    gray = grayscale(image_pixels)
    if gray.size == 0 or min(gray.shape) < 8 or float(gray.std()) < 1e-5:
        return result("perceptual_hash", start, findings=["Insufficient image texture for a meaningful perceptual hash."], metrics={"evaluated": False})
    image_hash = _hash(gray)
    if reference_pixels is None:
        return result("perceptual_hash", start, findings=["No reference image was supplied; image reuse is undetermined."], metrics={"evaluated": False, "hash": image_hash})
    reference = grayscale(reference_pixels)
    if reference.size == 0 or min(reference.shape) < 8 or float(reference.std()) < 1e-5:
        return result("perceptual_hash", start, findings=["The reference image lacks sufficient texture for comparison."], metrics={"evaluated": False})
    reference_hash = _hash(reference)
    distance = hamming_distance(image_hash, reference_hash)
    matched = distance <= 6
    similarity = 1 - distance / 63
    return result("perceptual_hash", start, 0.75 if matched else 0.0, 0.35, [
        "The image closely matches the supplied reference under a 63-bit DCT perceptual hash." if matched
        else "The supplied image and reference do not show a close DCT perceptual hash match.",
        "Avatar reuse may be authorized; pHash is not face recognition and is not collision-resistant."
    ], {"evaluated": True, "hash": image_hash, "referenceHash": reference_hash,
        "hammingDistance": distance, "similarity": round(similarity, 6), "matched": matched})
