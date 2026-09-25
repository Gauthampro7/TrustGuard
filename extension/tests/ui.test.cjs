/**
 * AC-3: Popup and panel usability, accessibility, untrusted text, and incomplete-advisory tests.
 * Validates complete vs incomplete states, XSS prevention, homoglyph formatting, ARIA/keyboard use.
 */
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
  SimulatedElement,
  createXFixture
} = require("./fixtures.cjs");

function loadTrustGuardView() {
  const context = {
    document: {
      createElement: tag => new SimulatedElement(tag)
    },
    globalThis: {}
  };
  vm.createContext(context);
  const code = fs.readFileSync(path.join(__dirname, "..", "verdict-ui.js"), "utf8");
  vm.runInContext(code, context);
  return context.globalThis.TrustGuardView;
}

function loadContentScriptApp({
  route = "/alice",
  handle = "alice",
  evaluate = null
} = {}) {
  const fixture = createXFixture({ handle, bio: "Public bio only." });
  const body = fixture.body;
  const main = fixture.main;

  let messageListener;
  const context = {
    location: { origin: "https://x.com", hostname: "x.com", pathname: route },
    URL,
    Date,
    console,
    setTimeout: (cb) => { cb(); return 1; },
    clearTimeout: () => {},
    setInterval: () => 1,
    clearInterval: () => {},
    MutationObserver: class { observe() {} disconnect() {} },
    document: {
      body,
      hidden: false,
      addEventListener() {},
      getElementById: id => body.children.find(node => node.id === id) || (body.shadow?.id === id ? body.shadow : null),
      querySelector: selector => selector === "main" ? main : body.querySelector(selector),
      querySelectorAll: selector => body.querySelectorAll(selector),
      createElement: tag => {
        const el = new SimulatedElement(tag);
        if (tag.toLowerCase() === "canvas") {
          el.getContext = () => ({
            drawImage() {},
            getImageData: () => ({ data: new Uint8ClampedArray(64 * 64 * 4).fill(128) })
          });
        }
        return el;
      }
    },
    chrome: {
      runtime: {
        id: "extension-id",
        onMessage: {
          addListener(listener) { messageListener = listener; }
        },
        async sendMessage(request) {
          if (evaluate) return evaluate(request);
          return {
            success: true,
            verdict: {
              continuousAuthenticityScore: 0.88,
              inspectionComplete: true,
              label: "REVIEW_EVIDENCE",
              modalitiesEvaluated: ["image", "text"],
              calibratedTrustVector: {
                mediaSynthesisScore: 0.1,
                crossModalDiscordanceScore: 0.0,
                identityMismatchScore: 0.05,
                contextualAnomalyScore: 0.1,
                epistemicUncertainty: 0.55
              },
              evidenceLedger: [{ polarity: "red_flag", finding: "Lookalike Cyrillic character in handle." }],
              verificationPlaybook: [{ step: 1, action: "Verify", instruction: "Check secondary channel." }]
            }
          };
        }
      }
    }
  };

  vm.createContext(context);
  for (const filename of ["verdict-ui.js", "content.js"]) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, "..", filename), "utf8"), context);
  }

  return {
    body,
    message: message => new Promise(resolve => messageListener(message, { id: "extension-id" }, resolve))
  };
}

// =========================================================
// AC-3: UI Usability, Accessibility, and Security Tests
// =========================================================

test("UI: complete advisory renders status, score index, evaluated modalities, and 5D vector", () => {
  const { render } = loadTrustGuardView();
  const container = new SimulatedElement("div");

  const verdict = {
    continuousAuthenticityScore: 0.85,
    inspectionComplete: true,
    label: "REVIEW_EVIDENCE",
    modalitiesEvaluated: ["image", "text"],
    calibratedTrustVector: {
      mediaSynthesisScore: 0.15,
      crossModalDiscordanceScore: 0.0,
      identityMismatchScore: 0.20,
      contextualAnomalyScore: 0.10,
      epistemicUncertainty: 0.50
    },
    evidenceLedger: [
      { polarity: "red_flag", finding: "Subtle high-frequency spatial artifact." },
      { polarity: "green_flag", finding: "Account age matches historical record." }
    ],
    verificationPlaybook: [
      { step: 1, action: "Confirm", instruction: "Reach out via known telephone directory." }
    ]
  };

  render(container, verdict);

  const text = container.textContent;
  assert.match(text, /Multimodal screening complete · identity unverified/u);
  assert.match(text, /85 \/ 100/u);
  assert.match(text, /Evaluated modalities: image, text/u);
  assert.match(text, /Calibrated 5D Trust Vector/u);
  assert.match(text, /0\.15/u);
  assert.match(text, /Subtle high-frequency spatial artifact/u);
  assert.match(text, /Account age matches historical record/u);
  assert.match(text, /1\. Confirm: Reach out via known telephone directory/u);
});

test("UI: incomplete advisory withholds authenticity score and reports missing modality note", () => {
  const { render } = loadTrustGuardView();
  const container = new SimulatedElement("div");

  const verdict = {
    continuousAuthenticityScore: 0.75, // Backend might calculate heuristic, but UI must withhold
    inspectionComplete: false,
    label: "INCOMPLETE_EVIDENCE",
    modalitiesEvaluated: ["text"],
    calibratedTrustVector: {
      mediaSynthesisScore: null,
      crossModalDiscordanceScore: null,
      identityMismatchScore: 0.15,
      contextualAnomalyScore: 0.10,
      epistemicUncertainty: 0.85
    },
    evidenceLedger: [
      { polarity: "neutral_uncertain", finding: "Avatar image unreadable due to canvas security." }
    ],
    verificationPlaybook: []
  };

  const notes = ["The browser blocked avatar pixel access (usually image CORS). No image was analyzed; the profile result is incomplete."];

  render(container, verdict, notes);

  const text = container.textContent;
  // State notice must clearly communicate incomplete inspection
  assert.match(text, /Incomplete inspection · another readable modality is needed/u);
  // Score must be withheld as a dash '—', never a number!
  assert.doesNotMatch(text, /75 \/ 100/u);
  assert.match(text, /—/u);
  assert.match(text, /Evaluated modalities: text/u);
  assert.match(text, /Evidence limitations/u);
  assert.match(text, /usually image CORS/u);
});

test("UI: unavailable dimensions are clearly displayed as 'Unavailable' without breaking meters", () => {
  const { render } = loadTrustGuardView();
  const container = new SimulatedElement("div");

  const verdict = {
    continuousAuthenticityScore: 0.5,
    inspectionComplete: false,
    label: "INCONCLUSIVE",
    calibratedTrustVector: {
      mediaSynthesisScore: null,
      crossModalDiscordanceScore: null,
      identityMismatchScore: 0.30,
      contextualAnomalyScore: null,
      epistemicUncertainty: 0.90
    },
    evidenceLedger: [],
    verificationPlaybook: []
  };

  render(container, verdict);

  const meters = container.querySelectorAll("meter");
  assert.equal(meters.length, 5);

  const text = container.textContent;
  // Dimensions with null must render "Unavailable"
  const unavailableOccurrences = (text.match(/Unavailable/gu) || []).length;
  assert.equal(unavailableOccurrences, 3); // mediaSynthesisScore, crossModalDiscordanceScore, contextualAnomalyScore
  // Active dimension rendered with 2 decimal places
  assert.match(text, /0\.30/u);
  assert.match(text, /0\.90/u);
});

test("Security: profile and verdict text is treated strictly as untrusted text, never executable markup", () => {
  const { render } = loadTrustGuardView();
  const container = new SimulatedElement("div");

  // XSS injection vectors in all text fields
  const xssPayload = "<script>alert('xss')</script><img src=x onerror=alert(1)><iframe src='javascript:alert(2)'>";
  const verdict = {
    continuousAuthenticityScore: 0.9,
    inspectionComplete: true,
    label: xssPayload,
    modalitiesEvaluated: [xssPayload],
    calibratedTrustVector: {
      mediaSynthesisScore: 0.1,
      crossModalDiscordanceScore: 0.0,
      identityMismatchScore: 0.0,
      contextualAnomalyScore: 0.0,
      epistemicUncertainty: 0.5
    },
    evidenceLedger: [
      { polarity: "red_flag", finding: `Red flag: ${xssPayload}` },
      { polarity: "green_flag", finding: `Green anchor: ${xssPayload}` },
      { polarity: "neutral_uncertain", finding: `Limitation: ${xssPayload}` }
    ],
    adversarialDialectic: {
      prosecutionArgument: `Prosecution: ${xssPayload}`,
      defenseMitigation: `Defense: ${xssPayload}`,
      judicialSynthesis: `Synthesis: ${xssPayload}`
    },
    verificationPlaybook: [
      { step: 1, action: xssPayload, instruction: xssPayload }
    ],
    noScoreIsProofNotice: xssPayload
  };

  render(container, verdict, [`Observation note: ${xssPayload}`]);

  // Assert that NO script, img, or iframe tags were created in the DOM
  assert.equal(container.querySelectorAll("script").length, 0);
  assert.equal(container.querySelectorAll("iframe").length, 0);
  assert.equal(container.querySelectorAll("img").length, 0);

  // The text content safely contains the raw tags as inert text
  assert.equal(container.textContent.includes("<script>"), true);
  assert.equal(container.textContent.includes("<img src=x"), true);
});

test("Homoglyphs: code-point explanations and mixed scripts are safely and accurately rendered", () => {
  const { render } = loadTrustGuardView();
  const container = new SimulatedElement("div");

  const homoglyphFinding = "Lookalike characters detected: 'а́pple' (U+0430 Cyrillic Small Letter A + U+0301 Combining Acute Accent) imitating Latin 'apple'.";
  const mixedScriptFinding = "Mixed-script display name contains 3 Cyrillic characters (U+0441, U+043E, U+0440) alongside Latin.";

  const verdict = {
    continuousAuthenticityScore: 0.40,
    inspectionComplete: true,
    label: "SUSPICIOUS_IDENTITY",
    modalitiesEvaluated: ["text"],
    calibratedTrustVector: {
      mediaSynthesisScore: 0.0,
      crossModalDiscordanceScore: 0.0,
      identityMismatchScore: 0.85,
      contextualAnomalyScore: 0.20,
      epistemicUncertainty: 0.45
    },
    evidenceLedger: [
      { polarity: "red_flag", finding: homoglyphFinding },
      { polarity: "red_flag", finding: mixedScriptFinding }
    ],
    verificationPlaybook: [
      { step: 1, action: "Inspect Unicode", instruction: "Examine character code points in security console." }
    ]
  };

  render(container, verdict);

  const text = container.textContent;
  assert.match(text, /U\+0430 Cyrillic Small Letter A/u);
  assert.match(text, /U\+0301 Combining Acute Accent/u);
  assert.match(text, /U\+0441, U\+043E, U\+0440/u);
});

test("Accessibility: in-page panel toggles via button ARIA attributes and closes on Escape", async () => {
  const app = loadContentScriptApp();

  // Inspect profile to inject in-page panel
  await app.message({ type: "INSPECT_PROFILE" });

  const host = app.body.children.find(c => c.id === "trustguard-profile-panel");
  assert.ok(host, "Panel host must be injected into document body");

  const shadow = host.shadow;
  const panel = shadow.querySelector("#trustguard-details");
  const button = shadow.querySelector("button.pill");

  assert.ok(panel, "Panel element must exist in shadow DOM");
  assert.ok(button, "Trigger button must exist in shadow DOM");

  // Initial State: panel hidden, aria-expanded="false"
  assert.equal(panel.hidden, true);
  assert.equal(button.getAttribute("aria-expanded"), "false");
  assert.equal(button.getAttribute("aria-controls"), "trustguard-details");

  // User clicks trigger pill button -> panel opens
  button.dispatchEvent({ type: "click" });
  assert.equal(panel.hidden, false);
  assert.equal(button.getAttribute("aria-expanded"), "true");

  // User presses Escape key inside shadow DOM -> panel closes, aria-expanded="false"
  let focusCalled = false;
  button.focus = () => { focusCalled = true; };

  shadow.dispatchEvent({ type: "keydown", key: "Escape" });
  assert.equal(panel.hidden, true);
  assert.equal(button.getAttribute("aria-expanded"), "false");
  assert.equal(focusCalled, true, "Trigger button must receive focus when closed via Escape");
});

test("Popup: offline / engine failure surfaces error cleanly and allows retry", () => {
  const { render } = loadTrustGuardView();
  const resultContainer = new SimulatedElement("div");
  const feedback = new SimulatedElement("p");
  const status = new SimulatedElement("span");
  const inspectButton = new SimulatedElement("button");

  function simulatePopupDisplay(response) {
    const enabled = response?.enabled === true;
    status.textContent = enabled ? "Live in tab" : "Idle";
    resultContainer.hidden = !response?.success;
    if (response?.success && response.verdict) {
      render(resultContainer, response.verdict, response.observationNotes);
      feedback.textContent = response.verdict.inspectionComplete
        ? "Review the evidence and complete independent verification."
        : "Partial observations only. Add a readable image and text in the dashboard to complete inspection.";
    } else if (response?.error) {
      feedback.textContent = response.error;
      status.textContent = enabled ? "Paused / retry" : "Unavailable";
      resultContainer.replaceChildren();
    }
    inspectButton.disabled = false;
  }

  // Engine offline response
  simulatePopupDisplay({
    success: false,
    error: "Local engine unavailable. Start TrustGuard at 127.0.0.1:8000."
  });

  assert.equal(status.textContent, "Unavailable");
  assert.equal(feedback.textContent, "Local engine unavailable. Start TrustGuard at 127.0.0.1:8000.");
  assert.equal(resultContainer.hidden, true);
  assert.equal(resultContainer.children.length, 0);
  assert.equal(inspectButton.disabled, false, "Inspect button must remain enabled for user retry");
});
