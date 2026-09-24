/** Relays consented DOM observations to the loopback API without retaining media. */
"use strict";

const PROFILE_ENDPOINT = "http://127.0.0.1:8000/api/v1/extension/evaluate-profile";
const PROFILE_HOSTS = new Set([
  "x.com", "www.x.com", "twitter.com", "www.twitter.com",
  "instagram.com", "www.instagram.com", "linkedin.com", "www.linkedin.com"
]);

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request?.type !== "EVALUATE_PROFILE") return false;
  let validSender = false;
  try {
    const source = new URL(sender.url || "");
    validSender = sender.id === chrome.runtime.id && !!sender.tab &&
      source.protocol === "https:" && PROFILE_HOSTS.has(source.hostname);
  } catch (_) { /* A missing or malformed sender cannot request inspection. */ }
  if (!validSender) {
    sendResponse({ success: false, error: "Inspection must originate from a supported profile tab." });
    return false;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  (async () => {
    try {
      const response = await fetch(PROFILE_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request.payload),
        signal: controller.signal,
        credentials: "omit",
        cache: "no-store",
        redirect: "error"
      });
      if (!response.ok) {
        throw new Error(response.status === 422
          ? "The profile observations were incomplete or invalid. Reload the profile and inspect again."
          : `The local inspection service returned HTTP ${response.status}.`);
      }
      const verdict = await response.json();
      if (!verdict.calibratedTrustVector || !Array.isArray(verdict.evidenceLedger) ||
          !Array.isArray(verdict.verificationPlaybook)) {
        throw new Error("The local service returned an outdated result. Restart the current TrustGuard backend.");
      }
      sendResponse({ success: true, verdict });
    } catch (error) {
      sendResponse({
        success: false,
        error: error.name === "AbortError" ? "The local inspection timed out. Try again." :
          error instanceof TypeError ? "Local engine unavailable. Start TrustGuard at 127.0.0.1:8000." : error.message
      });
    } finally {
      clearTimeout(timeout);
    }
  })();
  return true;
});
