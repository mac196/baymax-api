from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json, os, requests, urllib.parse, base64
from datetime import datetime

# THIS IS THE MISSING LINE THAT LOADS YOUR.env
from dotenv import load_dotenv
load_dotenv()

try:
    from llama_brain import get_baymax_reply
except ImportError:
    def get_baymax_reply(msg): return f"Baymax heard: {msg}"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel): message: str
class PulseRequest(BaseModel): bpm: int; user_id: str = "user"
class TranslateRequest(BaseModel): text: str; from_lang: str = "en"; to_lang: str = "fr"

DATA_FILE = os.path.join(os.path.dirname(__file__), "pulse_history.json")
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f: json.dump([], f)

def parse_lang(raw: str) -> str:
    s=raw.lower().strip()
    if "chinese" in s: return "zh-CN"
    return s[:6]

def translate_unlimited(text, src, tgt):
    sm=src.split('-')[0].lower(); tm=tgt.split('-')[0].lower()
    if sm==tm or not text.strip(): return text
    try:
        r=requests.get(f"https://ftapi.pythonanywhere.com/translate?sl={sm}&dl={tm}&text={urllib.parse.quote(text)}", timeout=10).json()
        if r.get("destination-text"): return r["destination-text"]
    except: pass
    return text

@app.get("/api")
def api_home():
    has_key = bool(os.getenv("GROQ_API_KEY"))
    return {"status":"Baymax online", "groq_key_loaded": has_key}

@app.post("/chat")
def chat(req: ChatRequest): return {"reply": get_baymax_reply(req.message)}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    src=parse_lang(req.from_lang); tgt=parse_lang(req.to_lang)
    return {"translated": translate_unlimited(req.text, src, tgt)}

@app.post("/api/screen-analyze")
async def screen_analyze(file: UploadFile = File(...), lang: str = "en"):
    import base64, os, requests
    content = await file.read()
    b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"
    target = lang[:5]
    key = os.getenv("GROQ_API_KEY")

    for model in ["qwen/qwen3.6-27b", "qwen/qwen3-32b", "llama-3.2-11b-vision-preview"]:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role":"user","content":[
                        {"type":"text","text":f"Describe in {target}"},
                        {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}}
                    ]}],
                    "max_tokens": 600
                },
                timeout=30
            ).json()
            if "choices" in r:
                return {"description": r["choices"][0]["message"]["content"]}
        except: continue

    return {"description": f"All models failed, last response: {r}"}

@app.post("/api/pulse")
def save_pulse(req: PulseRequest):
    entry={"bpm":req.bpm,"time":datetime.now().isoformat(),"user":req.user_id}
    with open(DATA_FILE,"r") as f: h=json.load(f)
    h.append(entry)
    with open(DATA_FILE,"w") as f: json.dump(h[-100:], f, indent=2)
    return {"status":"saved","entry":entry}

@app.get("/api/pulse")
def get_pulse():
    with open(DATA_FILE,"r") as f: return json.load(f)[::-1]

@app.get("/api/pulse/latest")
def get_latest():
    with open(DATA_FILE,"r") as f: h=json.load(f); return h[-1] if h else {}

BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="frontend")