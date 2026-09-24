"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("inspection-form");
  const inspectButton = document.getElementById("btn-inspect");
  const stopButton = document.getElementById("btn-stop");
  const status = document.getElementById("engine-status");
  const feedback = document.getElementById("feedback");
  const result = document.getElementById("inspection-result");
  const profile = document.getElementById("profile-name");

  function display(response) {
    const enabled = response?.enabled === true;
    stopButton.hidden = !enabled;
    status.textContent = enabled ? "Live in tab" : "Idle";
    result.hidden = !response?.success;
    profile.hidden = !response?.profile;
    if (response?.profile) profile.textContent = `${response.profile.platform} / @${response.profile.handle}`;
    if (response?.success && response.verdict) {
      globalThis.TrustGuardView.render(result, response.verdict, response.observationNotes);
      feedback.textContent = response.verdict.inspectionComplete
        ? "Review the evidence and complete independent verification."
        : "Partial observations only. Add a readable image and text in the dashboard to complete inspection.";
    } else if (response?.error) {
      feedback.textContent = response.error;
      status.textContent = enabled ? "Paused / retry" : "Unavailable";
      result.replaceChildren();
    }
  }

  async function messageTab(message) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("There is no active profile tab.");
    try {
      return await chrome.tabs.sendMessage(tab.id, message);
    } catch (_) {
      throw new Error("Open a public profile on X, Instagram, or LinkedIn. Reload that tab if TrustGuard was just installed.");
    }
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    inspectButton.disabled = true;
    feedback.textContent = "Inspecting visible profile evidence with the local engine…";
    status.textContent = "Inspecting";
    result.hidden = true;
    try {
      display(await messageTab({ type: "INSPECT_PROFILE", referenceHandle: document.getElementById("reference-handle").value }));
    } catch (error) { display({ success: false, error: error.message }); }
    finally { inspectButton.disabled = false; }
  });

  stopButton.addEventListener("click", async () => {
    try {
      await messageTab({ type: "STOP_INSPECTION" });
      display({ success: false, enabled: false });
      result.replaceChildren();
      feedback.textContent = "Monitoring stopped. No profile evidence is retained by this popup.";
    } catch (error) { display({ success: false, error: error.message }); }
  });

  messageTab({ type: "GET_INSPECTION_STATE" }).then(display).catch(() => {});
});
