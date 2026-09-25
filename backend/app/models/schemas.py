"""
TrustGuard Core Data Contracts & Pydantic v2 Schemas
Corresponds directly to OPENSPEC.md (Standard: TrustGuard Core v1.0.0)
PS-02 Digital Trust Pipeline: Multi-Modal AI for Digital Trust
"""

from __future__ import annotations
from enum import Enum
from typing import Annotated, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SourceChannel(str, Enum):
    WEB_PORTAL = "web_portal"
    BROWSER_EXTENSION = "browser_extension"
    HEADLESS_API = "headless_api"
    CITIZEN_TIPLINE = "citizen_tipline"


class ModalityType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    DOCUMENT = "document"
    URL = "url"


class AssessmentTier(str, Enum):
    BENIGN_AUTHENTIC = "BENIGN_AUTHENTIC"
    LOW_RISK_VERIFIED = "LOW_RISK_VERIFIED"
    UNCERTAIN_COMPRESSION_NOISE = "UNCERTAIN_COMPRESSION_NOISE"
    SUSPICIOUS_ANOMALY = "SUSPICIOUS_ANOMALY"
    HIGH_IMPERSONATION_RISK = "HIGH_IMPERSONATION_RISK"


class EvidencePolarity(str, Enum):
    RED_FLAG = "red_flag"
    GREEN_FLAG = "green_flag"
    NEUTRAL_UNCERTAIN = "neutral_uncertain"


class ForensicLayer(str, Enum):
    MEDIA_SYNTHETIC = "media_synthetic"
    STYLOMETRY_BEHAVIOR = "stylometry_behavior"
    CROSS_MODAL = "cross_modal"
    CONTEXT_GROUNDING = "context_grounding"
    IDENTITY_CONSISTENCY = "identity_consistency"


class PlaybookStatus(str, Enum):
    PENDING_ANALYST = "pending_analyst"
    CONFIRMED_FRAUD = "confirmed_fraud"
    CONFIRMED_AUTHENTIC = "confirmed_authentic"


# ---------------------------------------------------------------------------
# Ingestion Request Schemas
# ---------------------------------------------------------------------------

class ReferenceHandles(BaseModel):
    x_twitter: Optional[str] = None
    linkedin: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None


class ClaimedIdentity(BaseModel):
    canonicalUserId: Optional[str] = None
    entityName: Optional[str] = None
    claimedRole: Optional[str] = None
    claimedAffiliation: Optional[str] = None
    referenceHandles: Optional[ReferenceHandles] = None


class EvidenceMetadata(BaseModel):
    c2paPresent: Optional[bool] = False
    captureTimestamp: Optional[str] = None
    resolution: Optional[str] = None
    durationSec: Optional[float] = None
    extraMetadata: Optional[Dict[str, str]] = None


FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
Pixel = Annotated[float, Field(ge=0, le=255, allow_inf_nan=False)]
AudioValue = Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)]
PixelRow = Annotated[List[Pixel], Field(min_length=16, max_length=256)]
PixelMatrix = Annotated[List[PixelRow], Field(min_length=16, max_length=256)]


class EvidenceSamples(BaseModel):
    """Bounded, transient samples. Never persisted or fetched from a media URI."""
    model_config = ConfigDict(extra="forbid")
    imagePixels: Optional[PixelMatrix] = None
    referenceImagePixels: Optional[PixelMatrix] = None
    audioSamples: Optional[List[AudioValue]] = Field(None, min_length=800, max_length=96000)
    roomImpulseResponse: Optional[List[AudioValue]] = Field(None, min_length=1024, max_length=96000)
    sampleRate: int = Field(16000, ge=8000, le=48000)
    audioEnvelope: Optional[List[FiniteFloat]] = Field(None, min_length=25, max_length=1500)
    mouthAperture: Optional[List[FiniteFloat]] = Field(None, min_length=25, max_length=1500)
    envelopeRate: float = Field(25, ge=5, le=100, allow_inf_nan=False)
    rgbTrace: Optional[List[Annotated[List[Pixel], Field(min_length=3, max_length=3)]]] = Field(None, min_length=100, max_length=1500)

    @field_validator("imagePixels", "referenceImagePixels")
    @classmethod
    def rectangular_pixels(cls, value):
        if value and len({len(row) for row in value}) != 1:
            raise ValueError("imagePixels must be rectangular")
        return value

    @model_validator(mode="after")
    def paired_traces(self):
        if (self.audioEnvelope is None) != (self.mouthAperture is None):
            raise ValueError("audioEnvelope and mouthAperture must be supplied together")
        if self.audioEnvelope is not None and len(self.audioEnvelope) != len(self.mouthAperture):
            raise ValueError("Synchronized traces must have equal lengths")
        return self


class EvidenceItem(BaseModel):
    evidenceId: str = Field(min_length=1, max_length=100)
    modality: ModalityType
    mediaUri: Optional[str] = Field(None, max_length=2048)
    textContent: Optional[str] = Field(None, max_length=20000)
    metadata: Optional[EvidenceMetadata] = None
    samples: Optional[EvidenceSamples] = None

    @model_validator(mode="after")
    def match_samples_to_modality(self):
        if self.samples:
            visual = any(value is not None for value in (self.samples.imagePixels, self.samples.referenceImagePixels, self.samples.rgbTrace))
            acoustic = any(value is not None for value in (self.samples.audioSamples, self.samples.roomImpulseResponse))
            if visual and self.modality not in {ModalityType.IMAGE, ModalityType.VIDEO}:
                raise ValueError("Visual samples require image or video modality")
            if acoustic and self.modality not in {ModalityType.AUDIO, ModalityType.VIDEO}:
                raise ValueError("Audio samples require audio or video modality")
            if self.samples.audioEnvelope is not None and self.modality != ModalityType.VIDEO:
                raise ValueError("Synchronized mouth/audio traces require video modality")
        return self


class TrustGuardInspectionRequest(BaseModel):
    requestId: str = Field(..., min_length=1, max_length=128, description="Unique inspection request identifier")
    timestamp: str = Field(..., min_length=1, max_length=64, description="ISO 8601 timestamp of inspection request")
    sourceChannel: SourceChannel
    claimedIdentity: Optional[ClaimedIdentity] = None
    evidenceItems: List[EvidenceItem] = Field(..., min_length=1, max_length=8)

    @field_validator("evidenceItems")
    @classmethod
    def unique_evidence(cls, items):
        if len({item.evidenceId for item in items}) != len(items):
            raise ValueError("evidenceId values must be unique")
        return items


# ---------------------------------------------------------------------------
# Canonical Identity Baseline Schemas (Privacy-Preserving Anchor)
# ---------------------------------------------------------------------------

class BiometricAnchor(BaseModel):
    vectorModel: str
    embeddingDim: int
    isNormalizedL2: bool = True
    encryptedVectorCiphertext: str = Field(
        ..., description="Salted, AES-256 encrypted centroid embedding; raw biometrics never stored"
    )


class BiometricAnchors(BaseModel):
    faceCentroid: Optional[BiometricAnchor] = None
    voiceprint: Optional[BiometricAnchor] = None


class StylometricProfile(BaseModel):
    yulesKBaseline: float = Field(..., description="Yule's characteristic K lexical persistence metric")
    meanSentenceLength: float
    topFunctionWordFrequencies: Dict[str, float] = Field(default_factory=dict)
    posTransitionFrequencies: Dict[str, float] = Field(default_factory=dict)


class TrustGuardIdentityBaseline(BaseModel):
    baselineId: str
    enrolledAt: str
    userPseudonym: str
    biometricAnchors: BiometricAnchors
    stylometricProfile: StylometricProfile
    verifiedHandles: Dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Calibrated 5D Trust Vector & Dual-Polarity Ledger Schemas
# ---------------------------------------------------------------------------

class TrustVector(BaseModel):
    mediaSynthesisScore: float = Field(..., ge=0.0, le=1.0, description="Physical/spectral synthesis score [0,1]")
    crossModalDiscordanceScore: float = Field(..., ge=0.0, le=1.0, description="Cross-modal discordance index [0,1]")
    identityMismatchScore: float = Field(..., ge=0.0, le=1.0, description="Impersonation drift vs baseline [0,1]")
    contextualAnomalyScore: float = Field(..., ge=0.0, le=1.0, description="Contextual/historical anomaly score [0,1]")
    epistemicUncertainty: float = Field(..., ge=0.0, le=1.0, description="Quality degradation/uncertainty metric [0,1]")


class VerdictSummary(BaseModel):
    headline: str
    coreAnomaly: str
    noScoreIsProofNotice: str = (
        "Under TrustGuard core architecture, no single score constitutes legal or definitive proof. "
        "Review the calibrated 5D Trust Vector and complete the Human Verification Playbook before taking adverse action."
    )


class AffectedSpan(BaseModel):
    startSec: Optional[float] = None
    endSec: Optional[float] = None


class LedgerEvidenceItem(BaseModel):
    signalId: str
    layer: ForensicLayer
    modality: str
    polarity: EvidencePolarity
    confidence: float = Field(..., ge=0.0, le=1.0)
    finding: str
    affectedSpan: Optional[AffectedSpan] = None


class PlaybookStep(BaseModel):
    step: int
    action: str
    instruction: str
    resourceUri: Optional[str] = None
    status: PlaybookStatus = PlaybookStatus.PENDING_ANALYST


class AdversarialDialectic(BaseModel):
    """Dual-Agent Dialectic: Adversarial debate synthesizing prosecution and defense arguments."""
    prosecutionArgument: str = Field(..., description="Forensic prosecutor argument detailing anomalies and red flags")
    defenseMitigation: str = Field(..., description="Forensic defense advocate highlighting natural compression/sensor noise")
    judicialSynthesis: str = Field(..., description="Balanced judicial ruling justifying the calibrated Trust Vector")


class EnvironmentalForensics(BaseModel):
    """Acoustic and physiological environmental micro-signals."""
    reverberationMatchScore: Optional[float] = Field(None, ge=0.0, le=1.0, description="RT60 acoustic space consistency")
    ambientAcousticProfile: Optional[str] = Field(None, description="e.g. Studio Dead, Open Office, Reverb Hallway")
    rppgPulseConfidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Legacy field name: chrominance periodicity, NOT biological liveness probability")
    rt60Sec: Optional[float] = Field(None, ge=0)
    pulseFrequencyHz: Optional[float] = Field(None, ge=0)
    measurementNotes: Optional[str] = None


class CanaryTripwireAlert(BaseModel):
    """Active deception detection via honeypot tokens and zero-width markers."""
    tripwireTriggered: bool = False
    tripwireType: Optional[str] = None
    details: Optional[str] = None


class TrustGuardInspectionVerdict(BaseModel):
    verdictId: str
    requestId: str
    evaluatedAt: str
    assessmentTier: AssessmentTier
    calibratedTrustVector: TrustVector
    verdictSummary: VerdictSummary
    evidenceLedger: List[LedgerEvidenceItem]
    verificationPlaybook: List[PlaybookStep]
    # Creative & Autonomous Innovation Hooks (Astra Ultra Extensible Fields)
    adversarialDialectic: Optional[AdversarialDialectic] = None
    environmentalForensics: Optional[EnvironmentalForensics] = None
    tripwireStatus: Optional[CanaryTripwireAlert] = None
    innovationMetadata: Optional[Dict[str, str]] = None


# ---------------------------------------------------------------------------
# Chrome Extension In-Feed Evaluation Schemas
# ---------------------------------------------------------------------------

class ProfileEvaluationRequest(BaseModel):
    platform: str = Field(..., max_length=32, description="Platform name e.g. twitter, instagram, linkedin")
    handle: str = Field(min_length=1, max_length=200)
    displayName: str = Field(max_length=300)
    bioText: Optional[str] = Field("", max_length=20000)
    avatarUrl: Optional[str] = Field(None, max_length=2048)
    accountCreatedDate: Optional[str] = None
    avatarPixels: Optional[PixelMatrix] = None
    referenceHandle: Optional[str] = Field(None, max_length=200)
    postImagesPixels: Optional[List[PixelMatrix]] = None
    postsCount: Optional[int] = None
    followersCount: Optional[int] = None
    followingCount: Optional[int] = None

    @field_validator("avatarPixels")
    @classmethod
    def rectangular_avatar(cls, value):
        return EvidenceSamples.rectangular_pixels(value)

    @field_validator("postImagesPixels")
    @classmethod
    def rectangular_post_images(cls, value):
        if value is not None:
            for item in value:
                EvidenceSamples.rectangular_pixels(item)
        return value


class ProfileEvaluationResponse(BaseModel):
    continuousAuthenticityScore: float = Field(..., ge=0.0, le=1.0)
    badgeStatus: str = Field(..., description="e.g. meter-green, meter-amber, meter-red")
    label: str
    signals: List[str]
    calibratedTrustVector: Optional[TrustVector] = None
    evidenceLedger: List[LedgerEvidenceItem] = Field(default_factory=list)
    verificationPlaybook: List[PlaybookStep] = Field(default_factory=list)
    adversarialDialectic: Optional[AdversarialDialectic] = None
    modalitiesEvaluated: List[str] = Field(default_factory=list)
    inspectionComplete: bool = False
    noScoreIsProofNotice: str = "Diagnostic consistency index, not an authenticity probability. No score is proof."


# ---------------------------------------------------------------------------
# Human-in-the-Loop Audit Certificate Schemas
# ---------------------------------------------------------------------------

class AuditSignRequest(BaseModel):
    analystId: str = Field(min_length=1, max_length=100)
    analystNotes: str = Field(min_length=10, max_length=3000)
    finalDecision: str
    completedSteps: List[int]


class AuditCertificateResponse(BaseModel):
    auditCertificateId: str
    timestamp: str
    certificateSha256: str
    downloadPdfUrl: str
    verifyUrl: Optional[str] = None


class ScenarioSummary(BaseModel):
    scenarioId: str
    title: str
    description: str
    simulation: bool = True
