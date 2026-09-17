from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json, os, requests, urllib.parse, base64
from datetime import datetime

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

LANG_MAP = {"english":"en","spanish":"es","french":"fr","chinese":"zh-CN","german":"de","japanese":"ja","korean":"ko","russian":"ru","arabic":"ar","hindi":"hi","portuguese":"pt","italian":"it","dutch":"nl","turkish":"tr","swahili":"sw","kinyarwanda":"rw"}
def parse_lang(raw: str) -> str:
    s=raw.lower().strip()
    if "chinese" in s or s in ["zh","cn"]: return "zh-CN"
    for n,c in LANG_MAP.items():
        if n in s: return c
    return s[:6] if len(s)<=6 else "en"

translation_cache={}
def translate_unlimited(text, src, tgt):
    sm=src.split('-')[0].lower(); tm=tgt.split('-')[0].lower()
    for url in [f"https://ftapi.pythonanywhere.com/translate?sl={sm}&dl={tm}&text={urllib.parse.quote(text)}",
                f"https://ftapi.vedhatech.com/translate?sl={sm}&dl={tm}&text={urllib.parse.quote(text)}"]:
        try:
            r=requests.get(url, timeout=15).json()
            if r.get("destination-text"): return r["destination-text"]
        except: pass
    try:
        r=requests.get(f"https://lingva.ml/api/v1/{sm}/{tm}/{urllib.parse.quote(text)}", timeout=10).json()
        return r["translation"]
    except:
        return text

@app.get("/api")
def api_home(): return {"status":"Baymax online - Vision Ready"}

@app.post("/chat")
def chat(req: ChatRequest): return {"reply": get_baymax_reply(req.message)}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    src=parse_lang(req.from_lang); tgt=parse_lang(req.to_lang); text=req.text.strip()
    if not text or src==tgt: return {"translated":text, "source":src, "target":tgt}
    k=f"{src}:{tgt}:{text.lower()}"
    if k in translation_cache: return {"translated":translation_cache[k]}
    tr=translate_unlimited(text, src, tgt)
    translation_cache[k]=tr
    return {"translated":tr}

@app.post("/api/screen-analyze")
async def screen_analyze(file: UploadFile = File(...), lang: str = "en"):
    content = await file.read()
    b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"
    target = parse_lang(lang)

    # FIXED: Check all possible env names you might use on Render
    key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_KEY") or os.getenv("GOOGLE_API_KEY")

    if not key:
        return {"description":"❌ Add OPENROUTER_API_KEY in Render > Environment"}

    try:
        # OpenRouter
        if key.startswith("sk-or-"):
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [{"role":"user","content":[
                    {"type":"text","text":f"You are Baymax. Analyze image in {target}. If Chinese shopping page, extract product, price, features. Be accurate."},
                    {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}}
                ]}]
            }
            r = requests.post(url, headers=headers, json=payload, timeout=40).json()
            if "choices" in r:
                text = r["choices"][0]["message"]["content"]
                return {"description": text}
            else:
                return {"description": f"OpenRouter error: {r}"}
        else:
            # Direct Google
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            payload = {"contents":[{"parts":[{"text":f"Describe in {target}"},{"inline_data":{"mime_type":mime,"data":b64}}]}]}
            r = requests.post(url, json=payload, timeout=30).json()
            return {"description": r["candidates"][0]["content"]["parts"][0]["text"]}
    except Exception as e:
        return {"description": f"Vision error: {str(e)}"}

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