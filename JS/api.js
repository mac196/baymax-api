// Baymax API - fixed
const API_BASE = "";

export const BaymaxAPI = {
  async ping() {
    try {
      const r = await fetch(`${API_BASE}/api/health`);
      return await r.json();
    } catch {
      return { status: "offline" };
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