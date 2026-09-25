/* Local evidence workbench. Original files and decoded samples are never persisted by this client. */
"use strict";

const API_ORIGIN = "http://127.0.0.1:8000";
const API_BASE = `${API_ORIGIN}/api/v1`;
const byId = id => document.getElementById(id);
const state = { revision: 0, controller: null, fixture: null, media: [], verdict: null, busy: false, signing: false, originalBundle: null };
const dimensions = { media: "mediaSynthesisScore", cross: "crossModalDiscordanceScore", ident: "identityMismatchScore", context: "contextualAnomalyScore", uncertainty: "epistemicUncertainty" };
const tiers = { BENIGN_AUTHENTIC: "LOW OBSERVED ANOMALY · VERIFY INDEPENDENTLY", LOW_RISK_VERIFIED: "LOW OBSERVED ANOMALY · VERIFY INDEPENDENTLY", UNCERTAIN_COMPRESSION_NOISE: "INCONCLUSIVE / DEGRADED EVIDENCE", SUSPICIOUS_ANOMALY: "ANOMALIES REQUIRE VERIFICATION", HIGH_IMPERSONATION_RISK: "ELEVATED IMPERSONATION INDICATORS" };

let copyStatusTimer = null;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function status(message, error = false) {
  const target = byId("operation-status");
  target.textContent = message;
  target.classList.toggle("error", error);
}

function busy(value, label = "Inspecting evidence…") {
  state.busy = value;
  byId("btn-run-inspection").disabled = value;
  byId("btn-run-inspection").textContent = value ? label : "Inspect evidence →";
  document.body.classList.toggle("is-busy", value);
  byId("workspace").setAttribute("aria-busy", String(value));
  updateAudit();
}

function resetResult() {
  state.verdict = null;
  byId("verdict-banner").className = "verdict-banner";
  byId("verdict-tier").textContent = "READY TO INSPECT";
  const verdictBadge = byId("verdict-badge");
  if (verdictBadge) { verdictBadge.textContent = ""; verdictBadge.className = "verdict-badge"; }
  byId("verdict-headline").textContent = "Every signal needs context.";
  byId("verdict-detail").textContent = "Inspect the current bundle to see its assessment.";
  byId("run-metadata").textContent = "";
  for (const key of Object.keys(dimensions)) setBar(key, null);
  for (const id of ["red-flags-list", "green-flags-list", "neutral-flags-list"]) byId(id).replaceChildren(node("li", "Awaiting inspection.", "empty-state"));
  byId("ledger-count").textContent = "AWAITING EVIDENCE";
  byId("prosecution-arg").textContent = "Awaiting evidence.";
  byId("defense-arg").textContent = "Awaiting evidence.";
  byId("judicial-synthesis").textContent = "Independent human verification remains the deciding step.";
  byId("uncertainty-note").textContent = "Missing or degraded evidence increases uncertainty; it cannot establish authenticity.";
  byId("uncertainty-note").classList.remove("elevated");
  byId("playbook-steps").replaceChildren(node("p", "Your verification steps will appear after inspection.", "empty-state"));
  byId("audit-links").replaceChildren();
  byId("audit-links").hidden = true;
  byId("audit-notes").value = "";
  byId("final-decision").value = "";
  byId("audit-status").textContent = "Complete all steps, add your identifier and findings, then choose a decision.";
  if (byId("tripwire-banner")) byId("tripwire-banner").hidden = true;
  if (byId("verdict-actions")) byId("verdict-actions").hidden = true;
  if (byId("inspector-card")) byId("inspector-card").hidden = true;
  if (byId("copy-brief-status")) byId("copy-brief-status").textContent = "";
  if (byId("environmental-card")) {
    byId("environmental-card").hidden = true;
    byId("environmental-grid").replaceChildren();
    byId("environmental-notes").textContent = "";
  }
  updateAudit();
}

function invalidate() {
  state.revision += 1;
  state.controller?.abort();
  state.controller = null;
  busy(false);
  resetResult();
  status("");
  return state.revision;
}

function snapshotOriginalBundle() {
  state.originalBundle = {
    targetName: byId("target-name").value,
    targetHandle: byId("target-handle").value,
    messageText: byId("message-text").value,
    media: structuredClone(state.media),
    fixture: state.fixture ? structuredClone(state.fixture) : null
  };
}

function onInputChange() {
  if (state.originalBundle) {
    const slider = byId("sandbox-degradation");
    const isPerturbed = (slider && Number(slider.value) > 0) ||
      byId("sandbox-homoglyph")?.checked ||
      byId("sandbox-urgency")?.checked ||
      byId("sandbox-canary")?.checked;
    if (!isPerturbed) {
      state.originalBundle.targetName = byId("target-name").value;
      state.originalBundle.targetHandle = byId("target-handle").value;
      state.originalBundle.messageText = byId("message-text").value;
    }
  }
  invalidate();
}

async function api(path, options = {}) {
  const ownController = options.signal ? null : new AbortController();
  const timer = ownController ? setTimeout(() => ownController.abort(), 20000) : null;
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: options.signal || ownController.signal, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers } });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      let detail = `Local engine returned HTTP ${response.status}.`;
      if (typeof payload?.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload?.detail)) {
        detail = payload.detail.map(item => {
          if (typeof item === "string") return item;
          const loc = Array.isArray(item?.loc) ? item.loc.filter(l => l !== "body").join(".") : "";
          const msg = item?.msg || item?.message || JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }).join("; ");
      } else if (typeof payload?.message === "string") {
        detail = payload.message;
      } else if (typeof payload?.error === "string") {
        detail = payload.error;
      }
      throw new Error(detail);
    }
    if (!payload) throw new Error("The local engine returned an unreadable response.");
    return payload;
  } catch (error) {
    if (error instanceof TypeError) throw new Error("Cannot reach the local engine at 127.0.0.1:8000. Start the backend and serve this dashboard from a permitted local origin.");
    throw error;
  } finally { if (timer) clearTimeout(timer); }
}

async function health() {
  try {
    const response = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3500), cache: "no-store" });
    if (!response.ok) throw new Error("Unavailable");
    byId("system-status").className = "system-status online";
    byId("health-label").textContent = "Local engine connected";
  } catch {
    byId("system-status").className = "system-status offline";
    byId("health-label").textContent = "Local engine unavailable";
  }
}

function drawPixels(source, width, height) {
  if (!width || !height) throw new Error("This media has no readable visual frame.");
  const ratio = Math.min(1, 128 / Math.max(width, height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(width * ratio));
  canvas.height = Math.max(1, Math.round(height * ratio));
  if (Math.min(canvas.width, canvas.height) < 16) throw new Error("Visual evidence must remain at least 16 × 16 pixels after resizing. Choose a larger image with a less extreme aspect ratio.");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.fillStyle = "white";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(source, 0, 0, canvas.width, canvas.height);
  const rgba = context.getImageData(0, 0, canvas.width, canvas.height).data;
  const imagePixels = Array.from({ length: canvas.height }, (_, y) => Array.from({ length: canvas.width }, (_, x) => {
    const i = (y * canvas.width + x) * 4;
    return Math.round(.2126 * rgba[i] + .7152 * rgba[i + 1] + .0722 * rgba[i + 2]);
  }));
  return { imagePixels, resolution: `${canvas.width}x${canvas.height}` };
}

function waitForMedia(media, event, initiate) {
  return new Promise((resolve, reject) => {
    const finish = error => {
      clearTimeout(timer);
      media.removeEventListener(event, ready);
      media.removeEventListener("error", failed);
      error ? reject(error) : resolve();
    };
    const ready = () => finish();
    const failed = () => finish(new Error("This media format could not be decoded by your browser."));
    const timer = setTimeout(() => finish(new Error("Media decoding timed out. Try a shorter clip or a PNG image.")), 12000);
    media.addEventListener(event, ready, { once: true });
    media.addEventListener("error", failed, { once: true });
    initiate();
  });
}

async function decode(file, index) {
  if (file.size > 20 * 1024 * 1024) throw new Error(`${file.name}: exceeds the 20 MB local decoding limit.`);
  const evidenceId = `media_${index}_${crypto.randomUUID()}`;
  if (file.type.startsWith("audio/")) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass || !window.OfflineAudioContext) throw new Error("Your browser does not support local audio decoding.");
    const context = new AudioContextClass();
    try {
      const arrayBuf = await file.arrayBuffer();
      const decodePromise = context.decodeAudioData(arrayBuf);
      const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error(`${file.name}: audio decoding timed out.`)), 12000));
      const audio = await Promise.race([decodePromise, timeoutPromise]);
      const duration = Math.min(6, audio.duration);
      if (duration < .1) throw new Error("Audio evidence must contain at least 0.1 seconds of decoded samples.");
      const offline = new OfflineAudioContext(1, Math.max(1, Math.floor(duration * 16000)), 16000);
      const source = offline.createBufferSource();
      source.buffer = audio;
      source.connect(offline.destination);
      source.start(0, 0, duration);
      const rendered = await offline.startRendering();
      const audioSamples = Array.from(rendered.getChannelData(0), value => Math.round(Math.max(-1, Math.min(1, value)) * 100000) / 100000);
      return { name: file.name, note: `${duration.toFixed(1)} s · mono 16 kHz · transient samples`, item: { evidenceId, modality: "audio", samples: { audioSamples, sampleRate: 16000 }, metadata: { durationSec: duration, extraMetadata: { extraction: "Browser decoded, mono downmix; first six seconds maximum." } } } };
    } finally { await context.close(); }
  }
  const url = URL.createObjectURL(file);
  try {
    if (file.type.startsWith("image/")) {
      const image = new Image();
      await waitForMedia(image, "load", () => { image.src = url; });
      const data = drawPixels(image, image.naturalWidth, image.naturalHeight);
      return { name: file.name, note: `${data.resolution} grayscale · transient pixels`, item: { evidenceId, modality: "image", samples: { imagePixels: data.imagePixels }, metadata: { resolution: data.resolution, extraMetadata: { extraction: "Browser grayscale reduction; source provenance unverified." } } } };
    }
    if (file.type.startsWith("video/")) {
      const video = document.createElement("video");
      video.preload = "auto";
      video.muted = true;
      video.playsInline = true;
      try {
        await waitForMedia(video, "loadeddata", () => { video.src = url; });
        if (Number.isFinite(video.duration) && video.duration > .1) await waitForMedia(video, "seeked", () => { video.currentTime = Math.min(1, video.duration / 2); });
        const data = drawPixels(video, video.videoWidth, video.videoHeight);
        return { name: file.name, note: `${data.resolution} · one video frame only · no audio/sync analysis`, item: { evidenceId, modality: "video", samples: { imagePixels: data.imagePixels }, metadata: { resolution: data.resolution, extraMetadata: { extraction: "Single visual frame only; audio, lip-sync, temporal liveness unavailable." } } } };
      } finally { video.removeAttribute("src"); video.load(); }
    }
    throw new Error(`${file.name}: choose an image, audio or video file. Documents and URLs are not fetched.`);
  } finally { URL.revokeObjectURL(url); }
}

function renderMedia() {
  byId("media-list").replaceChildren(...state.media.map(media => {
    const item = node("li", media.name);
    item.append(node("small", media.note));
    return item;
  }));
  byId("clear-media").hidden = !state.media.length && !state.fixture;
}

async function chooseFiles(files) {
  const revision = invalidate();
  state.fixture = null;
  state.media = [];
  state.originalBundle = null;
  byId("scenario-select").value = "none";
  byId("scenario-notice").hidden = true;
  renderMedia();
  if (!files.length) return;
  if (files.length > 4) { status("Choose at most four files per inspection.", true); return; }
  busy(true, "Preparing local samples…");
  status("Decoding media in this browser. Original files are not uploaded.");
  try {
    const prepared = [];
    for (const [index, file] of Array.from(files).entries()) {
      if (revision !== state.revision) return;
      prepared.push(await decode(file, index));
      if (revision !== state.revision) return;
    }
    state.media = prepared;
    snapshotOriginalBundle();
    renderMedia();
    status("Media prepared. Add the accompanying text, then inspect the bundle.");
  } catch (error) {
    if (revision === state.revision) status(error.message, true);
  } finally { if (revision === state.revision) busy(false); byId("file-input").value = ""; }
}

async function scenarioChanged() {
  const selected = byId("scenario-select").value;
  const revision = invalidate();
  state.fixture = null;
  state.media = [];
  state.originalBundle = null;
  renderMedia();
  byId("scenario-notice").hidden = true;
  byId("message-text").value = "";
  byId("target-name").value = "";
  byId("target-handle").value = "";
  if (selected === "none") return;
  busy(true, "Loading simulated case…");
  try {
    const scenario = await api(`/scenarios/${encodeURIComponent(selected)}`);
    if (revision !== state.revision) return;
    if (!scenario.request?.evidenceItems || scenario.simulation !== true) throw new Error("The scenario response did not identify a valid simulation.");
    state.fixture = scenario.request;
    state.media = scenario.request.evidenceItems.filter(item => item.modality !== "text").map(item => ({ name: `Simulated ${item.modality} fixture`, note: "Pre-indexed synthetic signal fixture; not a verified real-world incident.", item }));
    byId("target-name").value = scenario.request.claimedIdentity?.entityName || "";
    byId("target-handle").value = scenario.request.claimedIdentity?.referenceHandles?.x_twitter || "";
    byId("message-text").value = scenario.request.evidenceItems.filter(item => item.modality === "text").map(item => item.textContent || "").join("\n\n");
    byId("scenario-notice").textContent = `SIMULATION · ${scenario.title}. ${scenario.description} These pre-indexed synthetic samples demonstrate the pipeline; their labels are scenario assumptions, not detector proof.`;
    byId("scenario-notice").hidden = false;
    snapshotOriginalBundle();
    renderMedia();
    status("Simulated case loaded. Select Inspect evidence to run the local extractors.");
  } catch (error) {
    if (revision === state.revision) status(error.name === "AbortError" ? "Scenario loading timed out. Check the local engine and retry." : error.message, true);
  } finally { if (revision === state.revision) busy(false); }
}

function buildRequest() {
  const text = byId("message-text").value.trim();
  if (!text || !state.media.length) throw new Error("An inspection needs two modalities: add readable media and an accompanying message or transcript.");
  const request = state.fixture ? structuredClone(state.fixture) : {};
  request.requestId = `req_web_${crypto.randomUUID()}`;
  request.timestamp = new Date().toISOString();
  request.sourceChannel = "web_portal";
  request.claimedIdentity = { ...(request.claimedIdentity || {}), entityName: byId("target-name").value.trim() || undefined, referenceHandles: { ...(request.claimedIdentity?.referenceHandles || {}), x_twitter: byId("target-handle").value.trim() || undefined } };
  const textTemplate = request.evidenceItems?.find(item => item.modality === "text") || {};
  request.evidenceItems = [...state.media.map(media => media.item), { ...textTemplate, evidenceId: "message_1", modality: "text", textContent: text }];
  return request;
}

function setBar(id, value) {
  const valid = typeof value === "number" && Number.isFinite(value);
  const bounded = valid ? Math.max(0, Math.min(1, value)) : 0;
  const bar = byId(`bar-${id}`);
  bar.style.width = `${bounded * 100}%`;
  byId(`val-${id}`).textContent = valid ? bounded.toFixed(2) : "—";
  const badge = byId(`badge-${id}`);
  let qualitative = "Not evaluated";
  if (badge) {
    if (!valid) {
      badge.textContent = "—";
      badge.className = "dim-badge";
    } else if (id === "uncertainty") {
      if (bounded >= .50) {
        badge.textContent = "ELEVATED";
        badge.className = "dim-badge badge-elevated-uncertainty";
        qualitative = `${bounded.toFixed(2)} - Elevated uncertainty (suspicion scores capped)`;
      } else if (bounded >= .25) {
        badge.textContent = "MODERATE";
        badge.className = "dim-badge badge-moderate";
        qualitative = `${bounded.toFixed(2)} - Moderate uncertainty`;
      } else {
        badge.textContent = "LOW";
        badge.className = "dim-badge badge-low";
        qualitative = `${bounded.toFixed(2)} - Low uncertainty`;
      }
    } else {
      if (bounded >= .65) {
        badge.textContent = "HIGH";
        badge.className = "dim-badge badge-high";
        qualitative = `${bounded.toFixed(2)} - High anomaly indicator`;
      } else if (bounded >= .35) {
        badge.textContent = "MODERATE";
        badge.className = "dim-badge badge-moderate";
        qualitative = `${bounded.toFixed(2)} - Moderate anomaly indicator`;
      } else {
        badge.textContent = "LOW";
        badge.className = "dim-badge badge-low";
        qualitative = `${bounded.toFixed(2)} - Low anomaly indicator`;
      }
    }
  }
  if (valid) bar.parentElement.setAttribute("aria-valuenow", bounded.toFixed(3));
  else bar.parentElement.removeAttribute("aria-valuenow");
  bar.parentElement.setAttribute("aria-valuetext", qualitative);
}

function renderVerdict(verdict) {
  if (!verdict.verdictId || !verdict.calibratedTrustVector || !Array.isArray(verdict.evidenceLedger) || !Array.isArray(verdict.verificationPlaybook)) throw new Error("Incomplete verdict received. Inspect again after checking the backend.");
  state.verdict = verdict;
  const vector = verdict.calibratedTrustVector;
  const uncertain = vector.epistemicUncertainty >= .5;
  byId("verdict-banner").className = `verdict-banner ${uncertain ? "uncertain" : /SUSPICIOUS|HIGH_/.test(verdict.assessmentTier) ? "suspicious" : ""}`;
  byId("verdict-tier").textContent = `${state.fixture ? "SIMULATION · " : ""}${tiers[verdict.assessmentTier] || "ASSESSMENT REQUIRES REVIEW"}`;
  const verdictBadge = byId("verdict-badge");
  if (verdictBadge) {
    if (uncertain) {
      verdictBadge.textContent = "❓ HIGH UNCERTAINTY (U ≥ 0.50) · CAPPED";
      verdictBadge.className = "verdict-badge badge-uncertain";
    } else if (/SUSPICIOUS|HIGH_/.test(verdict.assessmentTier)) {
      verdictBadge.textContent = "⚠️ ELEVATED ANOMALY";
      verdictBadge.className = "verdict-badge badge-suspicious";
    } else {
      verdictBadge.textContent = "🛡️ LOW ANOMALY";
      verdictBadge.className = "verdict-badge badge-low-risk";
    }
  }
  byId("verdict-headline").textContent = verdict.verdictSummary?.headline || "Inspection complete";
  byId("verdict-detail").textContent = verdict.verdictSummary?.coreAnomaly || "Review the ledger and verification steps.";
  for (const [id, key] of Object.entries(dimensions)) setBar(id, vector[key]);
  byId("proof-notice").textContent = verdict.verdictSummary?.noScoreIsProofNotice || "Review the evidence and verify independently.";
  const metadata = verdict.innovationMetadata || {};
  byId("run-metadata").textContent = [metadata.evaluatedModalities && `Evaluated: ${metadata.evaluatedModalities}`, metadata.elapsedMs && `Local extraction: ${metadata.elapsedMs} ms`, `Case: ${verdict.verdictId}`].filter(Boolean).join(" · ");
  byId("uncertainty-note").textContent = `${uncertain ? "Elevated uncertainty: anomaly indicators are dampened to limit overclaiming. " : "Limited anomalies do not establish authenticity. "}${metadata.calibration || "Missing dimensions remain uncertain; check data limitations below."}`;
  byId("uncertainty-note").classList.toggle("elevated", uncertain);
  const destinations = { red_flag: "red-flags-list", green_flag: "green-flags-list", neutral_uncertain: "neutral-flags-list" };
  for (const [polarity, id] of Object.entries(destinations)) {
    const signals = verdict.evidenceLedger.filter(item => item.polarity === polarity);
    byId(id).replaceChildren(...(signals.length ? signals.map(signal => {
      const item = node("li", signal.finding);
      item.append(node("small", `${signal.modality} · ${String(signal.layer).replaceAll("_", " ")}`));
      return item;
    }) : [node("li", polarity === "green_flag" ? "No mitigating anchors established." : polarity === "red_flag" ? "No red flags identified; this does not establish authenticity." : "No additional limitations recorded.", "empty-state")]));
  }
  byId("ledger-count").textContent = `${verdict.evidenceLedger.length} SIGNALS`;
  byId("prosecution-arg").textContent = verdict.adversarialDialectic?.prosecutionArgument || "No argument supplied.";
  byId("defense-arg").textContent = verdict.adversarialDialectic?.defenseMitigation || "No mitigation supplied.";
  byId("judicial-synthesis").textContent = verdict.adversarialDialectic?.judicialSynthesis || "Independent verification remains required.";
  byId("playbook-steps").replaceChildren(...verdict.verificationPlaybook.map((step, index) => {
    const row = node("div", undefined, "step-item");
    const checkbox = node("input");
    checkbox.type = "checkbox";
    checkbox.id = `verification-step-${index}`;
    checkbox.dataset.step = String(step.step);
    checkbox.addEventListener("change", updateAudit);
    const label = node("label", `${step.step}. ${step.action}`);
    label.htmlFor = checkbox.id;
    label.append(node("span", step.instruction));
    row.append(checkbox, label);
    return row;
  }));
  const tripwire = verdict.tripwireStatus;
  const tripwireBanner = byId("tripwire-banner");
  if (tripwireBanner) {
    if (tripwire && tripwire.tripwireTriggered) {
      tripwireBanner.hidden = false;
      byId("tripwire-details").textContent = tripwire.details || "A registered invisible copy marker was detected in the inspected text. Independent human verification is required.";
    } else {
      tripwireBanner.hidden = true;
    }
  }
  const env = verdict.environmentalForensics;
  const envCard = byId("environmental-card");
  if (envCard) {
    if (env && (env.rt60Sec != null || env.rppgPulseConfidence != null || env.ambientAcousticProfile != null)) {
      const stats = [];
      if (env.rt60Sec != null) {
        const s = node("div", undefined, "env-stat");
        s.append(node("span", "RT60 Reverberation"), node("strong", `${env.rt60Sec.toFixed(2)} s`));
        stats.push(s);
      }
      if (env.ambientAcousticProfile) {
        const s = node("div", undefined, "env-stat");
        s.append(node("span", "Estimated Space"), node("strong", env.ambientAcousticProfile));
        stats.push(s);
      }
      if (env.reverberationMatchScore != null) {
        const s = node("div", undefined, "env-stat");
        s.append(node("span", "Space Consistency"), node("strong", `${(env.reverberationMatchScore * 100).toFixed(0)}%`));
        stats.push(s);
      }
      if (env.rppgPulseConfidence != null) {
        const s = node("div", undefined, "env-stat");
        s.append(node("span", "Chrominance Periodicity"), node("strong", `${(env.rppgPulseConfidence * 100).toFixed(0)}%`));
        stats.push(s);
      }
      if (env.pulseFrequencyHz != null) {
        const s = node("div", undefined, "env-stat");
        s.append(node("span", "Pulse Frequency"), node("strong", `${env.pulseFrequencyHz.toFixed(2)} Hz`));
        stats.push(s);
      }
      byId("environmental-grid").replaceChildren(...stats);
      byId("environmental-notes").textContent = env.measurementNotes || "Caller-supplied acoustic and physiological micro-signals.";
      envCard.hidden = false;
    } else {
      envCard.hidden = true;
    }
  }
  if (byId("verdict-actions")) byId("verdict-actions").hidden = false;
  const inspectorCard = byId("inspector-card");
  if (inspectorCard) {
    let hasViz = false;
    const canvasSpectral = byId("canvas-spectral");
    if (canvasSpectral && verdict.innovationMetadata?.evaluatedModalities?.includes("visual")) {
      hasViz = true;
      const ctx = canvasSpectral.getContext("2d");
      ctx.clearRect(0, 0, canvasSpectral.width, canvasSpectral.height);
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(30, 10); ctx.lineTo(30, 75); ctx.lineTo(260, 75);
      ctx.stroke();
      ctx.strokeStyle = "#ba4857";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(30, 20);
      for (let i = 0; i <= 20; i++) {
        const x = 30 + (i / 20) * 230;
        const power = Math.exp(-i / 6) * 50 + 5;
        ctx.lineTo(x, 75 - power);
      }
      ctx.stroke();
    }
    const canvasSynchrony = byId("canvas-synchrony");
    if (canvasSynchrony) {
      const ctx = canvasSynchrony.getContext("2d");
      ctx.clearRect(0, 0, canvasSynchrony.width, canvasSynchrony.height);
      const videoItem = state.media.find(m => m.item?.modality === "video" && m.item?.samples?.audioEnvelope);
      if (videoItem?.item?.samples) {
        hasViz = true;
        const envSample = videoItem.item.samples.audioEnvelope;
        const mouth = videoItem.item.samples.mouthAperture;
        if (envSample && mouth && envSample.length) {
          ctx.strokeStyle = "#376fd2";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          const step = Math.min(80, envSample.length);
          for (let i = 0; i < step; i++) {
            const x = 20 + (i / step) * 240;
            const y = 75 - (envSample[i] || 0) * 50;
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          ctx.stroke();
          ctx.strokeStyle = "#d9822b";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          for (let i = 0; i < step; i++) {
            const x = 20 + (i / step) * 240;
            const y = 75 - (mouth[i] || 0) * 50;
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          ctx.stroke();
        }
      }
    }
    inspectorCard.hidden = !hasViz;
  }
  updateAudit();
  byId("verdict-banner").focus({ preventScroll: true });
}

async function inspect() {
  let request;
  try { request = buildRequest(); } catch (error) { status(error.message, true); return; }
  const revision = invalidate();
  const controller = new AbortController();
  state.controller = controller;
  const timer = setTimeout(() => controller.abort(), 20000);
  busy(true);
  status("Evaluating media and text with the local engine…");
  try {
    const verdict = await api("/inspect", { method: "POST", body: JSON.stringify(request), signal: controller.signal });
    if (revision !== state.revision) return;
    renderVerdict(verdict);
    status(state.fixture ? "Simulation complete. Review both sides of the evidence and the uncertainty before proceeding." : "Inspection complete. Independent verification is required before acting on this assessment.");
  } catch (error) {
    if (revision === state.revision) status(error.name === "AbortError" ? "Inspection timed out. Check the local backend, then try again." : error.message, true);
  } finally { clearTimeout(timer); if (revision === state.revision) { state.controller = null; busy(false); } }
}

function updateAudit() {
  const checks = [...document.querySelectorAll("#playbook-steps input[type=checkbox]")];
  const completed = checks.filter(check => check.checked).length;
  byId("playbook-progress").textContent = checks.length ? `${completed} / ${checks.length} CHECKS COMPLETED` : "AWAITING INSPECTION";
  byId("btn-sign-audit").disabled = !state.verdict || state.busy || state.signing || !checks.length || completed !== checks.length || !byId("analyst-id").value.trim() || byId("audit-notes").value.trim().length < 10 || !byId("final-decision").value;
}

function safeApiLink(url, label) {
  if (typeof url !== "string" || !url) throw new Error("Certificate link missing from the local engine response.");
  let resolved;
  try {
    resolved = new URL(url, API_ORIGIN);
  } catch {
    throw new Error("Invalid certificate link returned by engine.");
  }
  if (resolved.origin !== API_ORIGIN) throw new Error("Certificate link must point to the local TrustGuard backend.");
  if (resolved.protocol !== "http:" && resolved.protocol !== "https:") throw new Error("Certificate link has untrusted protocol.");
  const link = node("a", label);
  link.href = resolved.href;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  return link;
}

async function signAudit() {
  updateAudit();
  if (byId("btn-sign-audit").disabled) return;
  const revision = state.revision;
  const verdictId = state.verdict.verdictId;
  const request = { analystId: byId("analyst-id").value.trim(), analystNotes: byId("audit-notes").value.trim(), finalDecision: byId("final-decision").value, completedSteps: [...document.querySelectorAll("#playbook-steps input:checked")].map(input => Number(input.dataset.step)) };
  state.signing = true;
  updateAudit();
  byId("audit-status").textContent = "Sealing your independent assessment…";
  byId("audit-links").hidden = true;
  try {
    const result = await api(`/cases/${encodeURIComponent(verdictId)}/sign-audit`, { method: "POST", body: JSON.stringify(request) });
    if (revision !== state.revision) return;
    const links = [safeApiLink(result.downloadPdfUrl, "Download signed incident PDF ↗")];
    if (result.auditCertificateId) links.push(safeApiLink(`/api/v1/certificates/${encodeURIComponent(result.auditCertificateId)}/verify`, "Verify certificate integrity ↗"));
    if (result.certificateSha256) links.push(node("code", `SHA-256 ${result.certificateSha256}`));
    byId("audit-links").replaceChildren(...links);
    byId("audit-links").hidden = false;
    byId("audit-status").textContent = `${state.fixture ? "SIMULATION RECORD · " : ""}Certificate created. Integrity verification does not authenticate the underlying incident.`;
  } catch (error) {
    if (revision === state.revision) byId("audit-status").textContent = error.name === "AbortError" ? "Certificate request timed out. Try again." : error.message;
  } finally { state.signing = false; updateAudit(); }
}

async function generateCanary() {
  const text = byId("canary-text").value.trim();
  if (!text) { byId("canary-status").textContent = "Enter the public bio text you want to mark."; return; }
  byId("btn-canary").disabled = true;
  byId("canary-result").hidden = true;
  byId("canary-status").textContent = "Generating a local tripwire…";
  try {
    const result = await api("/canaries", { method: "POST", body: JSON.stringify({ text }) });
    byId("canary-output").value = result.markedText;
    byId("canary-notice").textContent = result.notice || "Keep a copy of your marked text. Platforms may remove invisible markers.";
    byId("canary-result").hidden = false;
    byId("canary-status").textContent = "Marked text is ready. Copy it to a profile you own; keep your original for comparison.";
  } catch (error) { byId("canary-status").textContent = error.name === "AbortError" ? "Tripwire request timed out. Try again." : error.message; }
  finally { byId("btn-canary").disabled = false; }
}

function initSandbox() {
  const slider = byId("sandbox-degradation");
  const valLabel = byId("sandbox-degradation-val");
  if (!slider || !valLabel) return;
  slider.addEventListener("input", () => {
    valLabel.textContent = `${slider.value}%`;
    slider.setAttribute("aria-valuenow", slider.value);
    slider.setAttribute("aria-valuetext", `${slider.value}% channel degradation`);
  });

  byId("btn-apply-sandbox").addEventListener("click", () => {
    if (!state.originalBundle) {
      snapshotOriginalBundle();
    }
    const baseBundle = state.originalBundle;
    if (!baseBundle) return;

    let handle = baseBundle.targetHandle;
    let text = baseBundle.messageText;
    let name = baseBundle.targetName;
    let media = structuredClone(baseBundle.media);
    let fixture = baseBundle.fixture ? structuredClone(baseBundle.fixture) : null;

    const degradation = Number(slider.value) / 100;
    for (const m of media) {
      m.item.metadata = m.item.metadata || {};
      m.item.metadata.extraMetadata = m.item.metadata.extraMetadata || {};
      if (degradation > 0) {
        m.item.metadata.extraMetadata.qualityDegradation = String(degradation);
      } else {
        delete m.item.metadata.extraMetadata.qualityDegradation;
      }
    }

    if (byId("sandbox-homoglyph").checked) {
      let handleSource = handle || "sample_handle";
      const homoglyphs = { a: "\u0430", e: "\u0435", o: "\u043e", p: "\u0440", c: "\u0441" };
      let injected = "";
      for (const ch of handleSource) injected += homoglyphs[ch.toLowerCase()] || ch;
      handle = injected;
      for (const m of media) {
        if (m.item.metadata?.extraMetadata) m.item.metadata.extraMetadata.observedHandle = injected;
      }
      if (text) {
        text = text.replace(/\b(account|wire|transfer|payment|official)\b/gi, match => match.split("").map(ch => homoglyphs[ch.toLowerCase()] || ch).join(""));
      }
    } else {
      for (const m of media) {
        if (m.item.metadata?.extraMetadata) delete m.item.metadata.extraMetadata.observedHandle;
      }
    }

    if (byId("sandbox-urgency").checked) {
      const urgencyAddition = " Urgent wire transfer immediately: bypass approval policy just this once, do not call my office, send funds before close of business.";
      if (!text.includes("bypass approval policy")) {
        text += urgencyAddition;
      }
    }

    if (byId("sandbox-canary").checked) {
      const canaryMarker = "\u2063\u200b\u2063\u200d\u200c\u200c\u200d\u200d\u200d\u200d\u200c\u200d\u200d\u200d\u200c\u200c\u200c\u200d\u200c\u200c\u200d\u200c\u200c\u200c\u200c\u200d\u200d\u200c\u200c\u200c\u200d\u200d\u200d\u200c\u200d\u200c\u200d\u200c\u200c\u200d\u200c\u200d\u200c\u200d\u200d\u200d\u200d\u200c\u200d\u200d\u200d\u200d\u200c\u200c\u200d\u200c\u200d\u200d\u200d\u200c\u200d\u200c\u200d\u200d\u200d\u200d\u200d\u200c\u200d\u200d\u200c\u200d\u200d\u200d\u200c\u200d\u200c\u200d\u200d\u200d\u200c\u200d\u200d\u200d\u200c\u200c\u200c\u200d\u200c\u200c\u200d\u200c\u200d\u200d\u200c\u200d\u200c\u200c\u200c\u200d\u200d\u200d\u200c\u200c\u200d\u200d\u200d\u200d\u200d\u200c\u200c\u200d\u200d\u200d\u200d\u200c\u200d\u200c\u200c\u200d\u200c\u200c\u200c\u200c\u200d\u200c\u200d\u200d\u200c\u200c\u200c\u2063\u200b\u2063";
      if (!text.includes(canaryMarker)) {
        text += canaryMarker;
      }
    }

    byId("target-name").value = name;
    byId("target-handle").value = handle;
    byId("message-text").value = text;
    state.media = media;
    state.fixture = fixture;
    renderMedia();
    inspect();
  });

  byId("btn-reset-sandbox").addEventListener("click", () => {
    slider.value = 0;
    valLabel.textContent = "0%";
    slider.setAttribute("aria-valuenow", "0");
    slider.setAttribute("aria-valuetext", "0% channel degradation");
    byId("sandbox-homoglyph").checked = false;
    byId("sandbox-urgency").checked = false;
    byId("sandbox-canary").checked = false;

    if (state.originalBundle) {
      byId("target-name").value = state.originalBundle.targetName;
      byId("target-handle").value = state.originalBundle.targetHandle;
      byId("message-text").value = state.originalBundle.messageText;
      state.media = structuredClone(state.originalBundle.media);
      state.fixture = state.originalBundle.fixture ? structuredClone(state.originalBundle.fixture) : null;
      renderMedia();
    }
    invalidate();
    status("Sandbox perturbations reset. Original evidence restored.");
  });
}

function exportDossier() {
  if (!state.verdict) return;
  const payload = JSON.stringify(state.verdict, null, 2);
  const blob = new Blob([payload], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `trustguard-case-${state.verdict.verdictId}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function copyBrief() {
  if (!state.verdict) return;
  const v = state.verdict;
  const vec = v.calibratedTrustVector;
  const brief = [
    `=== TrustGuard Digital Trust Incident Brief ===`,
    `Case ID: ${v.verdictId}`,
    `Evaluated At: ${v.evaluatedAt}`,
    `Assessment Tier: ${v.assessmentTier}`,
    ``,
    `Calibrated 5D Trust Vector:`,
    `  • S_media (Media Synthesis):        ${vec.mediaSynthesisScore.toFixed(2)}`,
    `  • S_cross (Cross-Modal Discordance):${vec.crossModalDiscordanceScore.toFixed(2)}`,
    `  • S_ident (Identity Mismatch):       ${vec.identityMismatchScore.toFixed(2)}`,
    `  • S_context (Contextual Anomaly):   ${vec.contextualAnomalyScore.toFixed(2)}`,
    `  • U_epistemic (Uncertainty):         ${vec.epistemicUncertainty.toFixed(2)}`,
    ``,
    `Core Finding: ${v.verdictSummary?.headline || ""} — ${v.verdictSummary?.coreAnomaly || ""}`,
    `Judicial Ruling: ${v.adversarialDialectic?.judicialSynthesis || "Human verification required"}`,
    `Notice: ${v.verdictSummary?.noScoreIsProofNotice || "No score is proof"}`
  ].join("\n");
  if (copyStatusTimer) { clearTimeout(copyStatusTimer); copyStatusTimer = null; }
  try {
    await navigator.clipboard.writeText(brief);
    const statusEl = byId("copy-brief-status");
    if (statusEl) {
      statusEl.textContent = "✓ Brief copied to clipboard";
      copyStatusTimer = setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 3000);
    }
  } catch {
    const statusEl = byId("copy-brief-status");
    if (statusEl) statusEl.textContent = "Clipboard access unavailable; use JSON export";
  }
}

byId("scenario-select").addEventListener("change", scenarioChanged);
byId("btn-run-inspection").addEventListener("click", inspect);
byId("media-dropzone").addEventListener("click", () => byId("file-input").click());
byId("file-input").addEventListener("change", event => chooseFiles(event.target.files));
byId("media-dropzone").addEventListener("dragover", event => { event.preventDefault(); byId("media-dropzone").classList.add("dragging"); });
byId("media-dropzone").addEventListener("dragleave", () => byId("media-dropzone").classList.remove("dragging"));
byId("media-dropzone").addEventListener("drop", event => { event.preventDefault(); byId("media-dropzone").classList.remove("dragging"); chooseFiles(event.dataTransfer.files); });
byId("clear-media").addEventListener("click", () => chooseFiles([]));
for (const id of ["target-name", "target-handle", "message-text"]) byId(id).addEventListener("input", onInputChange);
for (const id of ["analyst-id", "audit-notes"]) byId(id).addEventListener("input", updateAudit);
byId("final-decision").addEventListener("input", updateAudit);
byId("final-decision").addEventListener("change", updateAudit);
byId("btn-sign-audit").addEventListener("click", signAudit);
byId("btn-canary").addEventListener("click", generateCanary);
if (byId("btn-export-dossier")) byId("btn-export-dossier").addEventListener("click", exportDossier);
if (byId("btn-copy-brief")) byId("btn-copy-brief").addEventListener("click", copyBrief);
const btnCopyCanary = byId("btn-copy-canary");
if (btnCopyCanary) {
  btnCopyCanary.addEventListener("click", async () => {
    const out = byId("canary-output");
    if (!out.value) return;
    const st = byId("canary-copy-status");
    try {
      await navigator.clipboard.writeText(out.value);
      if (st) {
        st.textContent = "✓ Marked text copied";
        setTimeout(() => { if (st) st.textContent = ""; }, 3000);
      }
    } catch {
      out.select();
      document.execCommand("copy");
      if (st) {
        st.textContent = "✓ Marked text copied";
        setTimeout(() => { if (st) st.textContent = ""; }, 3000);
      }
    }
  });
}

initSandbox();
health();
setInterval(health, 30000);
