from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from deep_translator import GoogleTranslator
import json
import os
from datetime import datetime
import requests

try:
    from llama_brain import get_baymax_reply
except ImportError:
    def get_baymax_reply(msg):
        return f"Baymax heard: {msg}"

app = FastAPI(title="Baymax Brain")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class PulseRequest(BaseModel):
    bpm: int
    user_id: str = "user"

class TranslateRequest(BaseModel):
    text: str
    from_lang: str = "en"
    to_lang: str = "fr"

DATA_FILE = os.path.join(os.path.dirname(__file__), "pulse_history.json")
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

LANG_MAP = {
    "english": "en", "spanish": "es", "french": "fr", "chinese": "zh-CN",
    "german": "de", "japanese": "ja", "korean": "ko", "russian": "ru",
    "arabic": "ar", "hindi": "hi", "portuguese": "pt", "italian": "it",
    "dutch": "nl", "turkish": "tr", "swahili": "sw", "kinyarwanda": "rw"
}

def parse_lang(raw: str) -> str:
    s = raw.lower().strip()
    if "chinese" in s or s == "zh" or s == "cn" or "cn chinese" in s:
        return "zh-CN"
    for name, code in LANG_MAP.items():
        if name in s:
            return code
    parts = s.replace("-", " ").split()
    for p in parts:
        if p in LANG_MAP:
            return LANG_MAP[p]
        if p == "zh":
            return "zh-CN"
    if len(s) <= 6 and " " not in s:
        if s == "zh":
            return "zh-CN"
        return s
    return "en"

translation_cache = {}

def translate_via_mymemory(text, src, tgt):
    # MyMemory wants only 2-letter codes, zh-CN -> zh
    src_m = src.split('-')[0].lower()
    tgt_m = tgt.split('-')[0].lower()
    if tgt_m == "zh":
        tgt_m = "zh-CN"
    url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text)}&langpair={src_m}|{tgt_m}"
    r = requests.get(url, timeout=10)
    data = r.json()
    return data["responseData"]["translatedText"]

@app.get("/api")
def api_home():
    return {"status": "Baymax online - 100% round head"}

@app.post("/chat")
def chat(req: ChatRequest):
    reply = get_baymax_reply(req.message)
    return {"reply": reply}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    try:
        src = parse_lang(req.from_lang)
        tgt = parse_lang(req.to_lang)
        text = req.text.strip()

        if not text:
            return {"translated": "", "source": src, "target": tgt}
        if src == tgt:
            return {"translated": text, "source": src, "target": tgt}

        cache_key = f"{src}:{tgt}:{text.lower()}"
        if cache_key in translation_cache:
            return {"translated": translation_cache[cache_key], "source": src, "target": tgt}

        translated = None
        # 1. Try MyMemory first (no rate limit)
        try:
            translated = translate_via_mymemory(text, src, tgt)
        except Exception as e:
            print(f"MyMemory failed: {e}, trying Google...")
            # 2. Fallback to Google
            translated = GoogleTranslator(source=src, target=tgt).translate(text)

        translation_cache[cache_key] = translated
        if len(translation_cache) > 300:
            translation_cache.pop(next(iter(translation_cache)))

        return {"translated": translated, "source": src, "target": tgt}

    except Exception as e:
        print(f"Translate error: {e}")
        return {"error": str(e), "translated": f"Translation failed, try again: {e}"}

@app.get("/api/languages")
async def get_languages():
    return {"languages": ["en","fr","es","rw","ja","zh-CN","sw"]}

@app.post("/api/pulse")
def save_pulse(req: PulseRequest):
    entry = {"bpm": req.bpm, "time": datetime.now().isoformat(), "user": req.user_id}
    with open(DATA_FILE, "r") as f:
        history = json.load(f)
    history.append(entry)
    with open(DATA_FILE, "w") as f:
        json.dump(history[-100:], f, indent=2)
    return {"status": "saved", "entry": entry}

@app.get("/api/pulse")
def get_pulse():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return data[::-1]

@app.get("/api/pulse/latest")
def get_latest():
    with open(DATA_FILE, "r") as f:
        history = json.load(f)
    if history:
        return history[-1]
    return {}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="frontend")