"""User-owned, offline copy markers. A copied marker is not actor attribution."""

import hashlib
import secrets

from .common import bounded_text

WARNING = "Platforms may strip invisible markers. A match shows marker reuse, not who copied it or whether a model was involved. Keep the registration token private."


def _marker(token):
    if not isinstance(token, str) or not 8 <= len(token) <= 128:
        raise ValueError("token must be a private string between 8 and 128 characters")
    digest = hashlib.sha256(("TrustGuard-canary-v1:" + token).encode("utf-8")).digest()[:16]
    bits = "".join(f"{byte:08b}" for byte in digest)
    marker = "\u2063\u200b\u2063" + "".join("\u200c" if bit == "0" else "\u200d" for bit in bits) + "\u2063\u200b\u2063"
    token_id = hashlib.sha256(("TrustGuard-id-v1:" + token).encode("utf-8")).hexdigest()[:16]
    return marker, token_id


def generate(text, token=None):
    """Return {text, token, marker, tokenId, warning}; nothing is persisted.

    Detection requires this exact private token. Supplying a token is useful for
    deterministic demonstrations; generated defaults have 128 random bits.
    """
    text = bounded_text(text)
    token = secrets.token_hex(16) if token is None else token
    marker, token_id = _marker(token)
    if len(text) + len(marker) > 20000:
        raise ValueError("Bio plus marker exceeds the 20000-character extraction limit")
    return {"text": text + marker, "token": token, "marker": marker, "tokenId": token_id, "warning": WARNING}


def detect(text, registered_token):
    """Return {tripwireTriggered, tokenId, occurrenceCount, explanation}."""
    text = bounded_text(text)
    marker, token_id = _marker(registered_token)
    count = text.count(marker)
    return {"tripwireTriggered": count > 0, "tokenId": token_id,
        "occurrenceCount": count, "explanation": (
            "Exact registered copy marker found. Independently verify whether this reuse is authorized. " if count
            else "Registered marker not found; absence does not rule out copying. "
        ) + WARNING}
