// api.js - BAYMAX AUTO FINAL - Guangzhou EV Market
// Path: /api.js (same as index.html) — MODULE + non-module compatible

const API_BASE = "https://baymax-api-bii6.onrender.com"; // Render URL — cold start ~30s

const withTimeout = (ms, promise) => {
  const t = new Promise((_, rej) => setTimeout(() => rej(new Error(`TIMEOUT ${ms}ms — Render cold start, retrying`)), ms));
  return Promise.race([promise, t]);
};

export const BaymaxAPI = {

  // Unified chat — text + image base64 + Cantonese
  chat: async (message, mode = "auto", imageBase64 = null) => {
    const body = { message, mode, lang: "yue", city: "guangzhou" };
    if (imageBase64) body.image = imageBase64; // data:image/jpeg;base64,...

    // Retry once for Render sleep
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await withTimeout(25000, fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        }));
        if (!res.ok) {
          const txt = await res.text().then(s=>s.slice(0,300)).catch(()=>res.statusText);
          // Don't throw HTML page — return offline hint
          if (txt.includes('<!DOCTYPE')) throw new Error('Render waking up...');
          throw new Error(txt);
        }
        const data = await res.json();
        // normalize backend: reply / response / output
        data.reply = data.reply || data.response || data.output || '';
        return data;
      } catch (e) {
        if (attempt === 1) throw e;
        await new Promise(r => setTimeout(r, 1200)); // wait cold start
      }
    }
  },

  vision: (prompt, imageBase64, mode="screen") => BaymaxAPI.chat(prompt, mode, imageBase64),
  action: (type, data) => BaymaxAPI.chat(`ACTION:${type} ${JSON.stringify(data)}`, "car-action"),
  sos: (data) => BaymaxAPI.chat(`SOS ${JSON.stringify(data)} 在广州`, "roadside-sos"),
  memory: (text) => BaymaxAPI.chat(`记住: ${text}`, "car-memory"),

  ping: async () => {
    try {
      const res = await withTimeout(8000, fetch(`${API_BASE}/health`));
      return await res.json();
    } catch(e){ return { status:"offline", api: API_BASE, error: e.message }; }
  },

  // Cantonese TTS — HK voice + queue safe
  speakCantonese: (text) => {
    if (!text) return;
    try {
      speechSynthesis.cancel();
      const clean = text.replace(/[#*`_]/g,'').slice(0,200);
      const u = new SpeechSynthesisUtterance(clean);
      const voices = speechSynthesis.getVoices();
      const hk = voices.find(v => v.lang.toLowerCase().includes('hk')) 
              || voices.find(v => v.lang.toLowerCase().includes('yue'))
              || voices.find(v => v.lang.toLowerCase().startsWith('zh'));
      if (hk) u.voice = hk;
      u.lang = hk ? hk.lang : 'zh-HK';
      u.rate = 1.05;
      u.pitch = 1.05;
      u.volume = 1;
      speechSynthesis.speak(u);
    } catch {}
  }
};

// global for non-module tiles
window.BaymaxAPI = BaymaxAPI;

// Preload voices — Chrome needs async
function loadVoices(){ speechSynthesis.getVoices(); }
loadVoices();
if (speechSynthesis.onvoiceschanged !== undefined) {
  speechSynthesis.onvoiceschanged = loadVoices;
}