from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import os
from datetime import datetime
import requests
import urllib.parse

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
    if "chinese" in s or s == "zh" or s == "cn": return "zh-CN"
    for name, code in LANG_MAP.items():
        if name in s: return code
    parts = s.replace("-", " ").split()
    for p in parts:
        if p in LANG_MAP: return LANG_MAP[p]
        if p == "zh": return "zh-CN"
    if len(s) <= 6 and " " not in s:
        if s == "zh": return "zh-CN"
        return s
    return "en"

translation_cache = {}

def translate_unlimited(text, src, tgt):
    """FTAPI - unlimited, no key, works on Render"""
    src_m = src.split('-')[0].lower()
    tgt_m = tgt.split('-')[0].lower()
    # fix chinese codes for ftapi
    if tgt_m == "zh": tgt_m = "zh-CN"
    if src_m == "zh": src_m = "zh-CN"

    # 1. Primary: FTAPI PythonAnywhere (unlimited)
    try:
        url = f"https://ftapi.pythonanywhere.com/translate?sl={src_m}&dl={tgt_m}&text={urllib.parse.quote(text)}"
        r = requests.get(url, timeout=15)
        j = r.json()
        # ftapi returns destination-text
        if "destination-text" in j:
            return j["destination-text"]
        if "translated-text" in j:
            return j["translated-text"]
    except Exception as e:
        print(f"FTAPI 1 failed: {e}")

    # 2. Backup FTAPI 2
    try:
        url = f"https://ftapi.vedhatech.com/translate?sl={src_m}&dl={tgt_m}&text={urllib.parse.quote(text)}"
        r = requests.get(url, timeout=15)
        j = r.json()
        return j.get("destination-text") or j.get("translation") or list(j.values())[0]
    except Exception as e:
        print(f"FTAPI 2 failed: {e}")

    # 3. Lingva backup
    try:
        url = f"https://lingva.ml/api/v1/{src_m}/{tgt_m}/{urllib.parse.quote(text)}"
        r = requests.get(url, timeout=10)
        return r.json()["translation"]
    except Exception as e:
        print(f"Lingva failed: {e}")
        raise e

@app.get("/api")
def api_home(): return {"status": "Baymax online - FTAPI mode"}

@app.post("/chat")
def chat(req: ChatRequest): return {"reply": get_baymax_reply(req.message)}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    try:
        src = parse_lang(req.from_lang)
        tgt = parse_lang(req.to_lang)
        text = req.text.strip()
        if not text: return {"translated": "", "source": src, "target": tgt}
        if src == tgt: return {"translated": text, "source": src, "target": tgt}

        cache_key = f"{src}:{tgt}:{text.lower()}"
        if cache_key in translation_cache:
            return {"translated": translation_cache[cache_key], "source": src, "target": tgt}

        translated = translate_unlimited(text, src, tgt)

        translation_cache[cache_key] = translated
        if len(translation_cache) > 1000:
            translation_cache.pop(next(iter(translation_cache)))

        return {"translated": translated, "source": src, "target": tgt}

    except Exception as e:
        print(f"Translate final error: {e}")
        return {"error": str(e), "translated": text} # fallback to original text instead of ugly error

@app.get("/api/languages")
async def get_languages(): return {"languages": ["en","fr","es","rw","ja","zh-CN","sw"]}

@app.post("/api/pulse")
def save_pulse(req: PulseRequest):
    entry = {"bpm": req.bpm, "time": datetime.now().isoformat(), "user": req.user_id}
    with open(DATA_FILE, "r") as f: history = json.load(f)
    history.append(entry)
    with open(DATA_FILE, "w") as f: json.dump(history[-100:], f, indent=2)
    return {"status": "saved", "entry": entry}

@app.get("/api/pulse")
def get_pulse():
    with open(DATA_FILE, "r") as f: data = json.load(f)
    return data[::-1]

@app.get("/api/pulse/latest")
def get_latest():
    with open(DATA_FILE, "r") as f: history = json.load(f)
    return history[-1] if history else {}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="frontend")