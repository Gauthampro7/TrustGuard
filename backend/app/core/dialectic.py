"""Deterministic adversarial explanations grounded in the evidence ledger."""

from ..models.schemas import AdversarialDialectic, EvidencePolarity


def synthesize(ledger, vector, unavailable):
    red = [item.finding for item in ledger if item.polarity == EvidencePolarity.RED_FLAG]
    defense = [item.finding for item in ledger if item.polarity != EvidencePolarity.RED_FLAG]
    uncertainty = vector.epistemicUncertainty
    cap = min(1.0, 1.15 - uncertainty) if uncertainty >= 0.5 else 1.0
    return AdversarialDialectic(
        prosecutionArgument=" ".join(red[:3]) or "No measured feature crossed an anomaly threshold. This does not establish authenticity.",
        defenseMitigation=" ".join(defense[:3]) or "Compression, editing and capture conditions can produce similar artifacts; independent verification remains necessary.",
        judicialSynthesis=(
            f"Rule-based synthesis, not an independent AI adjudication. Uncertainty is {uncertainty:.2f}; "
            f"each suspicion dimension is bounded at {cap:.2f}. "
            + (f"Unmeasured dimensions: {', '.join(unavailable)}. " if unavailable else "")
            + "These are heuristic indices, not calibrated probabilities or proof of identity. Complete the independent verification playbook."
        ),
    )
