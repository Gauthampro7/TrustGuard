const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class Element {
  constructor(tag = "div", text = "") { this.tagName = tag; this.textContent = text; this.children = []; this.style = {}; this.hidden = false; }
  append(...nodes) { nodes.forEach(node => { node.parentElement = this; this.children.push(node); }); }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  setAttribute(name, value) { this[name] = value; }
  addEventListener() {}
  getClientRects() { return [{}]; }
  querySelectorAll() { return []; }
  closest() { return null; }
  attachShadow() { this.shadow = new Element(); return this.shadow; }
  remove() { if (this.parentElement) this.parentElement.children = this.parentElement.children.filter(child => child !== this); }
}

function verdict(complete = true) {
  return {
    continuousAuthenticityScore: .72, inspectionComplete: complete,
    label: complete ? "REVIEW_EVIDENCE" : "INCOMPLETE_EVIDENCE", modalitiesEvaluated: complete ? ["image", "text"] : ["text"],
    calibratedTrustVector: { mediaSynthesisScore: .1, crossModalDiscordanceScore: 0,
      identityMismatchScore: .2, contextualAnomalyScore: .1, epistemicUncertainty: .7 },
    evidenceLedger: [{ polarity: "red_flag", finding: "A lookalike needs review." }],
    verificationPlaybook: [{ step: 1, action: "Verify", instruction: "Contact a known source." }]
  };
}

function harness({ route = "/alice", handle = "alice", cors = false, evaluate } = {}) {
  const body = new Element("body");
  const name = new Element("div");
  name.querySelectorAll = () => [new Element("span", "Alice Example"), new Element("span", `@${handle}`)];
  const image = new Element("img");
  Object.assign(image, { complete: true, naturalWidth: 128, naturalHeight: 128, src: "https://pbs.twimg.com/avatar.png" });
  image.closest = selector => selector === "a" ? { href: `https://x.com/${handle}/photo` } : null;
  const main = new Element("main");
  main.querySelectorAll = selector => selector.includes("UserName") ? [name] :
    selector.includes("UserDescription") ? [new Element("div", "Public bio only.")] : selector.includes("UserAvatar") ? [image] : [];
  const sent = [];
  const sentReferences = [];
  const timers = new Map();
  let messageListener;
  let nextTimer = 0;
  const context = {
    location: { origin: "https://x.com", hostname: "x.com", pathname: route },
    URL, Date, console,
    setTimeout: callback => { const id = ++nextTimer; timers.set(id, callback); return id; },
    setInterval: callback => { const id = ++nextTimer; timers.set(id, callback); return id; },
    clearTimeout: id => timers.delete(id), clearInterval: id => timers.delete(id),
    MutationObserver: class { observe() {} disconnect() {} },
    document: {
      body, hidden: false, addEventListener() {},
      getElementById: id => body.children.find(node => node.id === id),
      querySelector: selector => selector === "main" ? main : null,
      createElement(tag) {
        const element = new Element(tag);
        if (tag === "canvas") element.getContext = () => ({ drawImage() {}, getImageData() {
          if (cors) throw new Error("tainted canvas");
          return { data: new Uint8ClampedArray(64 * 64 * 4).fill(128) };
        } });
        return element;
      }
    },
    chrome: { runtime: { id: "extension-id", onMessage: { addListener(listener) { messageListener = listener; } },
      async sendMessage(request) {
        sent.push(JSON.parse(JSON.stringify(request.payload)));
        sentReferences.push(request.payload);
        return evaluate ? evaluate(request) : { success: true, verdict: verdict(!cors) };
      }
    } }
  };
  vm.createContext(context);
  for (const filename of ["verdict-ui.js", "content.js"]) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, "..", filename), "utf8"), context);
  }
  return {
    context, sent, sentReferences, timers, body,
    message: message => new Promise(resolve => messageListener(message, { id: "extension-id" }, resolve))
  };
}

test("does not inspect or monitor until the popup opts in", () => {
  const app = harness();
  assert.equal(app.sent.length, 0);
  assert.equal(app.timers.size, 0);
});

test("rejects feeds, direct messages, and post pages", async () => {
  for (const route of ["/home", "/messages", "/i/chat", "/alice/status/123", "/search"]) {
    const app = harness({ route });
    const response = await app.message({ type: "INSPECT_PROFILE" });
    assert.equal(response.success, false, route);
    assert.equal(app.sent.length, 0, route);
    assert.equal(app.timers.size, 0, route);
  }
});

test("refuses a stale profile header after SPA navigation", async () => {
  const app = harness({ route: "/bob", handle: "alice" });
  const response = await app.message({ type: "INSPECT_PROFILE" });
  assert.equal(response.success, false);
  assert.equal(app.sent.length, 0);
});

test("sends a bounded avatar sample and removes raw pixels after evaluation", async () => {
  const app = harness();
  const response = await app.message({ type: "INSPECT_PROFILE", referenceHandle: "@original" });
  assert.equal(response.success, true);
  assert.equal(app.sent[0].avatarPixels.length, 64);
  assert.equal(app.sent[0].avatarPixels[0].length, 64);
  assert.equal(app.sent[0].referenceHandle, "original");
  assert.equal(app.sent[0].bioText, "Public bio only.");
  assert.equal("avatarPixels" in app.sentReferences[0], false);
  assert.equal(app.body.children.length, 1);
});

test("reports CORS-blocked images honestly without an image payload", async () => {
  const app = harness({ cors: true });
  const response = await app.message({ type: "INSPECT_PROFILE" });
  assert.equal("avatarPixels" in app.sent[0], false);
  assert.equal(response.verdict.inspectionComplete, false);
  assert.match(response.observationNotes[0], /CORS/u);
  const contents = element => [element.textContent || "", ...(element.children || []).map(contents)].join(" ");
  const rendered = contents(app.body.children[0].shadow);
  assert.match(rendered, /Incomplete inspection/u);
  assert.doesNotMatch(rendered, /72 \/ 100/u);
  assert.match(rendered, /Calibrated 5D Trust Vector/u);
  assert.match(rendered, /Independent human verification/u);
});

test("discards cross-route responses and clears the previous panel", async () => {
  let finish;
  const app = harness({ evaluate: () => new Promise(resolve => { finish = resolve; }) });
  const work = app.message({ type: "INSPECT_PROFILE" });
  app.context.location.pathname = "/bob";
  finish({ success: true, verdict: verdict() });
  const response = await work;
  assert.equal(response.success, false);
  assert.match(response.error, /profile changed/u);
  assert.equal(app.body.children.length, 0);
});

test("stopping an in-flight inspection prevents late rendering", async () => {
  let finish;
  const app = harness({ evaluate: () => new Promise(resolve => { finish = resolve; }) });
  const work = app.message({ type: "INSPECT_PROFILE" });
  await app.message({ type: "STOP_INSPECTION" });
  finish({ success: true, verdict: verdict() });
  const response = await work;
  assert.equal(response.success, false);
  assert.equal(response.enabled, false);
  assert.equal(app.body.children.length, 0);
  assert.equal(app.timers.size, 0);
});
