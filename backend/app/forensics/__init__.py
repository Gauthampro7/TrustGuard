"""
TrustGuard Forensics Suite: bounded, local measurements; every score is a review cue, not proof.

Heuristic extractors (NumPy only, <150 ms warmed on bounded inputs):
- spatial_fft, audio_vocoder: spatial spectrum and STFT phase / digital-silence measurements
- stylometry_drift: function words, Yule's K, optional baseline drift, urgency/payment/secrecy cues
- cross_modal_sync: correlation of caller-supplied audio-envelope and mouth-aperture traces
- homoglyph_hunter, perceptual_hash, canary_tripwire: Unicode TR39 lookalikes, DCT pHash reuse, copy markers
- environmental_acoustic, rppg: conditional RT60 from a measured impulse response, ROI chrominance periodicity

Optional pretrained extractors (backend/app/forensics/requirements-ml.txt; abstain when not installed):
- ai_text_classifier: RoBERTa AI-generated-text classifier for English prose
- ai_image_classifier: Swin-v2 AI-generated-image classifier

See VALIDATION.md for measured behaviour, limits and latency.
"""

__all__ = []
