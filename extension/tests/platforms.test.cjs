const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
  SimulatedElement,
  createXFixture,
  createInstagramFixture,
  createLinkedInFixture
} = require("./fixtures.cjs");

function mockVerdict(complete = true) {
  return {
    continuousAuthenticityScore: 0.85,
    inspectionComplete: complete,
    label: complete ? "REVIEW_EVIDENCE" : "INCOMPLETE_EVIDENCE",
    modalitiesEvaluated: complete ? ["image", "text"] : ["text"],
    calibratedTrustVector: {
      mediaSynthesisScore: 0.05,
      crossModalDiscordanceScore: 0.0,
      identityMismatchScore: 0.1,
      contextualAnomalyScore: 0.05,
      epistemicUncertainty: 0.65
    },
    evidenceLedger: [{ polarity: "green_flag", finding: "Standard digital trust indicators." }],
    verificationPlaybook: [{ step: 1, action: "Verify", instruction: "Confirm via established contact." }]
  };
}

function createPlatformHarness({
  platform = "twitter",
  route = "/alice",
  fixture = null,
  cors = false,
  evaluate = null
} = {}) {
  const hostMap = {
    twitter: "x.com",
    instagram: "instagram.com",
    linkedin: "linkedin.com"
  };
  const hostname = hostMap[platform] || "x.com";
  const origin = `https://${hostname}`;

  const head = fixture?.head || new SimulatedElement("head");
  const body = fixture?.body || new SimulatedElement("body");
  const main = fixture?.main || body.querySelector("main") || new SimulatedElement("main");

  const sent = [];
  const sentReferences = [];
  const timers = new Map();
  let messageListener;
  let nextTimer = 0;

  const context = {
    location: { origin, hostname, pathname: route },
    URL,
    Date,
    console,
    setTimeout: callback => { const id = ++nextTimer; timers.set(id, callback); return id; },
    setInterval: callback => { const id = ++nextTimer; timers.set(id, callback); return id; },
    clearTimeout: id => timers.delete(id),
    clearInterval: id => timers.delete(id),
    MutationObserver: class {
      observe() {}
      disconnect() {}
    },
    document: {
      head,
      body,
      hidden: false,
      addEventListener() {},
      getElementById: id => body.children.find(node => node.id === id) || (body.shadow?.id === id ? body.shadow : null),
      querySelector: selector => {
        if (selector === "main") return main;
        if (selector.startsWith("link")) return head.querySelector(selector);
        return body.querySelector(selector) || head.querySelector(selector);
      },
      querySelectorAll: selector => {
        return [...head.querySelectorAll(selector), ...body.querySelectorAll(selector)];
      },
      createElement(tag) {
        const element = new SimulatedElement(tag);
        if (tag.toLowerCase() === "canvas") {
          element.getContext = () => ({
            drawImage() {},
            getImageData() {
              if (cors) throw new Error("tainted canvas (CORS)");
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
          sentReferences.push(request.payload);
          return evaluate ? evaluate(request) : { success: true, verdict: mockVerdict(!cors) };
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
    sent,
    sentReferences,
    timers,
    body,
    head,
    message: message => new Promise(resolve => messageListener(message, { id: "extension-id" }, resolve))
  };
}

// ==========================================
// 1. X (Twitter) Adapter Fixture Matrix
// ==========================================

test("X: positive fixture extracts header, bio, and avatar pixels", async () => {
  const fixture = createXFixture({
    handle: "alice",
    displayName: "Alice Example",
    bio: "Principal Security Architect."
  });
  const app = createPlatformHarness({ platform: "twitter", route: "/alice", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal(app.sent.length, 1);
  const payload = app.sent[0];
  assert.equal(payload.platform, "twitter");
  assert.equal(payload.handle, "alice");
  assert.equal(payload.displayName, "Alice Example");
  assert.equal(payload.bioText, "Principal Security Architect.");
  assert.equal(payload.avatarPixels.length, 64);
  assert.equal(payload.avatarPixels[0].length, 64);
});

test("X: feed posts and DMs never enter extracted payload", async () => {
  const feedSpam = "URGENT CRYPTO GIVEAWAY: Send 1 ETH to double it!";
  const dmSecret = "Confidential DM: Check out my private repo link";
  const fixture = createXFixture({
    handle: "alice",
    displayName: "Alice",
    bio: "Public bio only.",
    feedPosts: [feedSpam],
    dms: [dmSecret]
  });
  const app = createPlatformHarness({ platform: "twitter", route: "/alice", fixture });
  await app.message({ type: "INSPECT_PROFILE" });

  const payload = app.sent[0];
  assert.doesNotMatch(payload.bioText, new RegExp(feedSpam, "u"));
  assert.doesNotMatch(payload.bioText, new RegExp(dmSecret, "u"));
  assert.doesNotMatch(payload.displayName, new RegExp(feedSpam, "u"));
  assert.equal(payload.bioText, "Public bio only.");
});

test("X: negative - missing header fails closed without payload", async () => {
  const fixture = createXFixture({ missingHeader: true });
  const app = createPlatformHarness({ platform: "twitter", route: "/alice", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, false);
  assert.match(response.error, /header was not found/u);
  assert.equal(app.sent.length, 0);
});

test("X: negative - mismatched header handle fails closed", async () => {
  const fixture = createXFixture({ handle: "alice", mismatchedHeader: true });
  const app = createPlatformHarness({ platform: "twitter", route: "/alice", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, false);
  assert.match(response.error, /matching public profile header was not found/u);
  assert.equal(app.sent.length, 0);
});

test("X: negative - hidden duplicate header is ignored in favor of visible header", async () => {
  const fixture = createXFixture({ handle: "alice", displayName: "Real Alice", hiddenDuplicate: true });
  const app = createPlatformHarness({ platform: "twitter", route: "/alice", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal(app.sent[0].displayName, "Real Alice");
  assert.equal(app.sent[0].handle, "alice");
});

test("X: negative - unavailable avatar falls back to text-only advisory", async () => {
  const fixture = createXFixture({ handle: "alice", avatarValid: false });
  const app = createPlatformHarness({ platform: "twitter", route: "/alice", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal("avatarPixels" in app.sent[0], false);
  assert.match(response.observationNotes[0], /No readable loaded profile avatar/u);
});

// ==========================================
// 2. Instagram Adapter Fixture Matrix
// ==========================================

test("Instagram: positive fixture extracts header, bio, and avatar pixels", async () => {
  const fixture = createInstagramFixture({
    handle: "carol_art",
    displayName: "Carol Art",
    bio: "Visual artist and creative director."
  });
  const app = createPlatformHarness({ platform: "instagram", route: "/carol_art", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal(app.sent.length, 1);
  const payload = app.sent[0];
  assert.equal(payload.platform, "instagram");
  assert.equal(payload.handle, "carol_art");
  assert.equal(payload.displayName, "Carol Art");
  assert.equal(payload.bioText, "Visual artist and creative director.");
  assert.equal(payload.avatarPixels.length, 64);
});

test("Instagram: post captions and direct messages never enter payload", async () => {
  const postSpam = "Post Caption: Buy limited edition NFTs now!";
  const dmSecret = "Instagram DM: Here is the secret coupon code";
  const fixture = createInstagramFixture({
    handle: "carol_art",
    displayName: "Carol",
    bio: "Art portfolio only.",
    feedPosts: [postSpam],
    dms: [dmSecret]
  });
  const app = createPlatformHarness({ platform: "instagram", route: "/carol_art", fixture });
  await app.message({ type: "INSPECT_PROFILE" });

  const payload = app.sent[0];
  assert.doesNotMatch(payload.bioText, new RegExp(postSpam, "u"));
  assert.doesNotMatch(payload.bioText, new RegExp(dmSecret, "u"));
  assert.equal(payload.bioText, "Art portfolio only.");
});

test("Instagram: negative - missing header fails closed", async () => {
  const fixture = createInstagramFixture({ missingHeader: true });
  const app = createPlatformHarness({ platform: "instagram", route: "/carol_art", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, false);
  assert.match(response.error, /header was not found/u);
  assert.equal(app.sent.length, 0);
});

test("Instagram: negative - mismatched header handle fails closed", async () => {
  const fixture = createInstagramFixture({ handle: "carol_art", mismatchedHeader: true });
  const app = createPlatformHarness({ platform: "instagram", route: "/carol_art", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, false);
  assert.match(response.error, /header does not yet match this profile address/u);
  assert.equal(app.sent.length, 0);
});

test("Instagram: negative - hidden duplicate header is ignored", async () => {
  const fixture = createInstagramFixture({ handle: "carol_art", displayName: "Real Carol", hiddenDuplicate: true });
  const app = createPlatformHarness({ platform: "instagram", route: "/carol_art", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal(app.sent[0].displayName, "Real Carol");
  assert.equal(app.sent[0].handle, "carol_art");
});

test("Instagram: negative - reserved and non-profile routes are rejected", async () => {
  for (const route of ["/direct", "/explore", "/reels", "/p/C31xyz", "/stories/carol_art"]) {
    const app = createPlatformHarness({ platform: "instagram", route });
    const response = await app.message({ type: "INSPECT_PROFILE" });
    assert.equal(response.success, false, route);
    assert.match(response.error, /Feeds, posts, and messages are not inspected/u, route);
    assert.equal(app.sent.length, 0, route);
  }
});

test("Instagram: negative - CORS canvas rejection reports incomplete advisory", async () => {
  const fixture = createInstagramFixture({ handle: "carol_art" });
  const app = createPlatformHarness({ platform: "instagram", route: "/carol_art", fixture, cors: true });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal("avatarPixels" in app.sent[0], false);
  assert.equal(response.verdict.inspectionComplete, false);
  assert.match(response.observationNotes[0], /CORS/u);
});

test("Instagram: negative - unavailable avatar falls back cleanly", async () => {
  const fixture = createInstagramFixture({ handle: "carol_art", avatarValid: false });
  const app = createPlatformHarness({ platform: "instagram", route: "/carol_art", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal("avatarPixels" in app.sent[0], false);
  assert.match(response.observationNotes[0], /No readable loaded profile avatar/u);
});

// ==========================================
// 3. LinkedIn Adapter Fixture Matrix
// ==========================================

test("LinkedIn: positive fixture extracts name, headline, and avatar pixels", async () => {
  const fixture = createLinkedInFixture({
    handle: "dan-smith",
    displayName: "Dan Smith",
    headline: "VP of Engineering at CloudSecure | Distributed Systems"
  });
  const app = createPlatformHarness({ platform: "linkedin", route: "/in/dan-smith", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal(app.sent.length, 1);
  const payload = app.sent[0];
  assert.equal(payload.platform, "linkedin");
  assert.equal(payload.handle, "dan-smith");
  assert.equal(payload.displayName, "Dan Smith");
  assert.equal(payload.bioText, "VP of Engineering at CloudSecure | Distributed Systems");
  assert.equal(payload.avatarPixels.length, 64);
});

test("LinkedIn: feed updates and in-mail messages never enter payload", async () => {
  const feedSpam = "Feed Announcement: We just raised $50M Series B!";
  const inmailSecret = "InMail Confidential: Executive compensation details enclosed";
  const fixture = createLinkedInFixture({
    handle: "dan-smith",
    displayName: "Dan Smith",
    headline: "Head of Infrastructure",
    feedPosts: [feedSpam],
    dms: [inmailSecret]
  });
  const app = createPlatformHarness({ platform: "linkedin", route: "/in/dan-smith", fixture });
  await app.message({ type: "INSPECT_PROFILE" });

  const payload = app.sent[0];
  assert.doesNotMatch(payload.bioText, new RegExp(feedSpam, "u"));
  assert.doesNotMatch(payload.bioText, new RegExp(inmailSecret, "u"));
  assert.doesNotMatch(payload.displayName, new RegExp(feedSpam, "u"));
  assert.equal(payload.bioText, "Head of Infrastructure");
});

test("LinkedIn: negative - stale canonical route waits for navigation", async () => {
  const fixture = createLinkedInFixture({
    handle: "dan-smith",
    canonicalUrl: "https://www.linkedin.com/in/stale-prior-account"
  });
  const app = createPlatformHarness({ platform: "linkedin", route: "/in/dan-smith", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, false);
  assert.match(response.error, /Wait for LinkedIn to finish navigating/u);
  assert.equal(app.sent.length, 0);
});

test("LinkedIn: negative - malformed canonical URL fails closed", async () => {
  const fixture = createLinkedInFixture({
    handle: "dan-smith",
    canonicalUrl: "https://www.linkedin.com/in/%E0%A4%A"
  });
  const app = createPlatformHarness({ platform: "linkedin", route: "/in/dan-smith", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, false);
  assert.match(response.error, /profile address could not be matched/u);
  assert.equal(app.sent.length, 0);
});

test("LinkedIn: negative - missing header or name fails closed", async () => {
  const fixtureNoHeader = createLinkedInFixture({ missingHeader: true });
  const app1 = createPlatformHarness({ platform: "linkedin", route: "/in/dan-smith", fixture: fixtureNoHeader });
  const resp1 = await app1.message({ type: "INSPECT_PROFILE" });
  assert.equal(resp1.success, false);
  assert.match(resp1.error, /header was not found/u);

  const fixtureNoName = createLinkedInFixture({ missingName: true });
  const app2 = createPlatformHarness({ platform: "linkedin", route: "/in/dan-smith", fixture: fixtureNoName });
  const resp2 = await app2.message({ type: "INSPECT_PROFILE" });
  assert.equal(resp2.success, false);
  assert.match(resp2.error, /profile header was not found|profile name is not available/u);
});

test("LinkedIn: negative - hidden duplicate top-card is ignored", async () => {
  const fixture = createLinkedInFixture({ handle: "dan-smith", displayName: "Dan Real", hiddenDuplicate: true });
  const app = createPlatformHarness({ platform: "linkedin", route: "/in/dan-smith", fixture });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal(app.sent[0].displayName, "Dan Real");
});

test("LinkedIn: negative - non-profile routes are rejected before collection", async () => {
  for (const route of ["/feed", "/messaging", "/mynetwork", "/jobs", "/in"]) {
    const app = createPlatformHarness({ platform: "linkedin", route });
    const response = await app.message({ type: "INSPECT_PROFILE" });
    assert.equal(response.success, false, route);
    assert.match(response.error, /Open a public profile/u, route);
    assert.equal(app.sent.length, 0, route);
  }
});

test("LinkedIn: negative - CORS canvas rejection reports incomplete advisory", async () => {
  const fixture = createLinkedInFixture({ handle: "dan-smith" });
  const app = createPlatformHarness({ platform: "linkedin", route: "/in/dan-smith", fixture, cors: true });
  const response = await app.message({ type: "INSPECT_PROFILE" });

  assert.equal(response.success, true);
  assert.equal("avatarPixels" in app.sent[0], false);
  assert.equal(response.verdict.inspectionComplete, false);
  assert.match(response.observationNotes[0], /CORS/u);
});

test("Universal: malformed URL fails closed on all platforms", async () => {
  for (const [platform, route] of [["twitter", "/%E0%A4%A"], ["instagram", "/%E0%A4%A"], ["linkedin", "/in/%E0%A4%A"]]) {
    const app = createPlatformHarness({ platform, route });
    const response = await app.message({ type: "INSPECT_PROFILE" });
    assert.equal(response.success, false, platform);
    assert.match(response.error, /profile address is malformed/u, platform);
    assert.equal(app.sent.length, 0, platform);
  }
});
