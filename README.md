# TrustGuard — Defense-in-Depth Digital Trust & Forensics Engine

[![Tests](https://img.shields.io/badge/Tests-414%20Passing-brightgreen.svg)](#verification)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.115-teal.svg)](https://fastapi.tiangolo.com/)
[![Extension](https://img.shields.io/badge/Chrome%20Extension-Manifest%20V3-purple.svg)](extension/)
[![Privacy](https://img.shields.io/badge/Privacy-Zero--Storage%20In--Memory-success.svg)](#privacy-and-data-protection)
[![Architecture](https://img.shields.io/badge/Architecture-Dual--Ledger%20%2B%205D%20Vector-orange.svg)](#core-architectural-pillars)

> **Track 01 PS-02: AI for Digital Trust**
> TrustGuard is a multimodal digital trust platform engineered to inspect manipulated media, deceptive text, and impersonation attempts across the open web. Rather than relying on a brittle single-scalar "deepfake probability", TrustGuard combines a **5-Dimensional Calibrated Trust Vector**, a **Dual-Entry Evidence Ledger** (prosecution vs. defense), and **Human-in-the-Loop Cryptographic Verification**.

---

## At a Glance

TrustGuard provides a **dual-interface architecture** tailored for both everyday users and specialized forensic investigators:

1. **🛡️ TrustGuard Quick Scam Scanner (Active by Default)**:
   An intuitive, rapid-assessment web tool designed for consumers, employees, and community moderators. Provides four independent, single-purpose detectors:
   - **AI Image & Deepfake Detector**: 2D-FFT azimuthal power and spectral lattice analysis.
   - **Fake & Lookalike Username Checker**: Unicode 17.0 TR39 Cyrillic/Greek homoglyph detection.
   - **Scam Message & Urgency Analyzer**: Linguistic coercion, wire-bypass, and financial demand screening.
   - **Full Multi-Modal Scam Scanner**: Comprehensive cross-checking with plain-English rationales and safety checklists.

2. **🔬 Forensic Analyst Workbench (`/dashboard/index.html`)**:
   A full-spectrum investigation cockpit for SOC analysts and fraud teams:
   - **5D Trust Vector Visualization**: Media synthesis ($S_{media}$), identity mismatch ($S_{ident}$), contextual anomaly ($S_{context}$), cross-modal discordance ($S_{cross}$), and epistemic uncertainty ($U_{epistemic}$).
   - **Adversarial Dialectic Engine**: Deterministic prosecution vs. defense synthesis resolving competing explanations.
   - **Attacker vs. Defender Sandbox (`AR-1`)**: Interactive perturbation simulator testing channel degradation and homoglyph injections in real time.
   - **Cryptographic Audit Certificates**: Ephemeral Ed25519-signed reports with downloadable tamper-proof PDF receipts and scannable QR verification.

3. **🧩 Zero-API Chrome Extension (`extension/`)**:
   Manifest V3 in-browser inspector running against live social profiles (Instagram, X, LinkedIn) with continuous dynamic authenticity scoring (0–100) and privacy-first local canvas downsampling.

---

## 🚀 Quick Start (60 Seconds)

### Option A: One-Click Launch on Windows (Recommended)
Double-click `start.bat` or run in PowerShell:
```bat
.\start.bat
```
*This validates your Python environment, runs the offline diagnostic suite, starts the FastAPI server on port 8000, and automatically opens the **Quick Scam Scanner** in your default browser.*

### Option B: Manual Launch (Cross-Platform)
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt -c backend/constraints.txt

# 2. Verify system health (offline diagnostics)
python scripts/diagnostics.py

# 3. Launch local API server (<150ms warmed response target)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

- **Quick Scam Scanner (Default)**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/) *(or `/dashboard/simple.html`)*
- **Forensic Analyst Workbench**: [http://127.0.0.1:8000/dashboard/index.html](http://127.0.0.1:8000/dashboard/index.html)
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)

*(Note: Navigating to `http://127.0.0.1:8000/` automatically redirects browser traffic to the Quick Scam Scanner. Both interfaces include one-click navigation to toggle seamlessly between simple and advanced modes).*

---

## 🎯 Evaluator & Judge Walkthrough

### 1. Test the Quick Scam Scanner (10 Seconds)
Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/):
- **Test Image Detector**: Click **⚡ Test Synthetic / AI Face** &rarr; **Scan Image for AI Artifacts**. Watch the 2D-FFT azimuthal detector identify synthetic grid frequencies.
- **Test Fake Username Checker**: Switch to the **Fake Username Checker** tab &rarr; Click **⚡ Try Fake CarryMinati (@CаrryMinati)** &rarr; **Check Handle**. Observe the offline Unicode TR39 engine pinpoint the Cyrillic `а` (U+0430) disguised inside Latin text.
- **Test Scam Message Checker**: Switch to the **Scam Message Checker** tab &rarr; Click **⚡ Try Urgent Bank Wire Demand** &rarr; **Analyze Message**. Watch the NLP heuristics flag emergency coercion and off-platform payment routing.
- **Test Full Multi-Modal Scanner**: Switch to the **Full Scam Scanner** tab &rarr; Select a 1-click preset (e.g. *CarryMinati YouTube Giveaway Scam*) &rarr; Click **Check for Scams & Fakes** to see combined multi-modal synthesis.

### 2. Test the Forensic Analyst Workbench
Click **🔬 Switch to Advanced Forensic Workbench** (top right) or navigate to [http://127.0.0.1:8000/dashboard/index.html](http://127.0.0.1:8000/dashboard/index.html):
- **Explore Simulated Cases**: Use the preset dropdown to test:
  1. `01 · Executive wire request` (Cross-modal audio/mouth discordance and financial pressure)
  2. `02 · Lookalike profile` (Cyrillic homoglyph collision + DCT pHash avatar reuse)
  3. `03 · Poor connection, real uncertainty` (*Crucial feature*: demonstrates epistemic uncertainty $U \ge 0.80$ dampening false-positive suspicion)
  4. `04 · Creator copyright & canary tripwire` (Detects zero-width steganographic honeytoken in bio + stolen artwork)
- **Attacker vs. Defender Sandbox**: Expand the sandbox card, increase channel degradation to 70%, and click **Apply perturbations & inspect**. Observe $U_{epistemic}$ rise while the suspicion dimensions cap at $\min(S_{raw}, 1.15 - U)$ to prevent unfair false accusations.
- **Seal Cryptographic Audit**: Complete the 3 independent verification playbook checks, input analyst notes, select a verdict, and click **Seal & Sign Audit Case**. Download the signed PDF report and inspect the detached Ed25519 signature payload.

### 3. Test the Chrome Browser Extension
1. Open Google Chrome &rarr; Navigate to `chrome://extensions/`.
2. Enable **Developer mode** (toggle in upper right).
3. Click **Load unpacked** &rarr; Select the `extension/` folder in this repository.
4. Visit any public profile on **Instagram**, **X (Twitter)**, or **LinkedIn**.
5. Click the **TrustGuard shield icon** in your extensions toolbar &rarr; Click **Inspect this profile**.
6. The extension extracts public DOM elements, securely downsamples the avatar via HTML5 canvas, calls the local backend, and renders a continuous 0–100 authenticity score with risk alerts.

---

## 🏛️ Core Architectural Pillars

```
                      ┌────────────────────────────────────────┐
                      │        Browser / Extension Client      │
                      │  (Downsampled grayscale canvas / DOM)  │
                      └───────────────────┬────────────────────┘
                                          │ Transient JSON (<= 8 MiB)
                                          ▼
                      ┌────────────────────────────────────────┐
                      │       FastAPI Local Engine (Port 8000) │
                      │       Warmed Execution Target < 150ms   │
                      └───────┬────────────────────────┬───────┘
                              │                        │
             ┌────────────────▼────────┐      ┌────────▼───────────────┐
             │   Forensics Extractors   │      │ Dual-Entry Ledger      │
             │   - 2D-FFT Spatial Spec │      │ - Prosecution (Red)    │
             │   - STFT Audio Discont. │      │ - Defense (Green)      │
             │   - Unicode 17.0 TR39   │      │ - Uncertainty (Grey)   │
             │   - DCT pHash Reuse     │      └────────┬───────────────┘
             │   - Zero-Width Canaries │               │
             └────────────────┬────────┘               │
                              │                        │
                              ▼                        ▼
                      ┌────────────────────────────────────────┐
                      │   5D Calibrated Trust Vector Engine    │
                      │   [S_media, S_ident, S_ctx, S_cross]   │
                      │    Capped by (1.15 - U_epistemic)      │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │  Adversarial Dialectic & Playbook      │
                      │  (Human-in-the-Loop Analyst Gate)      │
                      └───────────────────┬────────────────────┘
                                          │ Complete checks + notes
                                          ▼
                      ┌────────────────────────────────────────┐
                      │ Ephemeral Ed25519 Signed Audit & PDF   │
                      │ (Detached SHA-256 Manifest + QR Code)  │
                      └────────────────────────────────────────┘
```

### 1. Epistemic Uncertainty & Non-Scalar Trust
Single-scalar "authenticity percentages" are scientifically flawed and prone to severe false positives under compression noise. TrustGuard outputs a 5-dimensional vector:
- $S_{media} \in [0, 1]$: Media synthesis anomaly index.
- $S_{ident} \in [0, 1]$: Identity and homoglyph collision index.
- $S_{context} \in [0, 1]$: Linguistic coercion and urgency anomaly index.
- $S_{cross} \in [0, 1]$: Cross-modal temporal discordance.
- $U_{epistemic} \in [0, 1]$: Degradation and channel uncertainty.

**The Epistemic Ceiling**: When channel degradation occurs ($U_{epistemic} \ge 0.50$), all suspicion dimensions are strictly bounded:
$$\text{Calibrated Score} = \min\left(S_{raw},\; 1.15 - U_{epistemic}\right)$$
This guarantees that degraded, low-quality, or compressed media cannot be falsely branded as malicious deepfakes.

### 2. Dual-Entry Evidence Ledger
To eliminate confirmation bias, TrustGuard enforces a dual-entry ledger for every inspection:
- **Red Flags (Prosecution)**: Indicators of manipulation, synthetic frequencies, or coercion.
- **Green Flags (Defense)**: Mitigating factors such as natural camera spectral decay, consistent multi-year account metrics, or typical compression artifacts.
- **Neutral / Informational**: Contextual observations that do not tip the balance.

### 3. Reversible Adversarial Sandbox (`AR-1`)
Analysts can test "what-if" hypotheses directly inside the workbench. Perturbations (channel noise, packet degradation, Cyrillic injections, urgent payment markers) can be applied and completely reverted with zero state contamination.

### 4. Zero-Storage In-Memory Architecture
- **No Raw Media Retention**: Media files never touch disk or external cloud servers.
- **Local Numeric Processing**: Images are downsampled in-memory to 64x64 or 128x128 matrices; audio is downsampled to 6-second mono normalized waveforms.
- **Bounded Volatile State**: Retains at most 128 active cases and 64 certificates in ephemeral memory with 1-hour expiration. Restarting the server purges all data and generates a fresh signing key pair.

---

## 🔬 Implemented Forensics Capabilities

| Component | Detection Engine | Measured Signals & Scientific Boundaries |
| :--- | :--- | :--- |
| **Spatial Spectrum** | 2D Fast Fourier Transform | Azimuthal power distributions, high-frequency energy ratios, spectral roll-off, and generator grid lattice peaks. |
| **Audio Spectrum** | Short-Time Fourier Transform | Phase discontinuities, spectral centroid flux, mel-frequency transitions, and synthetic zero-crossing silence. |
| **Identity Spelling** | Offline Unicode 17.0.0 TR39 | Confusable skeleton mapping, Cyrillic/Greek mixed-script injection, and invisible character detection. |
| **Avatar Reuse** | Perceptual DCT Hash | 64-bit DCT perceptual hash distance against supplied reference avatars. Signals image reuse, not facial identity. |
| **Canary Tripwires** | Steganographic Zero-Width Markers | Locally registered invisible Unicode tokens embedded in public bios. Detects direct scraping and credential reuse. |
| **Cross-Modal Sync** | Pearson Correlation Tracing | Temporal correlation between normalized audio-envelope dynamics and video mouth-aperture time-series. |
| **Acoustic Profiling** | Schroeder Reverberation | T20/RT60 reverberation estimation from room impulse responses (RIR). |
| **Facial Photoplethysmography** | Chrominance Signal Analysis | Periodicity consistency across facial ROI mean RGB signals (requires $\ge 8$ seconds of stable video). |

---

## 🧪 Verification & Test Suite

The TrustGuard repository maintains a rigorous test suite of **414 passing tests** across core, forensics, browser extension, and end-to-end integration:

```powershell
# 1. Core API, Contract & Architecture Suite (85 tests)
python -m pytest tests/core/ tests/contracts/

# 2. Forensics Detectors, Models & Environmental Suite (263 tests)
python -m pytest tests/forensics/

# 3. Chrome Browser Extension Suite (49 tests)
node --test extension/tests/*.test.cjs

# 4. End-to-End Headless Chromium Smoke Suite (12 checks)
# Requires local server running on port 8000
node frontend/tests/browser-smoke.cjs

# 5. Offline System Health & Diagnostics (5 verification stages)
python scripts/diagnostics.py

# 6. Contract Frozen Protocol & ABI Conformance
python scripts/export_contracts.py --check
```

### Verified Test Summary
- ✅ **Core & Contracts**: 85 passed (0 warnings, 0 drift)
- ✅ **Forensics Engines**: 263 passed, 6 cleanly skipped (missing optional heavy GPU models cleanly abstain)
- ✅ **Browser Extension**: 49 passed across Instagram, X, LinkedIn DOM adapters, multi-image sampling, and memory safety
- ✅ **E2E Browser Smoke**: 12/12 passed (Chromium headless audit signing, sandbox transforms, PDF receipts)
- ✅ **Diagnostics**: 5/5 passed (100% component availability)

---

## 📁 Repository Structure

```
TrustGuard/
├── backend/                  # FastAPI Core Engine
│   ├── app/
│   │   ├── api/              # Versioned API routes (/api/v1/)
│   │   ├── core/             # 5D trust vector synthesis, audit signing, dialectic
│   │   ├── forensics/        # 2D-FFT, STFT, Unicode TR39, DCT pHash, Canary engines
│   │   └── main.py           # Application entry point, static mounts, route dispatch
│   ├── requirements.txt      # Locked production dependencies
│   └── constraints.txt       # Version constraints
├── frontend/                 # Responsive Zero-Dependency Web Client
│   ├── simple.html           # TrustGuard Quick Scam Scanner (Default Mode)
│   ├── simple.js             # Client logic for 4 independent scam detectors
│   ├── simple.css            # Accessible styling for Quick Scanner
│   ├── index.html            # Forensic Analyst Workbench
│   ├── app.js                # Workbench inspection, sandbox, audit workflows
│   ├── styles.css            # Workbench interface styles
│   └── tests/                # Playwright Chromium browser-smoke test suite
├── extension/                # Manifest V3 Chrome Extension
│   ├── src/                  # Background service worker, DOM adapters, popup UI
│   ├── adapters/             # Instagram, X (Twitter), and LinkedIn extractors
│   ├── tests/                # Native Node.js test runner suite (49 tests)
│   └── manifest.json         # Extension manifest (strict host permissions)
├── contracts/                # Shared Interface Contracts & ABI
│   ├── v1/                   # Frozen OpenAPI schemas, extractor interfaces
│   └── ownership.json        # Path authority and module ownership mappings
├── scripts/                  # Diagnostics, verification, and contract exporters
│   ├── diagnostics.py        # Offline system health verification
│   ├── export_contracts.py   # ABI drift checker
│   ├── check_module.py       # Per-module test runner
│   └── check_ownership.py    # Git boundary enforcement
├── tests/                    # Comprehensive Test Suites
│   ├── core/                 # API, validation, rate limiting, and audit tests
│   ├── contracts/            # Frozen protocol snapshots and schema tests
│   └── forensics/            # Signal processing, ML fallbacks, and performance tests
├── start.bat                 # Windows one-click launcher
└── README.md                 # Project documentation
```

---

## 👥 Engineering & Module Ownership

TrustGuard adheres to a modular engineering ownership architecture enforced via `contracts/ownership.json`:

| Module | Primary Owner | Scope & Responsibilities |
| :--- | :--- | :--- |
| **Core, API & Integration** | **Gautham** | FastAPI application, 5D vector synthesis, Ed25519 audit signing, contract frozen snapshots, integration CI. |
| **Forensic Engines** | **Akarsh** | 2D-FFT spatial analysis, STFT audio signals, Unicode TR39 confusable tables, pretrained model loaders. |
| **Frontend & Cockpit** | **Aril** | Quick Scam Scanner, Forensic Workbench UI, interactive sandbox, Playwright smoke tests, accessibility (WCAG AA). |
| **Browser Extension** | **Achumit** | Manifest V3 architecture, Instagram/X/LinkedIn DOM extractors, multi-image sampling, client privacy. |

---

## 🔒 Privacy and Data Protection

- **Zero Remote Calls for Evidence**: External `mediaUri` or `avatarUrl` values are never fetched by the backend. All processing occurs on data supplied directly by the client.
- **No Raw Biometric Storage**: Biometric enrollment databases and face/voice vector stores are deliberately excluded to safeguard user privacy under DPDP principles.
- **Ephemeral Key Lifecycle**: Audit reports are sealed using session-bound Ed25519 key pairs that rotate upon server restart.
- **Client-Side Data Bounding**: Media inputs are processed in transient chunks limited to 8 MiB per request.

---

## 📜 License & Compliance

TrustGuard is developed for **Track 01 PS-02: AI for Digital Trust**. Built exclusively with open-source dependencies under permissive licenses (Apache 2.0 / MIT / BSD).
