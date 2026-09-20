from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json, os, requests, urllib.parse, base64
from datetime import datetime
from typing import Optional, Dict

from dotenv import load_dotenv
load_dotenv()

try:
    from llama_brain import get_baymax_reply
except ImportError:
    def get_baymax_reply(msg, mode="auto", lang="yue", image_b64=None):
        return f"Baymax [{mode}] heard: {msg}"

app = FastAPI(title="Baymax Auto OS v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    mode: str = "auto"
    lang: str = "yue"
    city: str = "guangzhou"
    image: Optional[str] = None
    action_type: Optional[str] = None
    payload: Optional[Dict] = None

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

def parse_lang(raw: str) -> str:
    s = raw.lower().strip()
    if "chinese" in s: return "zh-CN"
    if s in ["yue", "cantonese", "zh-yue"]: return "yue"
    return s[:6]

def translate_unlimited(text, src, tgt):
    sm = src.split('-')[0].lower()
    tm = tgt.split('-')[0].lower()
    if sm == tm or not text.strip():
        return text
    try:
        r = requests.get(
            f"https://ftapi.pythonanywhere.com/translate?sl={sm}&dl={tm}&text={urllib.parse.quote(text)}",
            timeout=10
        ).json()
        if r.get("destination-text"):
            return r["destination-text"]
    except:
        pass
    return text

@app.get("/health")
def health():
    has_key = bool(os.getenv("GROQ_API_KEY"))
    return {
        "status": "Baymax Auto OS online",
        "groq_key_loaded": has_key,
        "version": "v2.0-car-14-systems",
        "city": "guangzhou",
        "cantonese": "95%",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api")
def api_home():
    has_key = bool(os.getenv("GROQ_API_KEY"))
    return {"status": "Baymax online", "groq_key_loaded": has_key}

@app.post("/chat")
def chat(req: ChatRequest):
    # Pass all car context to brain
    result = get_baymax_reply(
        msg=req.message,
        mode=req.mode,
        lang=req.lang,
        image_b64=req.image
    )
    # Support both string and dict returns
    if isinstance(result, dict):
        return result
    return {"reply": result}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    src = parse_lang(req.from_lang)
    tgt = parse_lang(req.to_lang)
    return {"translated": translate_unlimited(req.text, src, tgt)}

@app.post("/api/screen-analyze")
async def screen_analyze(file: UploadFile = File(...), lang: str = "yue"):
    content = await file.read()
    b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"
    # Re-use brain logic
    result = get_baymax_reply(
        msg=f"分析呢个画面, 用{lang}讲",
        mode="screen",
        lang=lang,
        image_b64=f"data:{mime};base64,{b64}"
    )
    if isinstance(result, dict):
        return {"description": result.get("reply", str(result))}
    return {"description": result}

@app.post("/api/pulse")
def save_pulse(req: PulseRequest):
    entry = {"bpm": req.bpm, "time": datetime.now().isoformat(), "user": req.user_id}
    try:
        with open(DATA_FILE, "r") as f:
            h = json.load(f)
    except:
        h = []
    h.append(entry)
    with open(DATA_FILE, "w") as f:
        json.dump(h[-100:], f, indent=2)
    return {"status": "saved", "entry": entry}

@app.get("/api/pulse")
def get_pulse():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)[::-1]
    except:
        return []

@app.get("/api/pulse/latest")
def get_latest():
    try:
        with open(DATA_FILE, "r") as f:
            h = json.load(f)
            return h[-1] if h else {"bpm": 78}
    except:
        return {"bpm": 78}

# --- Frontend mount (must be last) ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Check if frontend files exist in parent dir
if os.path.exists(os.path.join(BASE_DIR, "index.html")):
    app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="frontend")