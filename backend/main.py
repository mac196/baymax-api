from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from deep_translator import GoogleTranslator
import json
import os
from datetime import datetime

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
        src = req.from_lang[:5].split('-')[0].strip().lower()
        tgt = req.to_lang[:5].split('-')[0].strip().lower()
        translated = GoogleTranslator(source=src, target=tgt).translate(req.text)
        return {"translated": translated, "source": src, "target": tgt}
    except Exception as e:
        return {"error": str(e), "translated": req.text}

@app.get("/api/languages")
async def get_languages():
    try:
        return {"languages": GoogleTranslator().get_supported_languages(as_dict=True)}
    except:
        return {"languages": ["en","fr","es","rw","ja"]}

@app.post("/api/pulse")
def save_pulse(req: PulseRequest):
    entry = {"bpm": req.bpm, "time": datetime.now().isoformat(), "user": req.user_id}
    with open(DATA_FILE, "r") as f:
        history = json.load(f)
    history.append(entry)
    with open(DATA_FILE, "w") as f:
        json.dump(history[-100:], f, indent=2)
    print(f"[SAVED] {req.bpm} BPM")
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