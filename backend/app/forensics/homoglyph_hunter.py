"""Offline TR39 confusable mappings with a conservative identifier risk policy.

The full Unicode 17.0.0 mapping table is vendored under data/. Skeleton mapping
uses NFD, one table mapping, then NFD. Comparison additionally case-folds handles.
Mixed-script *risk* uses Latin/Cyrillic/Greek character names per identifier token;
it is not a full UTS #39 restriction-level or Script_Extensions implementation.
Multilingual prose and non-Latin names are not intrinsically suspicious.
"""

from functools import lru_cache
from pathlib import Path
from time import perf_counter
import unicodedata

from .common import bounded_text, result


@lru_cache(maxsize=1)
def _mappings():
    mappings = {}
    path = Path(__file__).with_name("data") / "confusables-17.0.0.txt"
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("#", 1)[0].split(";")
        if len(fields) >= 2:
            source = "".join(chr(int(point, 16)) for point in fields[0].split())
            target = "".join(chr(int(point, 16)) for point in fields[1].split())
            mappings[source] = target
    return mappings


def skeleton(text):
    """Return the TR39 table skeleton; caller chooses identifier case policy."""
    mappings = _mappings()
    return unicodedata.normalize("NFD", "".join(mappings.get(char, char) for char in unicodedata.normalize("NFD", bounded_text(text))))


def _tokens(text):
    """Identifier tokens; combining marks (category M) stay attached to their base letter.

    `\\w` excludes combining marks, so "а́pple" used to split into "а" + "pple"
    and hide the Latin/Cyrillic mix.
    """
    token = []
    for char in text:
        category = unicodedata.category(char)
        if category[0] in "LMN" or category == "Pc":
            token.append(char)
        elif token:
            yield "".join(token)
            token = []
    if token:
        yield "".join(token)


@lru_cache(maxsize=4096)
def _script(char):
    name = unicodedata.name(char, "")
    for script in ("LATIN", "CYRILLIC", "GREEK"):
        if script in name:
            return script
    return "OTHER" if char.isalpha() else "COMMON"


def analyze(text, reference=None):
    """Flag mixed-script identifiers or collisions with a supplied reference."""
    start = perf_counter()
    text = bounded_text(text)
    if reference is not None:
        bounded_text(reference, "reference")
    if not text:
        return result("homoglyph_hunter", start, findings=["No identifier was provided."], metrics={"evaluated": False})
    table = _mappings()
    candidate_chars = []
    for index, char in enumerate(text):
        mapped = table.get(char)
        if ord(char) > 127 and mapped and mapped != char and any("LATIN" in unicodedata.name(c, "") for c in mapped):
            candidate_chars.append({"index": index, "character": char,
                "codePoint": f"U+{ord(char):04X}", "looksLike": mapped, "script": _script(char)})
    mixed_tokens = []
    for token in _tokens(text):
        scripts = {_script(char) for char in token if char.isalpha()}
        if "LATIN" in scripts and scripts.intersection({"CYRILLIC", "GREEK"}):
            if any(ord(char) > 127 and char in table and any("LATIN" in unicodedata.name(c, "") for c in table[char]) for char in token):
                mixed_tokens.append(token)
    candidate_skeleton = skeleton(text.casefold())
    reference_skeleton = skeleton(reference.casefold()) if reference is not None else None
    collision = reference is not None and candidate_skeleton == reference_skeleton and unicodedata.normalize("NFC", text.casefold()) != unicodedata.normalize("NFC", reference.casefold())
    bidi_controls = sum(char in "\u202a\u202b\u202c\u202d\u202e" for char in text)
    score = 0.9 if collision else 0.65 if mixed_tokens else 0.45 if bidi_controls else 0.0
    findings = []
    if collision:
        findings.append("The identifier differs from the reference but has the same Unicode confusable skeleton.")
    if mixed_tokens:
        findings.append("An identifier token mixes Latin letters with Cyrillic/Greek lookalikes.")
    if bidi_controls:
        findings.append("Directional formatting controls can alter the identifier's visible reading order.")
    if not findings:
        findings.append("No mixed-script lookalike token or reference collision was established.")
    findings.append("A lookalike spelling is a review cue; multilingual names and legitimate aliases require independent identity verification.")
    return result("homoglyph_hunter", start, score, 0.15 if reference is not None else 0.35, findings, {
        "evaluated": True, "unicodeVersion": "17.0.0", "skeleton": candidate_skeleton,
        "referenceSkeleton": reference_skeleton, "referenceCollision": bool(collision),
        "mixedScriptTokens": mixed_tokens[:50], "confusables": candidate_chars[:80],
        "confusableCount": len(candidate_chars), "bidiControlCount": bidi_controls,
    })
