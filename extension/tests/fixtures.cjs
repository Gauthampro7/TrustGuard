/**
 * Simulated DOM and multi-platform fixtures for TrustGuard extension tests.
 * Zero external dependencies: pure Node.js compatible with node:test.
 */
"use strict";

class SimulatedElement {
  constructor(tag = "div", text = "") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.parentElement = null;
    this.style = {};
    this.hidden = false;
    this.attributes = new Map();
    this._listeners = new Map();
    if (text) this.textContent = text;
  }

  get id() { return this.getAttribute("id") || ""; }
  set id(value) { this.setAttribute("id", value); }

  get className() { return this.getAttribute("class") || ""; }
  set className(value) { this.setAttribute("class", value); }

  get classList() {
    const self = this;
    const tokens = new Set((this.className || "").split(/\s+/u).filter(Boolean));
    return {
      add(...names) { names.forEach(n => tokens.add(n)); self.className = Array.from(tokens).join(" "); },
      remove(...names) { names.forEach(n => tokens.delete(n)); self.className = Array.from(tokens).join(" "); },
      contains(name) { return tokens.has(name); },
      has(name) { return tokens.has(name); }
    };
  }

  get textContent() {
    if (this._text !== undefined) return this._text;
    return this.children.map(c => c.textContent).join("");
  }
  set textContent(value) {
    this._text = String(value);
    this.children = [];
  }

  get innerText() { return this.textContent; }
  set innerText(value) { this.textContent = value; }

  getAttribute(name) { return this.attributes.get(name.toLowerCase()) ?? null; }
  setAttribute(name, value) {
    const lower = name.toLowerCase();
    const str = String(value);
    this.attributes.set(lower, str);
    if (lower === "id") this._id = str;
    if (lower === "class") this._class = str;
    if (lower === "src") this.src = str;
    if (lower === "href") this.href = str;
    if (lower === "alt") this.alt = str;
  }
  hasAttribute(name) { return this.attributes.has(name.toLowerCase()); }
  removeAttribute(name) { this.attributes.delete(name.toLowerCase()); }

  append(...nodes) {
    nodes.forEach(node => {
      if (typeof node === "string") node = new SimulatedElement("span", node);
      node.parentElement = this;
      this.children.push(node);
    });
  }

  appendChild(node) {
    this.append(node);
    return node;
  }

  replaceChildren(...nodes) {
    this.children.forEach(c => { c.parentElement = null; });
    this.children = [];
    this._text = undefined;
    this.append(...nodes);
  }

  remove() {
    if (this.parentElement) {
      this.parentElement.children = this.parentElement.children.filter(child => child !== this);
      this.parentElement = null;
    }
  }

  attachShadow() {
    this.shadow = new SimulatedElement("shadow-root");
    this.shadow.parentElement = this;
    return this.shadow;
  }

  addEventListener(type, listener) {
    if (!this._listeners.has(type)) this._listeners.set(type, []);
    this._listeners.get(type).push(listener);
  }

  dispatchEvent(event) {
    const list = this._listeners.get(event.type) || [];
    list.forEach(fn => fn.call(this, event));
  }

  getClientRects() {
    let node = this;
    while (node) {
      if (node.hidden || node.style?.display === "none" || node.style?.visibility === "hidden") {
        return [];
      }
      node = node.parentElement;
    }
    return [{ width: 100, height: 100, top: 0, left: 0, right: 100, bottom: 100 }];
  }

  matches(selector) {
    if (!selector) return false;
    const parts = selector.split(",").map(s => s.trim()).filter(Boolean);
    return parts.some(sel => this._matchesSingle(sel));
  }

  _matchesSingle(selector) {
    const tokens = selector.split(/\s+/u).filter(Boolean);
    if (tokens.length === 1) return this._matchesCompound(tokens[0]);

    // Descendant selector: last token must match this element, predecessor must match an ancestor
    const target = tokens[tokens.length - 1];
    if (!this._matchesCompound(target)) return false;

    let ancestor = this.parentElement;
    let idx = tokens.length - 2;
    while (ancestor && idx >= 0) {
      if (ancestor._matchesCompound(tokens[idx])) idx--;
      ancestor = ancestor.parentElement;
    }
    return idx < 0;
  }

  _matchesCompound(compound) {
    // Splits e.g. section#id, img.class, #id, or [data-testid="user-avatar"]
    if (compound.startsWith("#")) {
      return this.id === compound.slice(1);
    }
    const re = /^([a-zA-Z0-9_-]+)?(?:#([a-zA-Z0-9_-]+))?((?:\.[a-zA-Z0-9_-]+)*)((?:\[[^\]]+\])*)$/u;
    const match = compound.match(re);
    if (!match) {
      if (compound.startsWith(".")) return this.classList.contains(compound.slice(1));
      if (compound.startsWith("[")) return this._matchesAttr(compound);
      return this.tagName.toLowerCase() === compound.toLowerCase();
    }

    const [, tag, id, classes, attrs] = match;
    if (tag && this.tagName.toLowerCase() !== tag.toLowerCase()) return false;
    if (id && this.id !== id) return false;
    if (classes) {
      const classNames = classes.split(".").filter(Boolean);
      for (const cn of classNames) {
        if (!this.classList.contains(cn)) return false;
      }
    }
    if (attrs) {
      const attrMatches = attrs.match(/\[[^\]]+\]/gu) || [];
      for (const attrStr of attrMatches) {
        if (!this._matchesAttr(attrStr)) return false;
      }
    }
    return true;
  }

  _matchesAttr(attrStr) {
    const inner = attrStr.slice(1, -1);
    const containsMatch = inner.match(/^([a-zA-Z0-9_-]+)\*=["']?([^"']+)["']?$/u);
    if (containsMatch) {
      const val = this.getAttribute(containsMatch[1]);
      return val !== null && val.includes(containsMatch[2]);
    }
    const prefixMatch = inner.match(/^([a-zA-Z0-9_-]+)\^=["']?([^"']+)["']?$/u);
    if (prefixMatch) {
      const val = this.getAttribute(prefixMatch[1]);
      return val !== null && val.startsWith(prefixMatch[2]);
    }
    const exactMatch = inner.match(/^([a-zA-Z0-9_-]+)=["']?([^"']+)["']?$/u);
    if (exactMatch) {
      return this.getAttribute(exactMatch[1]) === exactMatch[2];
    }
    return this.hasAttribute(inner);
  }

  closest(selector) {
    let curr = this;
    while (curr) {
      if (curr.matches && curr.matches(selector)) return curr;
      curr = curr.parentElement;
    }
    return null;
  }

  querySelectorAll(selector) {
    const results = [];
    function walk(node) {
      for (const child of node.children) {
        if (child.matches && child.matches(selector)) results.push(child);
        walk(child);
      }
    }
    walk(this);
    return results;
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}

/**
 * Creates simulated DOM fixture for X (Twitter).
 */
function createXFixture({
  handle = "alice",
  displayName = "Alice Example",
  bio = "Public bio only.",
  avatarUrl = "https://pbs.twimg.com/avatar.png",
  avatarValid = true,
  hiddenDuplicate = false,
  mismatchedHeader = false,
  missingHeader = false,
  statsText = "",
  postImages = [],
  feedPosts = ["SPAM TWEET: Send 1 BTC to get 2 BTC back!", "Crypto giveaway in replies"],
  dms = ["Private DM: Hey check this secret link!"]
} = {}) {
  const body = new SimulatedElement("body");
  const main = new SimulatedElement("main");
  body.append(main);

  if (hiddenDuplicate) {
    const dup = new SimulatedElement("div");
    dup.setAttribute("data-testid", "UserName");
    dup.style.display = "none";
    dup.append(new SimulatedElement("span", "Hidden Impostor"), new SimulatedElement("span", "@fake_alice"));
    main.append(dup);
  }

  if (!missingHeader) {
    const headerName = new SimulatedElement("div");
    headerName.setAttribute("data-testid", "UserName");
    const hHandle = mismatchedHeader ? "@wrong_user" : `@${handle}`;
    headerName.append(
      new SimulatedElement("span", displayName),
      new SimulatedElement("span", hHandle)
    );
    main.append(headerName);

    if (statsText) {
      const headerStats = new SimulatedElement("div");
      headerStats.setAttribute("data-testid", "UserProfileHeader_Items");
      headerStats.textContent = statsText;
      main.append(headerStats);
    }

    const desc = new SimulatedElement("div");
    desc.setAttribute("data-testid", "UserDescription");
    desc.textContent = bio;
    main.append(desc);

    const avatarContainer = new SimulatedElement("div");
    avatarContainer.setAttribute("data-testid", `UserAvatar-Container-${handle}`);
    const anchor = new SimulatedElement("a");
    anchor.setAttribute("href", `https://x.com/${handle}/photo`);
    const img = new SimulatedElement("img");
    img.setAttribute("src", avatarUrl);
    img.complete = avatarValid;
    img.naturalWidth = avatarValid ? 128 : 0;
    img.naturalHeight = avatarValid ? 128 : 0;
    anchor.append(img);
    avatarContainer.append(anchor);
    main.append(avatarContainer);
  }

  postImages.forEach(src => {
    const photoContainer = new SimulatedElement("div");
    photoContainer.setAttribute("data-testid", "tweetPhoto");
    const img = new SimulatedElement("img");
    img.setAttribute("src", src);
    img.complete = true;
    img.naturalWidth = 128;
    img.naturalHeight = 128;
    photoContainer.append(img);
    main.append(photoContainer);
  });

  // Feed posts inside articles with test ids
  feedPosts.forEach(postText => {
    const article = new SimulatedElement("article");
    article.setAttribute("data-testid", "tweet");
    article.append(new SimulatedElement("span", postText));
    // Even if an article has a UserName inside it, it must not be picked
    const postUser = new SimulatedElement("div");
    postUser.setAttribute("data-testid", "UserName");
    postUser.append(new SimulatedElement("span", "Feed Author"), new SimulatedElement("span", "@feed_author"));
    article.append(postUser);
    main.append(article);
  });

  // Direct messages drawer
  dms.forEach(dmText => {
    const dmDiv = new SimulatedElement("div");
    dmDiv.className = "dm-drawer-entry";
    dmDiv.append(new SimulatedElement("p", dmText));
    body.append(dmDiv);
  });

  return { body, main };
}

/**
 * Creates simulated DOM fixture for Instagram.
 */
function createInstagramFixture({
  handle = "carol_art",
  displayName = "Carol Art",
  bio = "Visual artist & designer in Tokyo.",
  avatarUrl = "https://instagram.com/avatar.jpg",
  avatarValid = true,
  hiddenDuplicate = false,
  mismatchedHeader = false,
  missingHeader = false,
  statsText = "",
  postImages = [],
  feedPosts = ["Instagram post caption: exclusive merch drop!", "Check the link in bio for discounts"],
  dms = ["Instagram Direct Message: Hey do you sell prints?"]
} = {}) {
  const body = new SimulatedElement("body");
  const main = new SimulatedElement("main");
  body.append(main);

  if (hiddenDuplicate) {
    const hiddenHeader = new SimulatedElement("header");
    hiddenHeader.style.display = "none";
    const dupHeading = new SimulatedElement("h2");
    dupHeading.setAttribute("data-testid", "user-name");
    dupHeading.textContent = "hidden_stale_user";
    hiddenHeader.append(dupHeading);
    main.append(hiddenHeader);
  }

  if (!missingHeader) {
    const header = new SimulatedElement("header");
    const heading = new SimulatedElement("h2");
    heading.setAttribute("data-testid", "user-name");
    heading.textContent = mismatchedHeader ? "wrong_handle" : handle;
    header.append(heading);

    const nameSpan = new SimulatedElement("span");
    nameSpan.setAttribute("data-testid", "profile-name");
    nameSpan.textContent = displayName;
    header.append(nameSpan);

    if (statsText) {
      header.append(new SimulatedElement("div", statsText));
    }

    const bioDiv = new SimulatedElement("div");
    bioDiv.setAttribute("data-testid", "user-bio");
    bioDiv.textContent = bio;
    header.append(bioDiv);

    const img = new SimulatedElement("img");
    img.setAttribute("data-testid", "user-avatar");
    img.setAttribute("alt", `${handle}'s profile picture`);
    img.setAttribute("src", avatarUrl);
    img.complete = avatarValid;
    img.naturalWidth = avatarValid ? 150 : 0;
    img.naturalHeight = avatarValid ? 150 : 0;
    header.append(img);

    main.append(header);
  }

  postImages.forEach(src => {
    const a = new SimulatedElement("a");
    a.setAttribute("href", "/p/sample123/");
    const img = new SimulatedElement("img");
    img.setAttribute("src", src);
    img.complete = true;
    img.naturalWidth = 150;
    img.naturalHeight = 150;
    a.append(img);
    main.append(a);
  });

  // Instagram feed/posts outside the header
  feedPosts.forEach(postCaption => {
    const article = new SimulatedElement("article");
    article.className = "post-card";
    article.append(new SimulatedElement("span", postCaption));
    main.append(article);
  });

  // Direct message threads
  dms.forEach(dm => {
    const directDiv = new SimulatedElement("div");
    directDiv.className = "direct-message-item";
    directDiv.append(new SimulatedElement("span", dm));
    body.append(directDiv);
  });

  return { body, main };
}

/**
 * Creates simulated DOM fixture for LinkedIn.
 */
function createLinkedInFixture({
  handle = "dan-smith",
  displayName = "Dan Smith",
  headline = "VP of Engineering at CloudSecure | Distributed Systems",
  avatarUrl = "https://licdn.com/avatar.jpg",
  avatarValid = true,
  canonicalUrl = `https://www.linkedin.com/in/${handle}`,
  hiddenDuplicate = false,
  missingHeader = false,
  missingName = false,
  feedPosts = ["LinkedIn Feed Update: Thrilled to announce our Series B funding round!", "We are actively hiring 10 engineers!"],
  dms = ["InMail Private: Exclusive executive compensation advisory."]
} = {}) {
  const body = new SimulatedElement("body");
  const head = new SimulatedElement("head");
  if (canonicalUrl !== null) {
    const canonicalLink = new SimulatedElement("link");
    canonicalLink.setAttribute("rel", "canonical");
    canonicalLink.setAttribute("href", canonicalUrl);
    head.append(canonicalLink);
  }

  const main = new SimulatedElement("main");
  body.append(main);

  if (hiddenDuplicate) {
    const hiddenSection = new SimulatedElement("section");
    hiddenSection.className = "pv-top-card";
    hiddenSection.style.display = "none";
    const hiddenH1 = new SimulatedElement("h1", "Hidden Impostor");
    hiddenSection.append(hiddenH1);
    main.append(hiddenSection);
  }

  if (!missingHeader) {
    const section = new SimulatedElement("section");
    section.className = "pv-top-card";

    if (!missingName) {
      const h1 = new SimulatedElement("h1", displayName);
      section.append(h1);
    }

    const headlineDiv = new SimulatedElement("div");
    headlineDiv.className = "text-body-medium";
    headlineDiv.textContent = headline;
    section.append(headlineDiv);

    const img = new SimulatedElement("img");
    img.className = "pv-top-card-profile-picture__image--show";
    img.setAttribute("src", avatarUrl);
    img.complete = avatarValid;
    img.naturalWidth = avatarValid ? 200 : 0;
    img.naturalHeight = avatarValid ? 200 : 0;
    section.append(img);

    main.append(section);
  }

  // LinkedIn activity/feed updates
  feedPosts.forEach(postText => {
    const feedItem = new SimulatedElement("div");
    feedItem.className = "feed-shared-update-v2";
    feedItem.append(new SimulatedElement("p", postText));
    main.append(feedItem);
  });

  // LinkedIn messaging overlay
  dms.forEach(dm => {
    const msgDiv = new SimulatedElement("div");
    msgDiv.className = "msg-overlay-bubble";
    msgDiv.append(new SimulatedElement("span", dm));
    body.append(msgDiv);
  });

  return { body, head, main };
}

module.exports = {
  SimulatedElement,
  createXFixture,
  createInstagramFixture,
  createLinkedInFixture
};
