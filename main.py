from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    try:
        from backend.llama_brain import get_baymax_reply
    except:
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

CURRENT_FILE = Path(__file__).resolve()
# SMART BASE: find where index.html actually lives
if (CURRENT_FILE.parent / "index.html").exists():
    BASE = CURRENT_FILE.parent
elif (CURRENT_FILE.parent.parent / "index.html").exists():
    BASE = CURRENT_FILE.parent.parent
else:
    BASE = CURRENT_FILE.parent

DATA_FILE = BASE / "pulse_history.json"
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
    return {
        "status": "Baymax Auto OS online",
        "groq_key_loaded": bool(os.getenv("GROQ_API_KEY")),
        "version": "v2.0-car-14-systems",
        "base": str(BASE),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api")
@app.get("/api/health")
def api_home():
    return {"status": "Baymax online", "groq_key_loaded": bool(os.getenv("GROQ_API_KEY"))}

@app.post("/chat")
def chat(req: ChatRequest):
    result = get_baymax_reply(msg=req.message, mode=req.mode, lang=req.lang, image_b64=req.image)
    if isinstance(result, dict):
        return result
    return {"reply": result}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    return {"translated": translate_unlimited(req.text, parse_lang(req.from_lang), parse_lang(req.to_lang))}

@app.post("/api/screen-analyze")
async def screen_analyze(file: UploadFile = File(...), lang: str = "yue"):
    content = await file.read()
    b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"
    result = get_baymax_reply(msg=f"分析呢个画面, 用{lang}讲", mode="screen", lang=lang, image_b64=f"data:{mime};base64,{b64}")
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

# --- STATIC MOUNTS ---
print(f"[Baymax] BASE={BASE} | index exists={(BASE/'index.html').exists()}")
for folder in ["JS", "js", "css", "operations"]:
    fp = BASE / folder
    if fp.exists():
        app.mount(f"/{folder}", StaticFiles(directory=str(fp)), name=folder)
        print(f"[Baymax] Mounted /{folder}")

# Frontend - serve ANY html file from BASE or subfolders
@app.get("/")
async def serve_root():
    index = BASE / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"error": "index.html not found", "base": str(BASE), "files": os.listdir(BASE)}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # skip api docs
    if full_path.startswith(("api/", "docs", "openapi.json", "redoc")) or full_path in ["health", "chat"]:
        return {"error": "not found"}

    # 1. Direct file in BASE
    fp = BASE / full_path
    if fp.is_file():
        return FileResponse(fp)

    # 2. File inside operations / other folders - search for it
    for sub in ["operations", "JS", "css", ""]:
        test = BASE / sub / full_path
        if test.is_file():
            return FileResponse(test)
        # also try just filename
        test2 = BASE / sub / Path(full_path).name
        if test2.is_file():
            return FileResponse(test2)

    # 3. If html requested but not found, return index (for SPA)
    if full_path.endswith(".html"):
        # list what exists to debug
        ops = list((BASE / "operations").glob("*.html")) if (BASE / "operations").exists() else []
        return {"status": "file not found", "requested": full_path, "base": str(BASE), "available_in_operations": [o.name for o in ops]}

    index = BASE / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"status": "Baymax online", "requested": full_path}