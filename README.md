# TrustGuard — Evidence before action

Local multimodal inspection for Track 01 PS-02: AI for Digital Trust. TrustGuard measures media and text, exposes both suspicious and mitigating findings, and requires independent human checks before an analyst seals a report. No score is proof.

## Run on Windows

Python 3.11+ and a modern Chromium browser are sufficient. There are no GPU, downloaded model-weight or paid API dependencies.

### One-Click Launch (Recommended)
Double-click `start.bat` or run in terminal:
```bat
.\start.bat
```
This automatically checks your environment, runs the system diagnostics suite, opens the TrustGuard Forensics Dashboard at **http://127.0.0.1:8000/dashboard/** in your default browser, and starts the FastAPI server.

### Manual Launch
```powershell
python -m pip install -r backend/requirements.txt
python scripts/diagnostics.py
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/dashboard/** (navigating to `http://127.0.0.1:8000/` automatically redirects browser traffic to the dashboard). Interactive API documentation is at **http://127.0.0.1:8000/api/v1/docs**. The server serves the dashboard directly; a separate frontend server is unnecessary. Do not open `index.html` with `file://`.

Choose a simulated case and click **Inspect evidence**, or supply a local image/audio/video file and accompanying text. Original files stay in the browser; reduced numeric samples are processed transiently by the loopback API. The browser processes images up to 128 × 128 pixels, the first six seconds of audio at 16 kHz, or a single video frame. Full video decoding, automatic mouth tracking and voice/face identity recognition are not implemented.

Load `extension/` using Chrome → Extensions → Developer mode → Load unpacked. On a supported public profile, click **Inspect this profile** in the popup. See [the extension guide](extension/README.md) for consent, supported routes, limitations and tests. No backend social scraping occurs. Cross-origin avatars can be unreadable to canvas; these produce an explicitly incomplete text advisory, not a multimodal inspection.

## What is implemented

| Component | Measured evidence and limits |
| --- | --- |
| Spatial spectrum | Windowed 2D FFT and azimuthal power, high-frequency energy, roll-off and narrow spectral peaks. Compression and textures can resemble synthetic artifacts. |
| Audio spectrum | STFT phase discontinuities, mel-band transitions and brief digital silence. These are not specific to vocoders. |
| Text | Function-word frequencies, Yule's K, optional adequate-length baseline drift, payment/urgency/verification-bypass cues. English rules; no LLM authorship classifier. |
| Cross-modal timing | Correlation of supplied synchronized audio-envelope and mouth-aperture traces. No automatic mouth ROI extraction or phoneme inference. |
| Identity spelling | Offline Unicode 17.0.0 TR39 confusable table, handle/reference collision and mixed-script display-name checks. Legitimate multilingual names are not inherently suspicious. |
| Avatar reuse | DCT perceptual hash against supplied reference pixels. A match is neutral reuse evidence until authorization is established; no face recognition. |
| Canary tripwires | Locally registered invisible markers, copied-text detection and dashboard generation. Markers may be stripped; a match does not identify a bot or prove unauthorized copying. |
| Conditional acoustics | Schroeder T20/RT60 estimation from a **measured room impulse response**, not arbitrary speech. Broad declared-room comparisons are illustrative. |
| Conditional chrominance | At least eight seconds of supplied facial ROI RGB means, with periodicity consistency checks. This is not a biological liveness probability. |
| Explainability | Five-dimensional vector, red/green/uncertain ledger, deterministic prosecutor/defense synthesis and independent verification playbook. |
| Incident records | Real PDF and scannable QR, Ed25519-signed assessment plus detached seal binding the PDF SHA-256 and session public key. |

`POST /api/v1/inspect` requires at least **two actually evaluated modalities** among visual, audio and text. Duplicate images, absent media, constant frames, silent audio and unfetched URLs cannot satisfy this requirement. The extension can return an incomplete advisory with the full vector and uncertainty explicitly displayed.

Scores are **heuristic anomaly indices, not empirically calibrated probabilities**. The four suspicion dimensions are capped at `1.15 - U` when epistemic uncertainty `U >= 0.50`. The least usable source bounds overall uncertainty so repeated easy signals cannot dilute degraded evidence. Unmeasured dimensions use zero as a schema placeholder and are listed explicitly as unavailable. No automatic tier asserts verified identity or authenticity.

## Demonstrations and API

`GET /api/v1/scenarios/{id}` returns a labeled synthetic fixture and an inspection `request`. The dashboard sends that request through the real extractors; it does not receive a hard-coded verdict.

- `ceo-wire-scam`: executive-transfer narrative, synthetic audio gating, delayed mouth traces and payment pressure alongside an intact visual channel.
- `homoglyph-clone`: Cyrillic lookalike handle and actual pHash comparison against a supplied synthetic avatar reference.
- `creator-copyright`: stolen digital artwork and bio with an active zero-width canary tripwire alert, Cyrillic lookalike handle and DCT pHash asset reuse match.
- `wifi-compression-edge-case`: noisy low-resolution frame, benign narrative and declared transmission loss; high uncertainty dampens suspicion.

These fixtures contain generated signals, not real biometric recordings or a validated deepfake benchmark. Rebuild with `python scripts/build_scenarios.py`.

The dashboard also features an interactive **Attacker vs. Defender Adversarial Sandbox**, allowing judges and analysts to inject channel degradation/packet loss, Cyrillic homoglyph lookalikes, urgent financial pressure, and registered canary honeytokens to watch the calibrated 5D Trust Vector and epistemic dampening ceiling adjust dynamically in real time.

The existing Pydantic request contract is extended by `evidenceItems[].samples`:

```json
{
  "imagePixels": "16–256 rectangular grayscale rows; numeric values 0–255",
  "referenceImagePixels": "optional reference image in the same representation",
  "audioSamples": "up to 96000 normalized mono samples, numeric values -1 to 1",
  "sampleRate": 16000,
  "audioEnvelope": "optional synchronized nonnegative measurements",
  "mouthAperture": "same length and timeline as audioEnvelope; video modality",
  "envelopeRate": 25,
  "roomImpulseResponse": "optional measured room impulse response; not ordinary speech",
  "rgbTrace": "optional facial ROI mean RGB values, at least eight seconds for analysis"
}
```

This block describes field shapes; strings describing arrays must be replaced with actual numeric arrays. Samples must match their declared modality. Requests are limited to eight evidence items and 8 MiB. Remote `mediaUri` and `avatarUrl` values are never fetched. A claimed C2PA presence flag is not cryptographically validated or treated as an authenticity anchor.

Other endpoints: `GET /api/v1/scenarios`, `GET /api/v1/forensics/capabilities`, `POST /api/v1/extension/evaluate-profile`, `POST /api/v1/canaries`, `POST /api/v1/cases/{verdictId}/sign-audit`, `GET /api/v1/certificates/{id}.pdf`, and `GET /api/v1/certificates/{id}/verify`.

## Privacy and certificate scope

No raw media, face/voice embeddings or decoded samples are written to disk or browser storage. Only derived verdicts and analyst records remain in bounded process memory: 128 cases and 64 certificates, each accessible for up to one hour; restart clears all records and the ephemeral signing key. Canary registration retains at most 100 random tokens per process. The fixture files are synthetic test signals.

Biometric enrollment and an encrypted identity vault are **not implemented or exposed**. The baseline schema reserves embedding contracts but the runtime never persists such data. Normalization, salting and encryption alone do not make biometric embeddings irreversible. Future biometric persistence would need a validated template-protection design, AES-256 envelope encryption, consent and retention controls. This prototype does not claim a legal DPDP compliance certification.

Signing requires an existing case, every playbook step marked completed, substantive notes and an explicit analyst decision. The analyst identifier is self-declared. Ed25519 protects record integrity, not the factual accuracy of the assessment, the truth of the notes or the identity of the analyst. Verification returns canonical payload and detached manifest signatures for independent checking. The public key is session-local, not an external trust authority.

The default QR URL works on the computer running the backend. For a phone on a trusted local network, set `TRUSTGUARD_PUBLIC_BASE_URL` to that computer's reachable HTTP origin and explicitly launch with `--host 0.0.0.0`; local firewall configuration must permit the connection. The configured URL affects the QR; the dashboard's download and verification links remain on loopback. Do not expose this unauthenticated local prototype to the public internet.

## Verification

```powershell
python -m pytest tests/
python -m pytest tests/test_performance.py tests/test_environmental.py -s -q
node --test extension/tests/*.test.cjs
```

The tests cover real feature extraction, multimodality enforcement, degradation bounds, canaries, malformed inputs, full API flows, signature/PDF tampering and extension consent/navigation behavior. PDF QR decoding is tested when optional PyMuPDF and OpenCV are installed. Bounded warmed extractor timings target <150 ms on the test host; model imports, browser decoding, HTTP transport and PDF generation are outside the extractor budget. Hardware and OS scheduling can affect latency.

For browser validation, install Playwright with `npm install --no-save playwright`, install its browser with `npx playwright install chromium`, start the backend, then run `node scripts/test_dashboard.cjs`. An existing Chromium binary can be selected with `PLAYWRIGHT_CHROMIUM_EXECUTABLE`; `PLAYWRIGHT_MODULE` can point to an existing Playwright installation. The script exercises the live local API and writes its report and desktop/mobile screenshots under `scratch/dashboard-smoke/`.

## Project map

- `backend/app/forensics/`: bounded CPU measurements and vendored Unicode data.
- `backend/app/core/`: inspection synthesis, deterministic dialectic, configuration and volatile signed records.
- `backend/app/api/`: live API and three fixture loaders.
- `frontend/`: accessible responsive evidence workbench.
- `extension/`: Manifest V3 public-DOM inspector.
- `tests/`: schemas, extractors, performance, environment signals and API regressions.
- `docs/presentations/`, `docs/reports/`: existing presentation and defense artifacts. Earlier pitch documents describe ambitions beyond the implemented scope above.

See [OPENSPEC.md](OPENSPEC.md) for the original contracts and implementation amendments.
