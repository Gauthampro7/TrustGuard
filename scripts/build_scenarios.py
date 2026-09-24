"""Rebuild deterministic synthetic fixtures; no real face, voice or identity data."""

import json
from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DESTINATION = PROJECT_ROOT / "backend" / "app" / "scenarios"


def build():
    rng = np.random.default_rng(24092026)
    y, x = np.mgrid[:64, :64]
    image = np.clip(110 + 40 * np.sin(x / 14) + 28 * np.cos(y / 11) + rng.normal(0, 2, (64, 64)), 0, 255).astype(int).tolist()
    t = np.arange(16000) / 16000
    voice = 0.45 * np.sin(2 * np.pi * (180 * t + 40 * t * t)) * (0.65 + 0.35 * np.sin(2 * np.pi * 3 * t))
    for start in (2000, 6000, 10000, 13500):
        voice[start:start + 800] = 0
    envelope = np.convolve(rng.uniform(0.05, 1, 150), np.ones(5) / 5, mode="same")
    mouth = np.r_[np.zeros(8), envelope[:-8]]
    ceo_message = (
        "This is Rajesh from the finance office. We need an urgent wire transfer immediately to complete the acquisition payment. "
        "Keep this confidential and do not tell the rest of the team. Do not call me because I am presenting at the conference. "
        "Skip approval and ignore the policy just this once. The replacement bank account will be sent in the next message. "
        "I expect you to send money before the meeting ends. We can finish the paperwork tomorrow and I will explain the exception to the board."
    )
    bio = (
        "Chief Financial Officer at Apex Infrastructure. I share updates about our teams, governance and responsible operations. "
        "Our official announcements are always available through our company communications office. This profile reflects my professional work "
        "and the projects that our colleagues are building together. Please use the company directory for all financial questions and "
        "follow the established approval process for any proposed payment. I look forward to discussing our next public results briefing "
        "and meeting partners at the upcoming industry conference. Views expressed here are my own."
    )
    wifi_message = (
        "Here is the field update from our site visit. The connection was unstable and the video was compressed during upload. "
        "There is no payment request or change to the existing approval process. The original recording is available from our communications "
        "team through the usual company directory. Please compare that original before drawing conclusions about the quality of this copy. "
        "We will send a written summary after the network connection improves. You can also call the office using your existing contact list "
        "if you need to confirm anything discussed in this recording."
    )

    def media(evidence_id, modality, samples, scenario_id, **extra):
        return {"evidenceId": evidence_id, "modality": modality, "samples": samples,
                "metadata": {"extraMetadata": {"fixtureId": scenario_id, **extra}}}

    def text(evidence_id, content, **extra):
        return {"evidenceId": evidence_id, "modality": "text", "textContent": content,
                "metadata": {"extraMetadata": extra}}

    from backend.app.forensics.canary_tripwire import generate as generate_canary
    creator_bio_base = (
        "Digital concept artist and matte painter creating immersive architectural worlds. "
        "Original portfolio works are exhibited exclusively through official verified gallery channels. "
        "I do not solicit direct wire or cryptocurrency deposits on social media feeds. "
        "Always confirm commission availability through signed agency agreements. "
        "All visual rights reserved under digital artist copyright guidelines."
    )
    creator_canary = generate_canary(creator_bio_base, token="creator_canary_token_2026")
    creator_message = (
        creator_canary["text"] + " "
        "Urgent update: Special commission slots open today only with 50% discount! "
        "Please send advance wire payment immediately to complete your reservation. "
        "Skip the gallery booking form and do not message the agency directly as slots are strictly limited."
    )
    art_image = np.clip(120 + 45 * np.sin(x / 8) * np.cos(y / 8) + 35 * np.cos((x + y) / 10), 0, 255).astype(int).tolist()

    cases = [
        ("ceo-wire-scam", "The urgent executive transfer", "A voice-clone narrative with an intact visual channel, synthetic audio gating and delayed mouth traces, plus payment pressure. Signals are generated fixtures, not validated deepfake recordings.", [
            media("conference-frame", "video", {"imagePixels": image, "audioEnvelope": envelope.round(5).tolist(), "mouthAperture": mouth.round(5).tolist(), "envelopeRate": 25}, "ceo-wire-scam"),
            media("gated-speech", "audio", {"audioSamples": voice.round(6).tolist(), "sampleRate": 16000}, "ceo-wire-scam"),
            text("wire-message", ceo_message),
        ], {"entityName": "Rajesh Verma", "claimedRole": "CFO", "claimedAffiliation": "Apex Infrastructure", "referenceHandles": {"x_twitter": "rajesh_verma_cfo"}}),
        ("homoglyph-clone", "One character. A different identity.", "A supplied reference avatar is reused beside a Cyrillic lookalike handle. The pixels are a synthetic texture; the identity and reuse authorization remain unverified.", [
            media("copied-avatar", "image", {"imagePixels": image, "referenceImagePixels": image}, "homoglyph-clone"),
            text("cloned-profile", bio, observedHandle="r\u0430jesh_verma_cfo"),
        ], {"entityName": "Rajesh Verma", "claimedRole": "CFO", "claimedAffiliation": "Apex Infrastructure", "referenceHandles": {"x_twitter": "rajesh_verma_cfo"}}),
        ("creator-copyright", "Creator attribution & canary tripwire", "A stolen digital artwork and bio scraped with an invisible canary marker, soliciting advance payments under a Cyrillic lookalike handle.", [
            media("stolen-artwork", "image", {"imagePixels": art_image, "referenceImagePixels": art_image}, "creator-copyright"),
            text("scraped-creator-profile", creator_message, observedHandle="elena_cr\u0435ative"),
        ], {"entityName": "Elena Rostova", "claimedRole": "Concept Artist", "claimedAffiliation": "Elena Art Studio", "referenceHandles": {"x_twitter": "elena_creative"}}),
        ("wifi-compression-edge-case", "Bad Wi-Fi is not evidence of fraud", "A benign field-update narrative with a degraded synthetic frame and caller-declared transmission loss. High uncertainty must bound suspicion.", [
            media("compressed-frame", "video", {"imagePixels": np.clip(128 + rng.normal(0, 30, (24, 24)), 0, 255).astype(int).tolist()}, "wifi-compression-edge-case", qualityDegradation="0.80"),
            text("field-transcript", wifi_message),
        ], {"entityName": "Rajesh Verma", "claimedRole": "CFO", "claimedAffiliation": "Apex Infrastructure", "referenceHandles": {"x_twitter": "rajesh_verma_cfo"}}),
    ]
    DESTINATION.mkdir(exist_ok=True)
    for scenario_id, title, description, items, identity in cases:
        payload = {"scenarioId": scenario_id, "title": title, "description": description, "simulation": True,
            "request": {"requestId": "fixture_" + scenario_id, "timestamp": "2026-09-24T12:00:00Z",
                "sourceChannel": "web_portal", "claimedIdentity": identity,
                "evidenceItems": items}}
        (DESTINATION / f"{scenario_id}.json").write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
        print(scenario_id)


if __name__ == "__main__":
    build()
