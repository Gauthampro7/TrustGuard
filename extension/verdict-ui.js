/** Shared, text-only result rendering for the popup and isolated in-page panel. */
"use strict";

globalThis.TrustGuardView = (() => {
  const dimensions = [
    ["mediaSynthesisScore", "Media anomaly"],
    ["crossModalDiscordanceScore", "Cross-modal discordance"],
    ["identityMismatchScore", "Identity mismatch"],
    ["contextualAnomalyScore", "Context anomaly"],
    ["epistemicUncertainty", "Uncertainty"]
  ];
  const number = value => typeof value === "number" && Number.isFinite(value)
    ? Math.max(0, Math.min(1, value)) : null;
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  }
  function list(parent, heading, values, className = "") {
    const section = node("section", undefined, "tg-section");
    section.append(node("h3", heading));
    const ul = node("ul", undefined, className);
    values.forEach(value => ul.append(node("li", value)));
    section.append(ul);
    parent.append(section);
  }
  function render(parent, verdict, observationNotes = []) {
    parent.replaceChildren();
    const complete = verdict.inspectionComplete === true;
    const score = number(verdict.continuousAuthenticityScore);
    parent.append(node("p", complete ? "Multimodal screening complete · identity unverified" :
      "Incomplete inspection · another readable modality is needed", "tg-state"));
    const label = String(verdict.label || "INCONCLUSIVE").replaceAll("_", " ");
    parent.append(node("p", label, "tg-label"));
    const index = node("div", undefined, "tg-index");
    index.append(node("strong", complete && score !== null ? `${Math.round(score * 100)} / 100` : "—"));
    index.append(node("span", "Continuous authenticity index"));
    parent.append(index);
    parent.append(node("p", "Heuristic support index, not a probability or proof. Higher values do not verify identity.", "tg-muted"));
    parent.append(node("p", `Evaluated modalities: ${(verdict.modalitiesEvaluated || []).join(", ") || "not reported"}.`, "tg-muted"));

    const vector = node("section", undefined, "tg-section");
    vector.append(node("h3", "Calibrated 5D Trust Vector"));
    vector.append(node("p", "Higher values indicate more anomalies or uncertainty. Missing evidence can suppress anomaly values.", "tg-muted"));
    dimensions.forEach(([key, title]) => {
      const value = number(verdict.calibratedTrustVector?.[key]);
      const row = node("div", undefined, "tg-vector-row");
      const description = node("div", undefined, "tg-vector-label");
      description.append(node("span", title), node("strong", value === null ? "Unavailable" : value.toFixed(2)));
      const meter = node("meter");
      meter.min = 0;
      meter.max = 1;
      meter.value = value ?? 0;
      meter.setAttribute("aria-label", title);
      row.append(description, meter);
      vector.append(row);
    });
    parent.append(vector);

    const ledger = verdict.evidenceLedger || [];
    list(parent, "Red flags", ledger.filter(item => item.polarity === "red_flag").map(item => item.finding)
      .concat(ledger.some(item => item.polarity === "red_flag") ? [] : ["No measured red flags; this does not establish authenticity."]), "tg-red");
    list(parent, "Green anchors / mitigating evidence", ledger.filter(item => item.polarity === "green_flag").map(item => item.finding)
      .concat(ledger.some(item => item.polarity === "green_flag") ? [] : ["No independent identity anchor was established."]), "tg-green");
    const limitations = [...observationNotes, ...ledger.filter(item => item.polarity === "neutral_uncertain").map(item => item.finding)];
    if (limitations.length) list(parent, "Evidence limitations", [...new Set(limitations)]);
    const dialectic = verdict.adversarialDialectic;
    if (dialectic) {
      const debate = node("section", undefined, "tg-section");
      debate.append(node("h3", "Adversarial dialectic"));
      [["Prosecution", dialectic.prosecutionArgument], ["Defense", dialectic.defenseMitigation],
        ["Synthesis", dialectic.judicialSynthesis]].forEach(([role, argument]) => {
        if (argument) debate.append(node("h4", role), node("p", argument));
      });
      parent.append(debate);
    }
    list(parent, "Independent human verification", (verdict.verificationPlaybook || []).map(step => `${step.step}. ${step.action}: ${step.instruction}`));
    parent.append(node("p", verdict.noScoreIsProofNotice || "No score is proof. Verify independently before taking action.", "tg-notice"));
  }
  return { render, node };
})();
