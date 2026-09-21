from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json, os, requests, urllib.parse, base64
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

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

CURRENT_DIR = Path(__file__).parent
DATA_FILE = CURRENT_DIR / "pulse_history.json"
if not DATA_FILE.exists():
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
    result = get_baymax_reply(
        msg=req.message,
        mode=req.mode,
        lang=req.lang,
        image_b64=req.image
    )
    if isinstance(result, dict):
        return result
    return {"reply": result}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    tgt = parse_lang(req.to_lang)
    src = parse_lang(req.from_lang)
    return {"translated": translate_unlimited(req.text, src, tgt)}

@app.post("/api/screen-analyze")
async def screen_analyze(file: UploadFile = File(...), lang: str = "yue"):
    content = await file.read()
    b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"
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

# --- FRONTEND MOUNT (MUST BE LAST, FIXED) ---
# Your real folders are in CURRENT_DIR (same folder as main.py)
print(f"[Baymax] Mounting from: {CURRENT_DIR}")
print(f"[Baymax] Has JS folder: {(CURRENT_DIR / 'JS').exists()}")
print(f"[Baymax] Has operations: {(CURRENT_DIR / 'operations').exists()}")

# Mount specific folders first (more specific first)
if (CURRENT_DIR / "JS").exists():
    app.mount("/JS", StaticFiles(directory=str(CURRENT_DIR / "JS")), name="js")
if (CURRENT_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(CURRENT_DIR / "css")), name="css")
if (CURRENT_DIR / "operations").exists():
    app.mount("/operations", StaticFiles(directory=str(CURRENT_DIR / "operations")), name="ops")

# Mount root last
app.mount("/", StaticFiles(directory=str(CURRENT_DIR), html=True), name="frontend")