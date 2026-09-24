# TrustGuard Sentinel

Load this directory using **chrome://extensions → Developer mode → Load unpacked**. Start the TrustGuard backend on `127.0.0.1:8000`, open a public X, Instagram, or LinkedIn profile, reload that tab after installing the extension, then choose **Inspect this profile** in the popup.

Inspection is opt-in for the current tab. The extension observes only the profile header: handle, display name, biography/headline, and the already-loaded avatar when browser canvas security permits reading its pixels. It never reads messages or post feeds, fetches social endpoints, or saves raw images. A transient 64 × 64 grayscale avatar sample is sent only to the local API. The extension needs `activeTab`, declarative content-script access to the supported sites, and loopback API access; it has no storage permission.

The optional original handle is a user-supplied comparison reference, not a verified identity credential. Lookalike findings, the complete 5D vector, both ledger polarities, uncertainty, adversarial explanations, and human verification steps are visible in the popup and expandable in-page panel. The continuous authenticity index is a supporting heuristic, never an identity probability or proof. It is withheld when the inspection lacks two readable modalities.

After inspection, the tab monitors profile-header changes with debouncing and at most one automatic API request every five seconds. **Stop** or a page reload ends monitoring. Navigating to a feed or messages removes the prior result. Results from a previous profile are discarded if navigation happens while an inspection is pending. Nothing is retained in browser storage.

Social site DOM selectors can change. The extension requires a recognized profile route and matching header and fails closed when it cannot identify one. Cross-origin avatar images commonly prohibit pixel access; this produces an incomplete advisory instead of a multimodal verdict. Use the web dashboard with a consented local image and text for a complete inspection in that case.

Run the dependency-free extension checks with `node --test extension/tests/*.test.cjs`. The tests exercise consent, feed/message exclusion, stale navigation, transient avatar handling, CORS failure, stopping pending work, and the local API bridge using DOM fixtures. They do not assert compatibility with future live platform markup.
