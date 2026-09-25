/**
 * AC-2: Lifecycle, monitoring, debouncing, and memory disposal tests for TrustGuard extension.
 * Tests Start/Stop, SPA navigations, mutation bursts, request rate-limits, and pixel disposal.
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

function mockVerdict(complete = true) {
  return {
    continuousAuthenticityScore: 0.82,
    inspectionComplete: complete,
    label: complete ? "REVIEW_EVIDENCE" : "INCOMPLETE_EVIDENCE",
    modalitiesEvaluated: complete ? ["image", "text"] : ["text"],
    calibratedTrustVector: {
      mediaSynthesisScore: 0.05,
      crossModalDiscordanceScore: 0.0,
      identityMismatchScore: 0.1,
      contextualAnomalyScore: 0.05,
      epistemicUncertainty: 0.60
    },
    evidenceLedger: [{ polarity: "green_flag", finding: "Standard identity signals verified." }],
    verificationPlaybook: [{ step: 1, action: "Verify", instruction: "Check independent channel." }]
  };
}

class VirtualClock {
  constructor() {
    this.currentTime = 100000;
    this.timers = new Map();
    this.intervals = new Map();
    this._nextId = 1;
  }

  now() {
    return this.currentTime;
  }

  setTimeout(callback, delay = 0) {
    const id = this._nextId++;
    this.timers.set(id, { callback, runAt: this.currentTime + delay });
    return id;
  }

  clearTimeout(id) {
    this.timers.delete(id);
  }

  setInterval(callback, interval = 0) {
    const id = this._nextId++;
    this.intervals.set(id, { callback, interval, nextRun: this.currentTime + interval });
    return id;
  }

  clearInterval(id) {
    this.intervals.delete(id);
  }

  async advanceBy(ms) {
    const target = this.currentTime + ms;
    while (this.currentTime < target) {
      // Find the next timer or interval to run
      let nextAction = null;
      let nextActionTime = target + 1;
      let isInterval = false;
      let actionId = null;

      for (const [id, timer] of this.timers.entries()) {
        if (timer.runAt <= target && timer.runAt < nextActionTime) {
          nextAction = timer.callback;
          nextActionTime = timer.runAt;
          isInterval = false;
          actionId = id;
        }
      }

      for (const [id, iv] of this.intervals.entries()) {
        if (iv.nextRun <= target && iv.nextRun < nextActionTime) {
          nextAction = iv.callback;
          nextActionTime = iv.nextRun;
          isInterval = true;
          actionId = id;
        }
      }

      if (!nextAction || nextActionTime > target) {
        this.currentTime = target;
        break;
      }

      this.currentTime = nextActionTime;
      if (isInterval) {
        const iv = this.intervals.get(actionId);
        if (iv) iv.nextRun = this.currentTime + iv.interval;
      } else {
        this.timers.delete(actionId);
      }

      await nextAction();
    }
  }
}

function createLifecycleHarness({
  route = "/alice",
  handle = "alice",
  displayName = "Alice Example",
  evaluate = null
} = {}) {
  const clock = new VirtualClock();
  const fixture = createXFixture({ handle, displayName, bio: "Public bio only." });
  const body = fixture.body;
  const main = fixture.main;

  const sent = [];
  const sentPayloadReferences = [];
  let messageListener;
  let observerInstances = [];
  let mutationCallbacks = [];

  class MockMutationObserver {
    constructor(callback) {
      this.callback = callback;
      this.observed = false;
      observerInstances.push(this);
      mutationCallbacks.push(callback);
    }
    observe(target, options) {
      this.target = target;
      this.options = options;
      this.observed = true;
    }
    disconnect() {
      this.observed = false;
      observerInstances = observerInstances.filter(obs => obs !== this);
      mutationCallbacks = mutationCallbacks.filter(cb => cb !== this.callback);
    }
  }

  const context = {
    location: {
      origin: "https://x.com",
      hostname: "x.com",
      pathname: route
    },
    URL,
    Date: { now: () => clock.now() },
    console,
    setTimeout: (cb, delay) => clock.setTimeout(cb, delay),
    clearTimeout: id => clock.clearTimeout(id),
    setInterval: (cb, iv) => clock.setInterval(cb, iv),
    clearInterval: id => clock.clearInterval(id),
    MutationObserver: MockMutationObserver,
    document: {
      body,
      hidden: false,
      addEventListener() {},
      getElementById: id => body.children.find(node => node.id === id) || (body.shadow?.id === id ? body.shadow : null),
      querySelector: selector => selector === "main" ? main : body.querySelector(selector),
      querySelectorAll: selector => body.querySelectorAll(selector),
      createElement(tag) {
        const element = new SimulatedElement(tag);
        if (tag.toLowerCase() === "canvas") {
          element.getContext = () => ({
            drawImage() {},
            getImageData() {
              return { data: new Uint8ClampedArray(64 * 64 * 4).fill(128) };
            }
          });
        }
        return element;
      }
    },
    chrome: {
      runtime: {
        id: "extension-id",
        onMessage: {
          addListener(listener) { messageListener = listener; }
        },
        async sendMessage(request) {
          sent.push(JSON.parse(JSON.stringify(request.payload)));
          sentPayloadReferences.push(request.payload);
          if (evaluate) return evaluate(request);
          return { success: true, verdict: mockVerdict(true) };
        }
      }
    }
  };

  vm.createContext(context);
  for (const filename of ["verdict-ui.js", "content.js"]) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, "..", filename), "utf8"), context);
  }

  return {
    context,
    clock,
    body,
    main,
    sent,
    sentPayloadReferences,
    get activeObservers() { return observerInstances.filter(o => o.observed); },
    get activeTimersCount() { return clock.timers.size; },
    get activeIntervalsCount() { return clock.intervals.size; },
    triggerMutation(records = [{ addedNodes: [new SimulatedElement("div")], removedNodes: [], target: body }]) {
      mutationCallbacks.forEach(cb => cb(records));
    },
    message: message => new Promise(resolve => messageListener(message, { id: "extension-id" }, resolve))
  };
}

// =========================================================
// Lifecycle, Monitoring, Debouncing & Pixel Disposal Tests
// =========================================================

test("Lifecycle: repeated Start and Stop cycles maintain exactly one observer and timer set", async () => {
  const app = createLifecycleHarness();

  // 1. Initial State: Idle
  assert.equal(app.activeObservers.length, 0);
  assert.equal(app.activeIntervalsCount, 0);

  // 2. Start monitoring
  const start1 = await app.message({ type: "INSPECT_PROFILE" });
  assert.equal(start1.success, true);
  assert.equal(app.activeObservers.length, 1);
  assert.equal(app.activeIntervalsCount, 1); // 1 routeTimer
  assert.equal(app.body.children.some(c => c.id === "trustguard-profile-panel"), true);

  // 3. Redundant start call does not duplicate observers or timers
  await app.message({ type: "INSPECT_PROFILE" });
  assert.equal(app.activeObservers.length, 1);
  assert.equal(app.activeIntervalsCount, 1);

  // 4. Stop monitoring
  const stop1 = await app.message({ type: "STOP_INSPECTION" });
  assert.equal(stop1.success, true);
  assert.equal(stop1.enabled, false);
  assert.equal(app.activeObservers.length, 0);
  assert.equal(app.activeIntervalsCount, 0);
  assert.equal(app.activeTimersCount, 0);
  assert.equal(app.body.children.some(c => c.id === "trustguard-profile-panel"), false);

  // 5. Querying state reports disabled
  const state = await app.message({ type: "GET_INSPECTION_STATE" });
  assert.equal(state.enabled, false);

  // 6. Resume monitoring again
  const start2 = await app.message({ type: "INSPECT_PROFILE" });
  assert.equal(start2.success, true);
  assert.equal(app.activeObservers.length, 1);
  assert.equal(app.activeIntervalsCount, 1);
  assert.equal(app.body.children.some(c => c.id === "trustguard-profile-panel"), true);

  // 7. Stop cleanly
  await app.message({ type: "STOP_INSPECTION" });
  assert.equal(app.activeObservers.length, 0);
  assert.equal(app.activeIntervalsCount, 0);
});

test("Lifecycle: rapid same-tab SPA navigation during in-flight inspection discards stale result", async () => {
  let finishPendingInspection;
  const app = createLifecycleHarness({
    evaluate: () => new Promise(resolve => { finishPendingInspection = resolve; })
  });

  // Start inspection on /alice
  const pendingPromise = app.message({ type: "INSPECT_PROFILE" });

  // While in-flight, URL pathname changes to /bob (SPA route change)
  app.context.location.pathname = "/bob";

  // Server completes the /alice inspection
  finishPendingInspection({ success: true, verdict: mockVerdict(true) });

  const result = await pendingPromise;
  assert.equal(result.success, false);
  assert.match(result.error, /profile changed during inspection/u);

  // The panel for /alice must NOT be rendered on /bob
  assert.equal(app.body.children.some(c => c.id === "trustguard-profile-panel"), false);
});

test("Lifecycle: navigation to non-profile feed or messages clears active panel immediately", async () => {
  const app = createLifecycleHarness();
  await app.message({ type: "INSPECT_PROFILE" });
  assert.equal(app.body.children.some(c => c.id === "trustguard-profile-panel"), true);

  // User navigates to feed /home
  app.context.location.pathname = "/home";

  // Route timer ticks (1000ms)
  await app.clock.advanceBy(1000);

  // Active panel must be removed upon detecting route change
  assert.equal(app.body.children.some(c => c.id === "trustguard-profile-panel"), false);
});

test("Debouncing: mutation bursts are throttled to at most one request every 5 seconds", async () => {
  const app = createLifecycleHarness();
  await app.message({ type: "INSPECT_PROFILE" });
  assert.equal(app.sent.length, 1);

  // Profile bio updates in the DOM during mutation burst
  const desc = app.main.querySelector('[data-testid="UserDescription"]');
  desc.textContent = "New updated bio text after edit.";

  // Fire a burst of 50 mutations in quick succession
  for (let i = 0; i < 50; i++) {
    app.triggerMutation();
  }

  // Advance by 1000ms (debounce window)
  await app.clock.advanceBy(1000);
  // Still within 5 second throttle window from the first request
  assert.equal(app.sent.length, 1);

  // Fire another 20 mutations
  for (let i = 0; i < 20; i++) {
    app.triggerMutation();
  }

  // Advance to 5100ms total
  await app.clock.advanceBy(4100);

  // Exactly one follow-up inspection dispatched; not 71!
  assert.equal(app.sent.length, 2);
  assert.equal(app.sent[1].bioText, "New updated bio text after edit.");
});

test("Memory safety: raw sampled avatar pixels are strictly disposed after response or error", async () => {
  // Case A: Successful inspection
  const appSuccess = createLifecycleHarness();
  await appSuccess.message({ type: "INSPECT_PROFILE" });

  assert.equal(appSuccess.sent.length, 1);
  const payloadRef = appSuccess.sentPayloadReferences[0];
  // avatarPixels must be deleted from the payload object reference
  assert.equal("avatarPixels" in payloadRef, false);

  // Case B: In-flight network or service worker crash
  const appError = createLifecycleHarness({
    evaluate: () => Promise.reject(new Error("Local inspection engine crashed"))
  });

  const errorResult = await appError.message({ type: "INSPECT_PROFILE" });
  assert.equal(errorResult.success, false);
  const errorPayloadRef = appError.sentPayloadReferences[0];
  // avatarPixels must still be purged in the finally block
  assert.equal("avatarPixels" in errorPayloadRef, false);
});

test("Resilience: extension connection error recovers gracefully on subsequent attempt", async () => {
  let shouldFail = true;
  const app = createLifecycleHarness({
    evaluate: () => {
      if (shouldFail) throw new Error("Extension context invalidated.");
      return { success: true, verdict: mockVerdict(true) };
    }
  });

  // Attempt 1: Fails cleanly
  const failResult = await app.message({ type: "INSPECT_PROFILE" });
  assert.equal(failResult.success, false);
  assert.match(failResult.error, /Extension connection unavailable/u);

  // Attempt 2: Connection restored
  shouldFail = false;
  const successResult = await app.message({ type: "INSPECT_PROFILE" });
  assert.equal(successResult.success, true);
  assert.equal(app.body.children.some(c => c.id === "trustguard-profile-panel"), true);
});
