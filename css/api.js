// Baymax API - auto-detects local vs Render
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
 ? "" // local: use relative
  : ""; // on Render, same domain serves frontend+backend

export const BaymaxAPI = {
  async ping() {
    try {
      const r = await fetch(`${API_BASE}/health`);
      if (!r.ok) throw new Error("health failed");
      return await r.json();
    } catch (e) {
      try {
        const r2 = await fetch(`${API_BASE}/api`);
        return await r2.json();
      } catch {
        return { status: "offline", api: API_BASE || "relative" };
      }
    }
  },

  async chat(message, mode="auto", lang="yue") {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, mode, lang, city: "guangzhou" })
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`Chat ${res.status}: ${txt}`);
    }
    return await res.json();
  },

  async translate(text, from="en", to="yue") {
    const res = await fetch(`${API_BASE}/api/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, from_lang: from, to_lang: to })
    });
    return await res.json();
  },

  speakCantonese(text) {
    if (!text) return;
    try {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "zh-HK";
      u.rate = 0.95;
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
    } catch {}
  }
};