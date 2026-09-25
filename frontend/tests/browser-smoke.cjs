/* Real Chromium smoke against a running local backend. No mocked inspection results. */
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const base = "http://127.0.0.1:8000";
const artifacts = path.resolve(__dirname, "../../scratch/dashboard-smoke");
const scenarios = ["ceo-wire-scam", "homoglyph-clone", "wifi-compression-edge-case", "creator-copyright"];
const dimensionKeys = { media: "mediaSynthesisScore", cross: "crossModalDiscordanceScore", ident: "identityMismatchScore", context: "contextualAnomalyScore", uncertainty: "epistemicUncertainty" };

async function inspect(page) {
  const responsePromise = page.waitForResponse(response => response.url() === `${base}/api/v1/inspect` && response.request().method() === "POST");
  await page.locator("#btn-run-inspection").click();
  const response = await responsePromise;
  assert.equal(response.status(), 200, await response.text());
  const verdict = await response.json();
  await page.waitForFunction(id => document.querySelector("#run-metadata").textContent.includes(id), verdict.verdictId);
  for (const [id, key] of Object.entries(dimensionKeys)) {
    assert.equal(await page.locator(`#val-${id}`).textContent(), verdict.calibratedTrustVector[key].toFixed(2));
  }
  assert.equal(await page.locator("#prosecution-arg").textContent(), verdict.adversarialDialectic.prosecutionArgument);
  assert.equal(await page.locator("#defense-arg").textContent(), verdict.adversarialDialectic.defenseMitigation);
  assert.equal(await page.locator("#judicial-synthesis").textContent(), verdict.adversarialDialectic.judicialSynthesis);
  assert.equal(await page.locator("#playbook-steps input").count(), verdict.verificationPlaybook.length);
  assert.equal(await page.locator("#btn-sign-audit").isDisabled(), true);
  for (const [polarity, id] of Object.entries({ red_flag: "red-flags-list", green_flag: "green-flags-list", neutral_uncertain: "neutral-flags-list" })) {
    const count = verdict.evidenceLedger.filter(item => item.polarity === polarity).length;
    assert.equal(await page.locator(`#${id} li:not(.empty-state)`).count(), count);
  }
  return verdict;
}

async function scenario(page, id) {
  await page.locator("#scenario-select").selectOption(id);
  await page.waitForFunction(() => document.querySelector("#operation-status").textContent.startsWith("Simulated case loaded"));
  assert.equal(await page.locator("#scenario-notice").isVisible(), true);
  const result = await inspect(page);
  assert.match(await page.locator("#verdict-tier").textContent(), /SIMULATION/);
  assert.ok(result.innovationMetadata.evaluatedModalities.split(",").length >= 2);
  return result;
}

async function noOverflow(page, label) {
  const size = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
  assert.ok(size.document <= size.viewport, `${label}: horizontal overflow ${JSON.stringify(size)}`);
}

async function main() {
  fs.mkdirSync(artifacts, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1080 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  const errors = [];
  const inspectRequests = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("request", request => { if (request.url() === `${base}/api/v1/inspect`) inspectRequests.push(request.postDataJSON()); });
  const report = { scenarios: [], checks: [], screenshots: [] };
  try {
    await page.goto(`${base}/dashboard/`, { waitUntil: "networkidle" });
    await page.waitForFunction(() => document.querySelector("#health-label").textContent === "Local engine connected");
    await noOverflow(page, "Desktop initial");
    await page.locator("#btn-run-inspection").click();
    assert.match(await page.locator("#operation-status").textContent(), /two modalities/);
    assert.equal(inspectRequests.length, 0);
    report.checks.push("Missing evidence blocked before any inspection request");

    for (const id of scenarios) {
      const result = await scenario(page, id);
      report.scenarios.push({ id, tier: result.assessmentTier, vector: result.calibratedTrustVector, elapsedMs: result.innovationMetadata.elapsedMs, ledgerSignals: result.evidenceLedger.length });
      if (id === "wifi-compression-edge-case") {
        assert.ok(result.calibratedTrustVector.epistemicUncertainty >= .5);
        assert.match(await page.locator("#uncertainty-note").textContent(), /Elevated uncertainty/);
      }
      if (id === "creator-copyright") {
        assert.equal(result.tripwireStatus.tripwireTriggered, true);
        assert.equal(await page.locator("#tripwire-banner").isVisible(), true);
      }
      await noOverflow(page, `Desktop ${id}`);
    }
    report.checks.push("All four real scenario requests rendered exact API vector, ledger, dialectic, tripwire and playbook values");

    const checks = page.locator("#playbook-steps input");
    await page.locator("#analyst-id").fill("BROWSER_SMOKE_ANALYST");
    await page.locator("#audit-notes").fill("Simulation exercise: independent checks remain inconclusive. No external incident is attested.");
    await page.locator("#final-decision").selectOption("INCONCLUSIVE");
    for (let i = 0; i < await checks.count() - 1; i += 1) await checks.nth(i).check();
    assert.equal(await page.locator("#btn-sign-audit").isDisabled(), true);
    await checks.last().check();
    assert.equal(await page.locator("#btn-sign-audit").isEnabled(), true);
    const auditPromise = page.waitForResponse(response => response.url().includes("/sign-audit"));
    await page.locator("#btn-sign-audit").click();
    const auditResponse = await auditPromise;
    assert.equal(auditResponse.status(), 200, await auditResponse.text());
    await page.locator("#audit-links").waitFor({ state: "visible" });
    const pdfUrl = await page.locator("#audit-links a").first().getAttribute("href");
    const pdf = await context.request.get(pdfUrl);
    assert.equal(pdf.status(), 200);
    assert.equal((await pdf.body()).subarray(0, 4).toString(), "%PDF");
    const verificationUrl = await page.locator("#audit-links a").nth(1).getAttribute("href");
    const verification = await context.request.get(verificationUrl);
    assert.equal(verification.status(), 200);
    report.certificateVerification = await verification.json();
    assert.equal(report.certificateVerification.valid, true);
    report.checks.push("All independent steps, analyst notes and explicit decision gate audit; PDF and integrity links work");

    await page.locator(".canary-card summary").click();
    await page.locator("#canary-text").fill("TrustGuard browser smoke public bio. Contact me through known channels.");
    await page.locator("#btn-canary").click();
    await page.locator("#canary-result").waitFor({ state: "visible" });
    const markedText = await page.locator("#canary-output").inputValue();
    assert.ok(markedText.length > (await page.locator("#canary-text").inputValue()).length);
    assert.match(await page.locator("#canary-notice").textContent(), /session/);
    report.checks.push("Canary generated through local API with explicit session scope");

    await page.locator("#scenario-select").selectOption("none");
    const png = await page.evaluate(() => {
      const canvas = document.createElement("canvas");
      canvas.width = 160; canvas.height = 120;
      const context = canvas.getContext("2d");
      const gradient = context.createLinearGradient(0, 0, 160, 120);
      gradient.addColorStop(0, "#346987"); gradient.addColorStop(1, "#efc984");
      context.fillStyle = gradient; context.fillRect(0, 0, 160, 120);
      context.fillStyle = "#354964"; context.fillRect(35, 30, 80, 65);
      return canvas.toDataURL("image/png").split(",")[1];
    });
    await page.locator("#file-input").setInputFiles({ name: "local-smoke-frame.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") });
    await page.waitForFunction(() => document.querySelector("#operation-status").textContent.startsWith("Media prepared"));
    await page.locator("#message-text").fill(`${markedText} This accompanying context provides details about a routine site update. Please verify the original source through a known directory before taking any action. No payment or unusual authorization is requested. <img src=x onerror=alert(1)>`);
    const custom = await inspect(page);
    assert.equal(await page.locator("#scenario-notice").isVisible(), false);
    assert.ok(!/SIMULATION/.test(await page.locator("#verdict-tier").textContent()));
    assert.equal(custom.tripwireStatus.tripwireTriggered, true);
    const sent = inspectRequests.at(-1);
    assert.deepEqual(sent.evidenceItems.map(item => item.modality).sort(), ["image", "text"]);
    assert.equal(sent.evidenceItems[0].samples.imagePixels[0].length, 128);
    assert.equal(sent.evidenceItems[0].samples.imagePixels.length, 96);
    assert.equal(sent.evidenceItems[0].mediaUri, undefined);
    assert.ok(!JSON.stringify(sent).includes("data:image"));
    assert.equal(await page.locator(".analysis-panel img").count(), 0);
    report.checks.push("Custom image + text decoded to bounded grayscale numeric samples; raw file never posted; generated canary detected; HTML-like text safe");

    const sampleRate = 22050;
    const samples = sampleRate;
    const wav = Buffer.alloc(44 + samples * 2);
    wav.write("RIFF", 0); wav.writeUInt32LE(wav.length - 8, 4); wav.write("WAVEfmt ", 8);
    wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
    wav.writeUInt32LE(sampleRate, 24); wav.writeUInt32LE(sampleRate * 2, 28);
    wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34); wav.write("data", 36); wav.writeUInt32LE(samples * 2, 40);
    for (let i = 0; i < samples; i += 1) wav.writeInt16LE(Math.round(9000 * Math.sin(i * 2 * Math.PI * 240 / sampleRate)), 44 + i * 2);
    await page.locator("#file-input").setInputFiles({ name: "synthetic-smoke-tone.wav", mimeType: "audio/wav", buffer: wav });
    await page.waitForFunction(() => document.querySelector("#operation-status").textContent.startsWith("Media prepared"));
    await inspect(page);
    const audioItem = inspectRequests.at(-1).evidenceItems[0];
    assert.equal(audioItem.modality, "audio");
    assert.equal(audioItem.samples.sampleRate, 16000);
    assert.equal(audioItem.samples.audioSamples.length, 16000);
    assert.ok(audioItem.samples.audioSamples.every(value => Math.abs(value) <= 1));
    report.checks.push("Real WAV browser decode resamples 22.05 kHz audio to bounded 16 kHz samples");

    // Self-generated one-second blue/white geometric VP8/WebM fixture (160 x 120, no audio or personal media).
    const videoBytes = Buffer.from("GkXfo59ChoEBQveBAULygQRC84EIQoKEd2VibUKHgQJChYECGFOAZwH/////////EU2bdKtNu4tTq4QVSalmU6yBoU27i1OrhBZUrmtTrIHLTbuMU6uEElTDZ1OsggEY7AEAAAAAAABoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVSalmpSrXsYMPQkBNgIxMYXZmNjEuNy4xMDBXQYxMYXZmNjEuNy4xMDAWVK5ryK4BAAAAAAAAP9eBAXPFiNxuiApjJ1BhnIEAIrWcg3VuZIiBAIaFVl9WUDiDgQEj44OEBfXhAOCQsIGguoF4moECVbCEVbmBARJUw2fXc3OfY8CAZ8iZRaOHRU5DT0RFUkSHjExhdmY2MS43LjEwMHNzsmPAi2PFiNxuiApjJ1BhZ8ihRaOHRU5DT0RFUkSHlExhdmM2MS4xOS4xMDAgbGlidnB4H0O2dUIs54EAo0DqgQAAgBALAJ0BKqAAeAAARwiFhYiFhIgCAgJ11Qv4D+KvKVMR4D+AP7AJgB/UD0Vf7B/AQ1qgrhjpCSpGIm0A5Mjz6esiqxnCS8tA/i/Rzw6YtN8x7WCMD/4gZgLhjpCYAqyIPUAA/v9NDd6pROEf/FZmdine5O//9tu/+9NZ/+pP//ai/I0GiW//68oVckHJnRYPv3kNNCBIAAAACAGAQBJAPP/af/+8xJ/+oO//aILjb7oX8n/n//+SBu08qgD42TsHUPV5glqpP/w07f3KBuQoed0qvxIfaMLDABSfl1fVCACsArAAAAAAo8OBAGQAcQIABRAQABzCMAsglXqgCqBSDaUeAAAAAAAAAiwAAAAAAAAAAAAABACSAAAAAAAABEgBfIAAAAAAAgYAAAAAo6eBAMgAsQIABRAQABgAGIgv9AAQyEvONrCeQ1oAOOSfgAAAAAAAAACjnIEBLACRAgAFEBAAGAAYWC/0AAiEQ8iPKqvDAACjnIEBkACRAgAFEBAAGAAYWC/0AAiEQ8iPKqvDAACjnIEB9ACRAgAFEBAAGAAYWC/0AAiEQ8iPKqvDAACjnIECWACRAgAFEBAAGAAYWC/0AAiEQ8iPKqvDAACjmIECvAARAgAFEBAUYABhYL/QACICBDLAAKOcgQMgAJECAAUQEAAYABhYL/QACIRDyI8qq8MAAKOcgQOEAJECAAUQEAAYABhYL/QACIRDyI8qq8MAAA==", "base64");
    await page.locator("#file-input").setInputFiles({ name: "synthetic-smoke-video.webm", mimeType: "video/webm", buffer: Buffer.from(videoBytes) });
    await page.waitForFunction(() => document.querySelector("#operation-status").textContent.startsWith("Media prepared"));
    await inspect(page);
    const videoItem = inspectRequests.at(-1).evidenceItems[0];
    assert.equal(videoItem.modality, "video");
    assert.ok(videoItem.samples.imagePixels.length >= 16);
    assert.equal(videoItem.samples.audioSamples, undefined);
    assert.match(await page.locator("#media-list").textContent(), /one video frame only/);
    report.checks.push("Real WebM browser decode submits one visual frame and clearly marks missing audio/sync analysis");

    // Hold a real backend response, change the evidence, then release the old result.
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    let responseReady;
    const received = new Promise(resolve => { responseReady = resolve; });
    let routeDone;
    const finished = new Promise(resolve => { routeDone = resolve; });
    await page.route(`${base}/api/v1/inspect`, async route => {
      try {
        const response = await route.fetch();
        responseReady();
        await gate;
        await route.fulfill({ response });
      } finally { routeDone(); }
    }, { times: 1 });
    await page.locator("#btn-run-inspection").click();
    await received;
    await page.locator("#message-text").fill("Revised evidence after the previous request. This must invalidate the old assessment.");
    release();
    await finished;
    await page.waitForTimeout(100);
    assert.equal(await page.locator("#verdict-tier").textContent(), "READY TO INSPECT");
    assert.equal(await page.locator("#val-media").textContent(), "—");
    assert.equal(await page.locator("#btn-sign-audit").isDisabled(), true);
    report.checks.push("Changing evidence invalidates pending results and prevents stale audit sign-off");

    await scenario(page, "homoglyph-clone");
    await page.locator(".canary-card summary").click();
    await page.screenshot({ path: path.join(artifacts, "dashboard-desktop.png"), fullPage: true });
    report.screenshots.push("scratch/dashboard-smoke/dashboard-desktop.png");
    await page.setViewportSize({ width: 390, height: 844 });
    await noOverflow(page, "390px mobile");
    await page.screenshot({ path: path.join(artifacts, "dashboard-mobile.png"), fullPage: true });
    report.screenshots.push("scratch/dashboard-smoke/dashboard-mobile.png");
    assert.deepEqual(errors, [], `Browser errors: ${errors.join("; ")}`);
    report.checks.push("1440px desktop and 390px mobile have no horizontal overflow or browser errors");
    fs.writeFileSync(path.join(artifacts, "report.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify({ passed: true, checks: report.checks, scenarios: report.scenarios, screenshots: report.screenshots }, null, 2));
  } catch (error) {
    await page.screenshot({ path: path.join(artifacts, "failure.png"), fullPage: true }).catch(() => {});
    console.error("Browser errors:", errors);
    console.error("UI status:", await page.locator("#operation-status").textContent().catch(() => "unavailable"));
    throw error;
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
