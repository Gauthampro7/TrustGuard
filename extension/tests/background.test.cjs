const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function harness(fetch) {
  let listener;
  const context = {
    URL, AbortController, setTimeout, clearTimeout, fetch,
    chrome: { runtime: { id: "extension-id", onMessage: { addListener(value) { listener = value; } } } }
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "background.js"), "utf8"), context);
  return (sender = { id: "extension-id", tab: { id: 1 }, url: "https://x.com/alice" }) =>
    new Promise(resolve => listener({ type: "EVALUATE_PROFILE", payload: { handle: "alice" } }, sender, resolve));
}

test("background rejects requests outside supported content tabs", async () => {
  let fetched = false;
  const send = harness(async () => { fetched = true; });
  const reply = await send({ id: "extension-id", url: "https://evil.example/", tab: { id: 1 } });
  assert.equal(reply.success, false);
  assert.equal(fetched, false);
});

test("background surfaces API validation failures instead of rendering them as verdicts", async () => {
  const send = harness(async () => ({ ok: false, status: 422 }));
  const reply = await send();
  assert.equal(reply.success, false);
  assert.match(reply.error, /incomplete or invalid/u);
});

test("background rejects legacy scalar-only API responses", async () => {
  const send = harness(async () => ({ ok: true, json: async () => ({ continuousAuthenticityScore: .9 }) }));
  const reply = await send();
  assert.equal(reply.success, false);
  assert.match(reply.error, /outdated result/u);
});

test("background sends only to loopback with no cookies, redirects, or cache", async () => {
  const expected = { calibratedTrustVector: {}, evidenceLedger: [], verificationPlaybook: [] };
  const send = harness(async (url, options) => {
    assert.equal(url, "http://127.0.0.1:8000/api/v1/extension/evaluate-profile");
    assert.equal(options.credentials, "omit");
    assert.equal(options.redirect, "error");
    assert.equal(options.cache, "no-store");
    return { ok: true, json: async () => expected };
  });
  const reply = await send();
  assert.equal(reply.success, true);
  assert.equal(reply.verdict, expected);
});
