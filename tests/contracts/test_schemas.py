"""
Unit tests validating TrustGuard data contracts against OPENSPEC.md specification.
Ensures schemas can parse, serialize, and validate inspection requests and verdicts.
"""

import pytest
from backend.app.models.schemas import (
    TrustGuardInspectionRequest,
    TrustGuardInspectionVerdict,
    TrustGuardIdentityBaseline,
    SourceChannel,
    ModalityType,
    AssessmentTier,
    TrustVector,
    VerdictSummary,
    LedgerEvidenceItem,
    ForensicLayer,
    EvidencePolarity,
    PlaybookStep,
    PlaybookStatus,
    ProfileEvaluationRequest,
    ProfileEvaluationResponse,
)


def test_inspection_request_validation():
    """Verify TrustGuardInspectionRequest conforms to OPENSPEC Section 2."""
    raw_payload = {
        "requestId": "req_tg_test_001",
        "timestamp": "2026-09-24T20:00:00Z",
        "sourceChannel": "web_portal",
        "claimedIdentity": {
            "canonicalUserId": "user_123",
            "entityName": "Rajesh Verma",
            "claimedRole": "CFO",
            "claimedAffiliation": "Apex Infrastructure",
            "referenceHandles": {
                "x_twitter": "rajesh_verma_cfo"
            }
        },
        "evidenceItems": [
            {
                "evidenceId": "ev_01",
                "modality": "video",
                "mediaUri": "https://example.com/video.mp4",
                "metadata": {
                    "c2paPresent": False,
                    "durationSec": 14.5
                }
            },
            {
                "evidenceId": "ev_02",
                "modality": "text",
                "textContent": "Urgent transfer required immediately."
            }
        ]
    }
    
    req = TrustGuardInspectionRequest.model_validate(raw_payload)
    assert req.requestId == "req_tg_test_001"
    assert req.sourceChannel == SourceChannel.WEB_PORTAL
    assert len(req.evidenceItems) == 2
    assert req.evidenceItems[0].modality == ModalityType.VIDEO
    assert req.evidenceItems[1].modality == ModalityType.TEXT


def test_inspection_verdict_validation():
    """Verify TrustGuardInspectionVerdict conforms to OPENSPEC Section 5."""
    raw_verdict = {
        "verdictId": "ver_001",
        "requestId": "req_001",
        "evaluatedAt": "2026-09-24T20:01:00Z",
        "assessmentTier": "HIGH_IMPERSONATION_RISK",
        "calibratedTrustVector": {
            "mediaSynthesisScore": 0.88,
            "crossModalDiscordanceScore": 0.92,
            "identityMismatchScore": 0.85,
            "contextualAnomalyScore": 0.74,
            "epistemicUncertainty": 0.10
        },
        "verdictSummary": {
            "headline": "Severe Acoustic Cloned Impersonation Detected",
            "coreAnomaly": "Phoneme-viseme desynchronization paired with synthetic vocoder spectral phase cuts."
        },
        "evidenceLedger": [
            {
                "signalId": "sig_voice_clone",
                "layer": "media_synthetic",
                "modality": "audio",
                "polarity": "red_flag",
                "confidence": 0.94,
                "finding": "Vocoder phase discontinuity in 4kHz-8kHz frequency band.",
                "affectedSpan": {"startSec": 2.1, "endSec": 8.4}
            }
        ],
        "verificationPlaybook": [
            {
                "step": 1,
                "action": "Secondary Out-of-Band Call",
                "instruction": "Initiate direct phone call on verified internal PBX.",
                "status": "pending_analyst"
            }
        ]
    }
    
    verdict = TrustGuardInspectionVerdict.model_validate(raw_verdict)
    assert verdict.assessmentTier == AssessmentTier.HIGH_IMPERSONATION_RISK
    assert verdict.calibratedTrustVector.mediaSynthesisScore == 0.88
    assert verdict.calibratedTrustVector.epistemicUncertainty == 0.10
    assert len(verdict.evidenceLedger) == 1
    assert verdict.evidenceLedger[0].polarity == EvidencePolarity.RED_FLAG


def test_profile_evaluation_contracts():
    """Verify Chrome Extension profile evaluation request/response."""
    req = ProfileEvaluationRequest(
        platform="twitter",
        handle="rajesh_cfo",
        displayName="Rajesh Verma"
    )
    assert req.platform == "twitter"
    assert req.handle == "rajesh_cfo"

    res = ProfileEvaluationResponse(
        continuousAuthenticityScore=0.14,
        badgeStatus="meter-red",
        label="HIGH_RISK_IMPERSONATOR",
        signals=["Homoglyph spoofing detected."]
    )
    assert res.continuousAuthenticityScore == 0.14
    assert res.badgeStatus == "meter-red"


def test_creative_innovations():
    """Verify Astra Ultra creative extension schemas (Dialectic, Environmental, Canary)."""
    from backend.app.models.schemas import AdversarialDialectic, EnvironmentalForensics, CanaryTripwireAlert

    dialectic = AdversarialDialectic(
        prosecutionArgument="2D-FFT azimuthal roll-off deviates from natural camera optics; vocoder splice present.",
        defenseMitigation="Sensor exhibits severe low-light thermal noise; video underwent WhatsApp H.264 compression.",
        judicialSynthesis="Epistemic uncertainty bounds final suspicion to 0.42. Independent PBX verification required."
    )
    assert "2D-FFT" in dialectic.prosecutionArgument

    env = EnvironmentalForensics(
        reverberationMatchScore=0.12,
        ambientAcousticProfile="Studio Dead Echo (Acoustic Clash with Factory Video)",
        rppgPulseConfidence=0.08
    )
    assert env.reverberationMatchScore == 0.12

    tripwire = CanaryTripwireAlert(
        tripwireTriggered=True,
        tripwireType="linguistic_watermark",
        details="Claimed message contains registered persona honeypot phrase 'in perpetuity of clause 9'."
    )
    assert tripwire.tripwireTriggered is True

