/** Public profile header inspection. Collection starts only after popup consent. */
(() => {
  "use strict";
  const HOST_ID = "trustguard-profile-panel";
  const { node, render } = globalThis.TrustGuardView;
  const xReserved = new Set(["home", "explore", "notifications", "messages", "search", "i", "settings", "compose", "login", "logout", "signup", "intent", "tos", "privacy", "jobs"]);
  const instagramReserved = new Set(["accounts", "direct", "explore", "reels", "reel", "p", "stories", "about", "developer", "legal", "web", "challenge", "emails", "privacy", "push", "session", "api"]);
  let enabled = false;
  let referenceHandle = "";
  let route = location.origin + location.pathname;
  let generation = 0;
  let lastKey = "";
  let lastAttempt = 0;
  let cached = null;
  let pending = null;
  let timer;
  let routeTimer;
  let observer;

  const text = element => (element?.innerText || element?.textContent || "").replace(/\s+/gu, " ").trim();
  const visible = element => !!element && element.getClientRects().length > 0;
  const firstVisible = (root, selectors) => Array.from(root.querySelectorAll(selectors)).find(visible);
  const routeKey = () => location.origin + location.pathname;
  function removePanel() { document.getElementById(HOST_ID)?.remove(); }
  function updateRoute() {
    if (route === routeKey()) return false;
    route = routeKey();
    generation += 1;
    lastKey = "";
    cached = null;
    removePanel();
    return true;
  }

  function profileRoute() {
    const host = location.hostname.replace(/^www\./u, "");
    let parts;
    try { parts = location.pathname.split("/").filter(Boolean).map(decodeURIComponent); }
    catch (_) { throw new Error("The current profile address is malformed."); }
    if (host === "x.com" || host === "twitter.com") {
      if (!parts[0] || xReserved.has(parts[0].toLowerCase()) || parts.length > 2 ||
          (parts[1] && !["with_replies", "media", "highlights", "articles"].includes(parts[1]))) {
        throw new Error("Open a public X profile. Home feeds, posts, and messages are not inspected.");
      }
      return { platform: "twitter", handle: parts[0] };
    }
    if (host === "instagram.com") {
      if (parts.length !== 1 || instagramReserved.has(parts[0].toLowerCase())) {
        throw new Error("Open a public Instagram profile. Feeds, posts, and messages are not inspected.");
      }
      return { platform: "instagram", handle: parts[0] };
    }
    if (host === "linkedin.com" && parts.length === 2 && parts[0] === "in") {
      return { platform: "linkedin", handle: parts[1] };
    }
    throw new Error("Open a public profile on X, Instagram, or LinkedIn.");
  }

  function readProfile() {
    const identity = profileRoute();
    const main = document.querySelector("main");
    if (!main) throw new Error("The profile header has not loaded. Wait for the profile, then retry.");
    let displayName = "";
    let bioText = "";
    let avatar;
    if (identity.platform === "twitter") {
      const name = Array.from(main.querySelectorAll('[data-testid="UserName"]')).find(element =>
        visible(element) && !element.closest("article") &&
        Array.from(element.querySelectorAll("span")).some(span => text(span).toLowerCase() === `@${identity.handle}`.toLowerCase()));
      if (!name) throw new Error("A matching public profile header was not found. No feed content was collected.");
      displayName = text(Array.from(name.querySelectorAll("span")).find(span => text(span) && !text(span).startsWith("@")));
      const bio = Array.from(main.querySelectorAll('[data-testid="UserDescription"]')).find(element => visible(element) && !element.closest("article"));
      bioText = text(bio);
      avatar = Array.from(main.querySelectorAll('[data-testid^="UserAvatar-Container-"] img')).find(image => {
        const anchor = image.closest("a");
        if (!visible(image) || image.closest("article") || !anchor) return false;
        try { return decodeURIComponent(new URL(anchor.href).pathname).toLowerCase() === `/${identity.handle}/photo`.toLowerCase(); }
        catch (_) { return false; }
      });
    } else if (identity.platform === "instagram") {
      const header = firstVisible(main, "header");
      if (!header) throw new Error("A public Instagram profile header was not found.");
      const heading = Array.from(header.querySelectorAll("h1, h2, [data-testid='user-name']")).find(element =>
        text(element).replace(/^@/u, "").toLowerCase() === identity.handle.toLowerCase());
      if (!heading) throw new Error("The loaded Instagram header does not yet match this profile address.");
      const name = firstVisible(header, "[data-testid='profile-name'], h1");
      displayName = text(name) || identity.handle;
      const bio = firstVisible(header, "[data-testid='user-bio'], [data-testid='profile-bio'], .biography");
      // Only a profile biography/name container is eligible; never consume the page or post text.
      bioText = text(bio || (name && name !== heading ? name.parentElement : null));
      avatar = Array.from(header.querySelectorAll("img")).find(image => visible(image) &&
        ((image.alt || "").toLowerCase().includes(identity.handle.toLowerCase()) ||
         image.matches('[data-testid="user-avatar"], [data-testid="profile-avatar"]')));
    } else {
      const canonical = document.querySelector('link[rel="canonical"]')?.href;
      if (canonical) {
        try {
          if (decodeURIComponent(new URL(canonical).pathname).replace(/\/$/u, "").toLowerCase() !==
              decodeURIComponent(location.pathname).replace(/\/$/u, "").toLowerCase()) {
            throw new Error("Wait for LinkedIn to finish navigating to the public profile.");
          }
        } catch (error) {
          if (error.message?.includes("LinkedIn")) throw error;
          throw new Error("The profile address could not be matched.");
        }
      }
      const name = firstVisible(main, ".pv-top-card h1, section h1, h1.top-card-layout__title");
      const header = name?.closest("section, .pv-top-card, .top-card-layout");
      if (!name || !header) throw new Error("A public LinkedIn profile header was not found.");
      displayName = text(name);
      bioText = text(firstVisible(header, ".text-body-medium, .top-card-layout__headline"));
      avatar = firstVisible(header, "img.pv-top-card-profile-picture__image--show, img.pv-top-card-profile-picture__image, img.profile-photo-edit__preview, img.top-card-layout__entity-image");
    }
    if (!displayName) throw new Error("The public profile name is not available yet.");
    const payload = {
      ...identity,
      displayName: displayName.slice(0, 256),
      bioText: bioText.slice(0, 6000)
    };
    if (avatar?.currentSrc || avatar?.src) payload.avatarUrl = avatar.currentSrc || avatar.src;
    if (referenceHandle) payload.referenceHandle = referenceHandle;
    return { payload, avatar };
  }

  function sampleAvatar(image) {
    if (!image || !image.complete || image.naturalWidth < 16 || image.naturalHeight < 16) {
      return { note: "No readable loaded profile avatar was available. Add an image and text in the dashboard for a multimodal inspection." };
    }
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 64;
    try {
      const context = canvas.getContext("2d", { willReadFrequently: true });
      context.drawImage(image, 0, 0, 64, 64);
      const rgba = context.getImageData(0, 0, 64, 64).data;
      const pixels = Array.from({ length: 64 }, (_, y) => Array.from({ length: 64 }, (_, x) => {
        const i = (y * 64 + x) * 4;
        return Math.round(0.2126 * rgba[i] + 0.7152 * rgba[i + 1] + 0.0722 * rgba[i + 2]);
      }));
      return { pixels };
    } catch (_) {
      return { note: "The browser blocked avatar pixel access (usually image CORS). No image was analyzed; the profile result is incomplete." };
    } finally {
      canvas.width = canvas.height = 0;
    }
  }

  function showPanel(reply) {
    removePanel();
    const host = node("div");
    host.id = HOST_ID;
    host.style.cssText = "position:fixed!important;bottom:20px!important;right:20px!important;z-index:2147483647!important;max-width:calc(100vw - 32px)!important;";
    const shadow = host.attachShadow({ mode: "closed" });
    const style = node("style");
    style.textContent = `:host{font:13px/1.5 system-ui,sans-serif;color:#14243a}*{box-sizing:border-box}button{font:inherit;cursor:pointer}button:focus-visible{outline:3px solid #4a91fa;outline-offset:3px}.pill{padding:11px 15px;border:1px solid #8797af;border-radius:24px;background:#fff;color:#152b48;box-shadow:0 8px 28px #11244333}.panel{width:360px;max-width:calc(100vw - 40px);max-height:65vh;overflow:auto;background:#fff;border:1px solid #c6d3e2;border-radius:14px;padding:16px;margin-bottom:10px;box-shadow:0 8px 40px #11244333}[hidden]{display:none}h2,h3,h4,p{margin:0 0 8px}h2{font-size:17px}h3{font-size:13px}h4{font-size:12px;margin-top:10px}ul{padding-left:18px}li{margin-bottom:7px}.tg-section{border-top:1px solid #e2e8f0;margin-top:16px;padding-top:14px}.tg-muted,.tg-notice{font-size:11px;color:#506078}.tg-notice{margin-top:14px}.tg-state{font-weight:650;color:#805111}.tg-label{font-size:11px}.tg-index{display:flex;align-items:baseline;gap:10px;margin:12px 0}.tg-index strong{font-size:23px}.tg-index span{font-size:11px}.tg-vector-label{display:flex;justify-content:space-between}.tg-vector-row{margin:8px 0}meter{width:100%;height:10px}.tg-red li::marker{color:#b33345}.tg-green li::marker{color:#276b59}.stop{border:1px solid #c8d1df;background:#f8faff;padding:6px 10px;border-radius:8px;margin-top:10px}`;
    const panel = node("section", undefined, "panel");
    panel.id = "trustguard-details";
    panel.hidden = true;
    panel.append(node("h2", "TrustGuard · evidence first"));
    const result = node("div");
    if (reply.success) render(result, reply.verdict, reply.observationNotes);
    else result.append(node("p", reply.error));
    panel.append(result);
    const stopButton = node("button", "Stop monitoring this tab", "stop");
    stopButton.type = "button";
    stopButton.addEventListener("click", stop);
    panel.append(stopButton);
    let title = "TrustGuard · inspection unavailable";
    if (reply.success) {
      const flags = reply.verdict.evidenceLedger.filter(item => item.polarity === "red_flag").length;
      title = `TrustGuard · ${flags} red flag${flags === 1 ? "" : "s"} · ${reply.verdict.inspectionComplete ? "review evidence" : "incomplete"}`;
    }
    const button = node("button", title, "pill");
    button.type = "button";
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", panel.id);
    button.addEventListener("click", () => {
      panel.hidden = !panel.hidden;
      button.setAttribute("aria-expanded", String(!panel.hidden));
    });
    shadow.addEventListener("keydown", event => {
      if (event.key === "Escape") { panel.hidden = true; button.setAttribute("aria-expanded", "false"); button.focus(); }
    });
    shadow.append(style, panel, button);
    document.body.append(host);
  }

  function schedule() {
    if (!enabled || document.hidden) return;
    clearTimeout(timer);
    timer = setTimeout(() => { inspect(false).catch(() => {}); }, Math.max(800, 5000 - (Date.now() - lastAttempt)));
  }

  async function inspect(force = false) {
    updateRoute();
    if (!enabled) return { success: false, error: "Inspection is paused.", enabled: false };
    if (pending) {
      await pending;
      if (!force) { schedule(); return cached; }
      updateRoute();
      if (!enabled) return { success: false, error: "Inspection is paused.", enabled: false };
    }
    let observation;
    try { observation = readProfile(); }
    catch (error) {
      cached = { success: false, error: error.message, enabled };
      if (force) showPanel(cached);
      else removePanel();
      return cached;
    }
    const key = JSON.stringify(observation.payload) + `:${observation.avatar?.complete}:${observation.avatar?.naturalWidth}`;
    if (!force && key === lastKey) return cached;
    if (!force && Date.now() - lastAttempt < 5000) { schedule(); return cached; }
    lastKey = key;
    lastAttempt = Date.now();
    const currentRoute = route;
    const ticket = ++generation;
    const avatar = sampleAvatar(observation.avatar);
    if (avatar.pixels) observation.payload.avatarPixels = avatar.pixels;
    pending = (async () => {
      let response;
      try {
        response = await chrome.runtime.sendMessage({ type: "EVALUATE_PROFILE", payload: observation.payload });
      } catch (_) {
        response = { success: false, error: "Extension connection unavailable. Reload this tab after installing or updating TrustGuard." };
      } finally {
        // The raw downsample is transient; keep only the evidence response in memory.
        delete observation.payload.avatarPixels;
        if (avatar.pixels) avatar.pixels.length = 0;
      }
      if (!enabled || routeKey() !== currentRoute || ticket !== generation) {
        return { success: false, error: "The profile changed during inspection. Inspect the current profile again.", enabled };
      }
      cached = { ...(response || { success: false, error: "The local engine did not respond." }),
        enabled, profile: { platform: observation.payload.platform, handle: observation.payload.handle },
        observationNotes: avatar.note ? [avatar.note] : [] };
      showPanel(cached);
      return cached;
    })();
    try { return await pending; }
    finally { pending = null; }
  }

  function start() {
    if (enabled) return;
    enabled = true;
    observer = new MutationObserver(records => {
      const relevant = records.some(record => {
        if (record.target === document.getElementById(HOST_ID)) return false;
        const changed = [...record.addedNodes, ...record.removedNodes];
        return !(changed.length && changed.every(element => element.id === HOST_ID));
      });
      if (relevant) schedule();
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ["src", "href"] });
    routeTimer = setInterval(() => { if (updateRoute()) schedule(); }, 1000);
  }

  function stop() {
    enabled = false;
    generation += 1;
    clearTimeout(timer);
    clearInterval(routeTimer);
    observer?.disconnect();
    cached = null;
    lastKey = "";
    referenceHandle = "";
    removePanel();
  }

  document.addEventListener("visibilitychange", () => { if (!document.hidden) schedule(); });
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (sender.id !== chrome.runtime.id) return false;
    if (request?.type === "GET_INSPECTION_STATE") {
      updateRoute();
      sendResponse(cached || { success: false, enabled, idle: true });
      return false;
    }
    if (request?.type === "STOP_INSPECTION") {
      stop();
      sendResponse({ success: true, enabled: false });
      return false;
    }
    if (request?.type !== "INSPECT_PROFILE") return false;
    try {
      readProfile(); // Refuse collection on feeds, messages, or unsupported routes.
      referenceHandle = String(request.referenceHandle || "").trim().replace(/^@/u, "").slice(0, 128);
      start();
      inspect(true).then(sendResponse).catch(() => sendResponse({ success: false, error: "The public profile could not be inspected.", enabled }));
    } catch (error) {
      sendResponse({ success: false, error: error.message, enabled });
    }
    return true;
  });
})();
