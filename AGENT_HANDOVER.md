# TrustGuard: Agent Handover & Innovation Briefing for Astra Ultra

> **Parallel workspace update:** Read AGENTS.md and docs/team/README.md first. Gautham owns current-device core/API/contracts/integration; Akarsh owns detectors, Aril the dashboard, and Achumit the extension. Tasks are in docs/team/TASKS.md; frozen protocols in contracts/v1/. API handlers are split into api/endpoints/, tests into core/forensics/contracts, and the browser suite into frontend/tests/. Historical paths below remain context; README.md and the team guide contain current commands.

> **Implementation update, 2026-09-25:** The implementation is complete across all layers. See README.md for current scope and launch instructions, and docs/reports/IMPLEMENTATION_VALIDATION.md for 102 passing Python tests, 11 extension checks, 4 live Chromium scenario validations, and zero browser overflow. All 6 creative frontiers (Adversarial Dialectic, RT60 Environmental Acoustics, Steganographic Canary Tripwires, rPPG Periodicity, Attacker vs Defender Sandbox, and Ed25519 Signed Audit Certificates) are implemented and verified.
 
 ---
 
 ## 1. Executive Briefing: The Astra Ultra Innovation Charter
 
 * **Assigned Agent**: **Astra Ultra** (and advanced successor agents).
 * **Project Identifier**: `PS-02` (Track 01: 24-Hour Prototype Build) · **TrustGuard: AI for Digital Trust**.
 * **Current Lifecycle State**: **Full Implementation & Autonomous Creative Frontiers Complete. All 102 tests passing; repository published to private GitHub repo.**
* **Core Stakeholder Directive to Astra Ultra**:
  > 🌟 **The Creative Mandate**: You are **NOT** restricted to only the baseline items requested by the user. The project owner has explicitly authorized and encouraged you to **be creative outside the box**—to invent novel trust-verification mechanisms, propose surprising deceptive counter-measures, design stunning UI micro-interactions, and elevate TrustGuard far beyond a standard hackathon submission into a landmark, award-winning digital trust defense platform.
* **Team Profile**: University student team competing in Innovators Conclave 2026.
  * *Directive*: Maintain high professional rigor and technical authority. **Never explicitly mention student status in pitch slides, code docstrings, or UI copy.**
  * *Constraint*: All software must run reliably on standard consumer laptops with zero paid API crutches and zero GPU dependencies ($<150\text{ms}$ execution target).
  * *User Boundary*: **Do not start coding feature algorithms, model weights, or servers until the user explicitly commands "start".**

---

## 2. System Architecture & Critical Design Tenets (The Safety Rails)

While Astra Ultra has full creative freedom, the following core tenets mandated by the problem statement must remain uncompromised:

### Tenet 1: "No Score is Proof" (Judges Scoring Trap #1)
* **Never** output a single scalar confidence score as absolute truth (e.g., `"88% AI Fake"`).
* **Always** compute the **Calibrated 5D Trust Vector**:
  $$\mathbf{T} = \left\langle S_{\text{media}}, S_{\text{cross}}, S_{\text{ident}}, S_{\text{context}}, U_{\text{epistemic}} \right\rangle$$
* **Always** provide:
  1. The **Dual-Polarity Evidence Ledger** (Red Flags vs. Green Mitigating Factors).
  2. The **Independent Verification Playbook** (human-in-the-loop action steps: PBX call, source video archive lookup, escrow bank verification).

### Tenet 2: True Multimodality (Judges Scoring Trap #2)
* Evaluators penalize *"A single-modality model dressed up as multimodal"*.
* Every inspection case must synthesize at least **two modalities**:
  * Modality A: Media (Video visual frames / Audio speech spectrum / Images).
  * Modality B: Communication text / WhatsApp chat / Email transcripts.
  * Modality C: Identity baseline / Claimed role / Provenance metadata / Historical archives.

### Tenet 3: Zero-Scraping / Extension-First Architecture
* Do **NOT** write backend web scrapers that query Twitter/Instagram/LinkedIn directly. They trigger immediate Cloudflare IP blacklists and fail during live demos.
* Use the **Chrome Manifest V3 Extension** to inspect public DOM elements directly inside the user's active browser session.
* For personal identity enrollment, use **consented BYOD (Bring-Your-Own-Data)** archives (GDPR Takeout exports).

### Tenet 4: Privacy & India DPDP Act 2023 Compliance
* **Zero raw biometric storage**: Never store raw face photos or voice audio on disk.
* Store only **irreversible, salted normalized float vectors** (512-d ArcFace, 192-d ECAPA-TDNN) protected by AES-256-GCM envelope encryption.

---

## 3. Creative Frontiers for Astra Ultra (Beyond the Prompt)

Astra Ultra is green-lit to expand the codebase with these innovative vectors:

### 💡 Creative Frontier 1: Dual-Agent Adversarial Dialectic ("Prosecutor vs. Defense AI")
Instead of outputting a dry score, instantiate an adversarial forensic debate inside the explainability engine:
* **The Forensic Prosecutor**: Highlights mathematical artifacts (2D-FFT azimuthal spikes, vocoder phase cuts, homoglyph lookalikes).
* **The Forensic Public Defender**: Argues legitimate real-world noise (low bitrate transcode, poor sensor illumination, micro-jitter).
* **The Judicial Resolution**: Explains the calibrated 5D Trust Vector as the mathematical synthesis of both viewpoints.
* *Schema hook*: `adversarialDialectic` in `TrustGuardInspectionVerdict`.

### 💡 Creative Frontier 2: Environmental Acoustics & Room Reverberation Discordance (RT60)
* Detect acoustic space contradictions: e.g., video shows an executive standing in an echoey convention hall, but audio has an RT60 reverberation time of $<0.15\text{s}$ (soundproof recording studio), indicating vocal dubbing.
* *Schema hook*: `environmentalForensics` in `TrustGuardInspectionVerdict`.

### 💡 Creative Frontier 3: Active Canary Tokens & Persona Tripwires
* Provide users with a tool to generate invisible zero-width unicode tokens or unique stylistic watermarks ("canary salt") embedded in public bio strings.
* When clone accounts or scraping LLMs ingest and re-post this text, TrustGuard instantly triggers a `tripwireTriggered: true` alert.
* *Schema hook*: `tripwireStatus` in `TrustGuardInspectionVerdict`.

### 💡 Creative Frontier 4: Remote Photoplethysmography (rPPG) Biological Liveness
* CPU-friendly OpenCV spatial chrominance analysis on facial regions (forehead / cheeks) detecting cardiac pulse micro-flushes to distinguish living flesh from synthetic diffusion frames.

### 💡 Creative Frontier 5: Interactive "Attacker vs. Defender" Demo Sandbox
* In `frontend/`, allow judges to interactively manipulate distortion sliders (e.g. inject compression noise, shift pitch, alter sentence burstiness) and watch TrustGuard’s 5D Vector calibrate dynamically in real time.

### 💡 Creative Frontier 6: Cryptographically Sealed Audit Certificate with Live QR Code
* In `backend/app/api/routes.py`, generate a tamper-evident audit PDF containing a real scannable QR code that verifies the report against the local API endpoint.

---

## 4. Directory Layout & Module Index

```
TrustGuard/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # FastAPI v1 endpoints conforming to OPENSPEC
│   │   ├── core/config.py         # App settings & CORS configuration
│   │   ├── forensics/             # 4-layer fast CPU forensic modules (<150ms)
│   │   ├── models/schemas.py      # Pydantic v2 data contracts (extensible)
│   │   ├── scenarios/             # Pre-indexed demo scenario payloads
│   │   └── main.py                # FastAPI entry point
│   └── requirements.txt
├── docs/
│   ├── presentations/             # presentation_simple.{html,pptx}, presentation.{html,pptx}
│   ├── reports/                   # QA Defense Guide & Feasibility Report PDFs
│   └── problem_statement/        # PS-02 challenge brief, images, and text
├── extension/                     # Chrome Manifest V3 Browser Extension
│   ├── manifest.json              # Extension manifest v3 metadata
│   ├── background.js              # Background service worker
│   ├── content.js                 # DOM-level profile inspector
│   └── popup/                     # Popup interface (popup.html, popup.js, popup.css)
├── frontend/                      # Web Dashboard Portal
│   ├── index.html                 # Main evidence upload dropzone, Trust Vector & Playbook UI
│   ├── styles.css                 # Light-themed clean design system
│   └── app.js                     # Client interaction logic
├── scripts/                       # Python generator scripts for decks and PDFs
├── tests/                         # Test suite (tests/test_schemas.py 4/4 passing)
├── .gitignore                     # Git ignore rules
├── OPENSPEC.md                    # Data contracts & JSON-LD specification
└── README.md                      # Master documentation
```

---

## 5. Work Completed in Refactoring Phase

1. **Repository Clean & Modularized**: Root directory contains only essential specifications, configs, and top-level packages. All documentation and media neatly categorized in `docs/`.
2. **Data Contracts Implemented & Tested**:
   - `backend/app/models/schemas.py` created with complete Pydantic v2 validation.
   - Enhanced with extensible models: `AdversarialDialectic`, `EnvironmentalForensics`, `CanaryTripwireAlert`.
   - `tests/test_schemas.py` passing 100% (**4/4 tests passed in 0.04s**).
3. **API & Configuration Scaffolding**:
   - `backend/app/core/config.py` configured with CORS, epistemic uncertainty dampening ($U \ge 0.50$), and local laptop execution.
   - `backend/app/api/routes.py` wired with the core endpoints.
   - `backend/app/main.py` entrypoint ready.
4. **Browser Extension Scaffolding**:
   - Chrome Manifest V3 configuration in `extension/manifest.json`.
   - Content script, background service worker, and popup UI created.
5. **Frontend Web Dashboard Scaffolding**:
   - `frontend/index.html`, `styles.css`, and `app.js` ready with 5D Trust Vector, Dual-Polarity Ledger, and verification playbook layout.

---

## 6. Execution Roadmap for Astra Ultra (When User Says "Start")

Execute in this structured sequence:

### Step 1: Forensic Modules Implementation (`backend/app/forensics/`)
Implement deterministic, fast CPU algorithms:
1. `spatial_fft.py`: Azimuthal average on 2D Fourier power spectrum (detects upsampling checkerboard artifacts).
2. `stylometry_drift.py`: Function word frequencies, Yule's Characteristic $K$, and urgency keyword scoring.
3. `cross_modal_sync.py`: Audio waveform envelope vs video mouth aperture correlation.
4. `homoglyph_hunter.py`: Confusable unicode lookalike character scanner.
5. *(Astra Creative Addition)* `environmental_acoustic.py`: RT60 reverberation estimation and ambient noise matching.
6. *(Astra Creative Addition)* `canary_tripwire.py`: Active honeypot token generator and verifier.

### Step 2: Adversarial Dialectic Engine (`backend/app/core/dialectic.py`)
Implement the synthesizer that generates the "Prosecutor vs. Defense AI" judicial ruling for each verdict.

### Step 3: Pre-Indexed Golden Scenarios (`backend/app/scenarios/`)
Implement 4 realistic, instant-loading scenarios:
1. `ceo-wire-scam.json`: Authentic executive video + AI cloned voice + urgent WhatsApp text.
2. `homoglyph-clone.json`: Cyrillic spoofed social media handle + cloned avatar.
3. `creator-copyright.json`: Stolen digital artwork + scraped bio + active canary tripwire trigger.
4. `wifi-compression-edge-case.json`: Low-res field video with high epistemic uncertainty ($U \ge 0.50$) correctly dampening suspicion.

### Step 4: Wire Frontend & Extension
- Connect `frontend/app.js` to `POST /api/v1/inspect`.
- Add interactive visual cards for the **Adversarial Dialectic**, **Environmental Acoustics**, **Canary Tripwire Alert Banner**, and **Attacker vs Defender Demo Sandbox**.
- Connect `extension/background.js` to `POST /api/v1/extension/evaluate-profile`.

### Step 5: Run End-to-End Verification
- Launch test suite with `pytest` (102 tests passed).
- Run extension validation with Node test runner (11 tests passed).
- Execute live Chromium headless validation across 1440px desktop and 390px mobile viewports (4 scenarios verified).
- Validate that all scenarios return properly structured verdicts and vectors in $<150\text{ms}$.
