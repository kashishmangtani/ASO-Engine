/* AI Revenue tracking snippet. Anonymous: records only the AI source, event type and page path.
   Install: <script async src="https://YOUR-PLATFORM/t.js" data-key="SITE_KEY"></script>
   Custom conversions (booking widgets, phone clicks): window.asoLead && window.asoLead(); */
(function () {
  var s = document.currentScript;
  if (!s) return;
  var key = s.getAttribute("data-key");
  var endpoint = new URL(s.src).origin + "/t/" + encodeURIComponent(key);
  var AI = {
    "chatgpt.com": "chatgpt", "chat.openai.com": "chatgpt", "openai.com": "chatgpt",
    "perplexity.ai": "perplexity", "gemini.google.com": "gemini", "bard.google.com": "gemini",
    "copilot.microsoft.com": "copilot", "claude.ai": "claude", "chat.deepseek.com": "deepseek",
    "deepseek.com": "deepseek", "grok.com": "grok", "meta.ai": "meta-ai"
  };
  var WORDS = ["chatgpt", "openai", "perplexity", "gemini", "copilot", "claude", "deepseek", "grok"];
  var WORD_MAP = { openai: "chatgpt" };
  var DAY = 864e5, TTL = 30 * DAY, KEY = "aso_src";

  function fromHost(h) {
    h = (h || "").toLowerCase().replace(/^www\./, "");
    for (var d in AI) if (h === d || h.slice(-(d.length + 1)) === "." + d) return AI[d];
    return null;
  }
  function fromUtm(v) {
    v = (v || "").toLowerCase();
    if (!v) return null;
    var h = fromHost(v);
    if (h) return h;
    for (var i = 0; i < WORDS.length; i++) if (v.indexOf(WORDS[i]) > -1) return WORD_MAP[WORDS[i]] || WORDS[i];
    return null;
  }
  function store(k, v, session) {
    try { (session ? sessionStorage : localStorage).setItem(k, v); } catch (e) {}
  }
  function load(k, session) {
    try { return (session ? sessionStorage : localStorage).getItem(k); } catch (e) { return null; }
  }
  function send(type, source) {
    var body = JSON.stringify({ type: type, source: source, path: location.pathname });
    try {
      if (navigator.sendBeacon && navigator.sendBeacon(endpoint, body)) return;
    } catch (e) {}
    try { fetch(endpoint, { method: "POST", body: body, keepalive: true, mode: "no-cors" }); } catch (e) {}
  }

  var src = null;
  try { if (document.referrer) src = fromHost(new URL(document.referrer).hostname); } catch (e) {}
  if (!src) {
    try { src = fromUtm(new URLSearchParams(location.search).get("utm_source")); } catch (e) {}
  }
  if (src) {
    store(KEY, JSON.stringify({ s: src, t: Date.now() }));
    if (!load("aso_v_" + src, true)) { store("aso_v_" + src, "1", true); send("visit", src); }
  }

  function currentSource() {
    try {
      var v = JSON.parse(load(KEY) || "null");
      if (v && Date.now() - v.t < TTL) return v.s;
    } catch (e) {}
    return "other";
  }
  var lastLead = 0;
  function lead() {
    var now = Date.now();
    if (now - lastLead < 5000) return; // ignore double submits
    lastLead = now;
    send("lead", currentSource());
  }
  window.asoLead = lead;
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (f && f.getAttribute && f.getAttribute("data-aso-ignore") !== null) return;
    if (f && f.querySelector && !f.querySelector('input[type="email"], input[type="tel"], textarea')) return; // skip search boxes
    lead();
  }, true);
})();
