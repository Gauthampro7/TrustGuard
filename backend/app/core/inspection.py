"""Transient multimodal feature extraction and transparent uncertainty calibration."""

import json
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from ..forensics import spatial_fft, audio_vocoder, stylometry_drift, cross_modal_sync, homoglyph_hunter
from ..forensics import canary_tripwire, perceptual_hash, environmental_acoustic, rppg
from ..forensics import ai_image_classifier, ai_text_classifier
from ..models.schemas import (
    TrustGuardInspectionVerdict, TrustVector, VerdictSummary, LedgerEvidenceItem,
    PlaybookStep, CanaryTripwireAlert, EnvironmentalForensics,
)
from .dialectic import synthesize


DIMENSIONS = ("mediaSynthesisScore", "crossModalDiscordanceScore", "identityMismatchScore", "contextualAnomalyScore")


class InsufficientModalities(ValueError):
    pass


def inspect(request, *, require_multimodal=True, registered_tokens=()):
    started = perf_counter()
    ledger, results, modalities = [], [], set()
    scores = {key: [] for key in DIMENSIONS}
    timings, declarations = {}, []
    usable = []
    declared_degradation = 0.0
    environmental = EnvironmentalForensics()
    tripwire = CanaryTripwireAlert(details="No registered canary match observed; absence does not rule out copying.")

    def add(result, dimension, layer, modality, evidence_id, *, score_override=None, polarity_override=None):
        results.append(result)
        timings[f"{evidence_id}:{result.name}"] = round(result.elapsed_ms, 3)
        score = result.score if score_override is None else score_override
        evaluated = result.metrics.get("evaluated", True)
        if evaluated:
            usable.append(result.uncertainty)
        if dimension and evaluated:
            # A signal is bounded by its own usability, so a degraded source cannot raise suspicion
            # and an unrelated short text cannot erase a reliable red flag.
            scores[dimension].append(min(score, 1.15 - result.uncertainty) if result.uncertainty >= 0.5 else score)
        polarity = polarity_override or ("neutral_uncertain" if result.uncertainty >= 0.70 else ("red_flag" if score >= 0.45 else "green_flag"))
        measures = []
        for key in ("highFrequencyPowerRatio", "spectralPeakRatio", "phaseDiscontinuityRate", "briefDigitalSilenceGaps", "yulesK", "urgencyScore", "lagMs", "correlation", "hammingDistance"):
            if key in result.metrics:
                measures.append(f"{key}={result.metrics[key]}")
        for character in result.metrics.get("confusables", [])[:5]:
            measures.append(f"{character['codePoint']} resembles {character['looksLike']!r}")
        measured = (" Measurements: " + "; ".join(measures) + ".") if measures else ""
        ledger.append(LedgerEvidenceItem(
            signalId=f"{evidence_id}:{result.name}", layer=layer, modality=modality,
            polarity=polarity, confidence=round(1 - result.uncertainty, 4),
            finding=" ".join(result.findings) + measured + " Feature reliability is not a probability of authenticity.",
        ))
        return evaluated

    reference = None
    if request.claimedIdentity and request.claimedIdentity.referenceHandles:
        reference = next((v for v in request.claimedIdentity.referenceHandles.model_dump().values() if v), None)
        if reference is not None:
            reference = reference.strip().removeprefix("@")
    for item in request.evidenceItems:
        samples = item.samples
        extra = (item.metadata.extraMetadata or {}) if item.metadata else {}
        if extra.get("fixtureId"):
            declarations.append(extra["fixtureId"][:100])
        degradation = extra.get("qualityDegradation", "0")
        try:
            degradation = float(degradation)
            if 0 <= degradation <= 1:
                declared_degradation = max(declared_degradation, degradation)
        except (TypeError, ValueError):
            pass
        if samples and samples.imagePixels is not None and item.modality.value in {"image", "video"}:
            if add(spatial_fft.analyze(samples.imagePixels), "mediaSynthesisScore", "media_synthetic", "visual", item.evidenceId):
                modalities.add("visual")
            add(ai_image_classifier.analyze(samples.imagePixels), "mediaSynthesisScore", "media_synthetic", "visual", item.evidenceId)
            if samples.referenceImagePixels is not None:
                result = perceptual_hash.analyze(samples.imagePixels, samples.referenceImagePixels)
                # Shared avatars are reuse evidence; an authorized profile can reuse its own avatar.
                add(result, "contextualAnomalyScore", "context_grounding", "visual", item.evidenceId,
                    score_override=0.35 if result.metrics.get("matched") else 0.0, polarity_override="neutral_uncertain")
            if item.modality.value == "video":
                ledger.append(LedgerEvidenceItem(signalId=f"{item.evidenceId}:frame-limit", layer="media_synthetic", modality="visual",
                    polarity="neutral_uncertain", confidence=1.0, finding="The visual spectrum evaluates a sampled frame, not a full video, face identity or biological liveness."))
        if samples and samples.audioSamples is not None and item.modality.value in {"audio", "video"}:
            if len(samples.audioSamples) < samples.sampleRate / 10:
                raise ValueError("Audio must contain at least 0.1 seconds at the declared sample rate")
            if add(audio_vocoder.analyze(samples.audioSamples, samples.sampleRate), "mediaSynthesisScore", "media_synthetic", "audio", item.evidenceId):
                modalities.add("audio")
        if samples and samples.audioEnvelope is not None and item.modality.value == "video":
            add(cross_modal_sync.analyze(samples.audioEnvelope, samples.mouthAperture, samples.envelopeRate),
                "crossModalDiscordanceScore", "cross_modal", "audio+visual", item.evidenceId)
        if samples and samples.roomImpulseResponse is not None:
            result = environmental_acoustic.analyze(samples.roomImpulseResponse, samples.sampleRate, extra.get("claimedEnvironment"))
            if add(result, "crossModalDiscordanceScore", "cross_modal", "audio+declared_context", item.evidenceId):
                modalities.add("audio")
                environmental.rt60Sec = result.metrics["rt60Sec"]
                environmental.reverberationMatchScore = result.metrics["matchScore"]
                environmental.ambientAcousticProfile = result.metrics["profile"]
                environmental.measurementNotes = "Measured room impulse response only; declared environment is not verified from video. Microphones and processing can explain differences."
        if samples and samples.rgbTrace is not None:
            result = rppg.analyze(samples.rgbTrace, samples.envelopeRate)
            if add(result, None, "media_synthetic", "visual", item.evidenceId, polarity_override="neutral_uncertain"):
                modalities.add("visual")
                environmental.rppgPulseConfidence = result.metrics["pulseRegularity"]
                environmental.pulseFrequencyHz = result.metrics["pulseFrequencyHz"]
                environmental.measurementNotes = (environmental.measurementNotes or "") + " Caller-supplied ROI chrominance periodicity is not biological liveness or identity proof."
        text = (item.textContent or "").strip()
        if text and item.modality.value in {"text", "document"}:
            if add(stylometry_drift.analyze(text, baseline_text=extra.get("baselineText")),
                "contextualAnomalyScore", "stylometry_behavior", "text", item.evidenceId):
                modalities.add("text")
            machine_text = ai_text_classifier.analyze(text)
            # AI-assisted writing is common and legitimate: alone it can reach SUSPICIOUS, never HIGH.
            add(machine_text, "mediaSynthesisScore", "media_synthetic", "text", item.evidenceId, score_override=min(machine_text.score, 0.6))
            handle = extra.get("observedHandle")
            if handle:
                add(homoglyph_hunter.analyze(handle.strip().removeprefix("@"), reference=reference), "identityMismatchScore", "identity_consistency", "text", item.evidenceId)
            display_name = extra.get("observedDisplayName")
            if display_name:
                add(homoglyph_hunter.analyze(display_name), "identityMismatchScore", "identity_consistency", "text", item.evidenceId + "-display-name")
            for token in registered_tokens:
                match = canary_tripwire.detect(text, token)
                if match["tripwireTriggered"]:
                    tripwire = CanaryTripwireAlert(tripwireTriggered=True, tripwireType="registered_unicode_marker",
                        details="A locally registered marker was copied. Ownership and unauthorized use still require human verification.")
                    scores["contextualAnomalyScore"].append(0.55)
                    ledger.append(LedgerEvidenceItem(signalId=f"{item.evidenceId}:canary", layer="context_grounding", modality="text",
                        polarity="red_flag", confidence=1, finding=tripwire.details))
                    break
        if item.mediaUri and not samples:
            ledger.append(LedgerEvidenceItem(signalId=f"{item.evidenceId}:unfetched", layer="context_grounding", modality=item.modality.value,
                polarity="neutral_uncertain", confidence=1, finding="A media URI was supplied without local samples. TrustGuard does not fetch remote media; this item was not evaluated."))
        if item.metadata and item.metadata.c2paPresent:
            ledger.append(LedgerEvidenceItem(signalId=f"{item.evidenceId}:provenance", layer="context_grounding", modality=item.modality.value,
                polarity="neutral_uncertain", confidence=1, finding="The caller reports C2PA metadata. No cryptographic provenance validation was performed; this is not an authenticity anchor."))

    if require_multimodal and len(modalities) < 2:
        raise InsufficientModalities("Supply at least two evaluated modalities: visual pixels, audio samples, or text. URLs, empty items and repeated images do not establish multimodality.")
    if not modalities:
        raise InsufficientModalities("No usable evidence samples or text were supplied")
    unavailable = [key for key, values in scores.items() if not values]
    # Repeating easy signals must not outvote an unusable or degraded source.
    uncertainty = max(0.25, max(usable, default=1.0), declared_degradation, 0.10 * len(unavailable))
    channel = max(declared_degradation, 0.90 if len(modalities) < 2 else 0.0)
    if len(modalities) < 2:
        uncertainty = max(uncertainty, 0.90)
    cap = min(1, 1.15 - channel) if channel >= 0.5 else 1
    vector = TrustVector(**{key: round(min(max(values, default=0), cap), 4) for key, values in scores.items()},
                         epistemicUncertainty=round(uncertainty, 4))
    maximum = max(vector.model_dump()[key] for key in DIMENSIONS)
    if maximum >= 0.7:
        tier, headline = "HIGH_IMPERSONATION_RISK", "Multiple signals warrant independent identity checks"
    elif maximum >= 0.4:
        tier, headline = "SUSPICIOUS_ANOMALY", "Anomalies warrant independent verification"
    elif uncertainty >= 0.5:
        tier, headline = "UNCERTAIN_COMPRESSION_NOISE", "Inconclusive / limited or degraded evidence"
    else:
        # No automatic authenticity or verified-identity verdict from absence of anomalies.
        tier, headline = "UNCERTAIN_COMPRESSION_NOISE", "No strong measured anomaly / identity remains unverified"
    if declared_degradation:
        ledger.append(LedgerEvidenceItem(signalId="quality:declared", layer="media_synthetic", modality="capture_context",
            polarity="neutral_uncertain", confidence=1, finding=f"Caller reports quality degradation {declared_degradation:.2f}. The declaration raises uncertainty; it is not independently verified."))
    if unavailable:
        ledger.append(LedgerEvidenceItem(signalId="coverage:missing", layer="context_grounding", modality="coverage",
            polarity="neutral_uncertain", confidence=1, finding="Unmeasured dimensions have index zero, not verified authenticity: " + ", ".join(unavailable) + "."))
    red = [entry.finding for entry in ledger if entry.polarity.value == "red_flag"]
    playbook = [
        PlaybookStep(step=1, action="Contact a known independent channel", instruction="Call a previously known number or internal directory PBX. Do not use contact details supplied by the suspicious account."),
        PlaybookStep(step=2, action="Check the original source", instruction="Request the original recording and compare the full context, account spelling and consented reference archive. Matching avatars or pulse traces do not prove identity."),
        PlaybookStep(step=3, action="Confirm the requested action", instruction="Verify payment details or access requests with a second authorized person through an established channel. Record what was checked before drawing a conclusion."),
    ]
    metadata = {
        "calibration": "Heuristic uncertainty bounds v1; not empirically probability-calibrated. Ledger confidence means feature usability.",
        "evaluatedModalities": ",".join(sorted(modalities)),
        "unavailableDimensions": ",".join(unavailable),
        "simulation": str(bool(declarations)).lower(),
        "fixtureId": ",".join(sorted(set(declarations))),
        "retention": "Samples processed in memory only; only derived verdicts retained in a bounded process-local cache.",
        "extractorTimingsMs": json.dumps(timings),
        "elapsedMs": f"{(perf_counter() - started) * 1000:.3f}",
    }
    return TrustGuardInspectionVerdict(verdictId=f"ver_{uuid4().hex}", requestId=request.requestId,
        evaluatedAt=datetime.now(timezone.utc).isoformat(), assessmentTier=tier, calibratedTrustVector=vector,
        verdictSummary=VerdictSummary(headline=headline, coreAnomaly=red[0] if red else "Review measured features and evidence gaps; this assessment does not establish identity or media origin."),
        evidenceLedger=ledger, verificationPlaybook=playbook,
        adversarialDialectic=synthesize(ledger, vector, unavailable), environmentalForensics=environmental,
        tripwireStatus=tripwire, innovationMetadata=metadata)
