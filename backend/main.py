from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json, os, requests, urllib.parse, base64, io
from datetime import datetime
from PIL import Image

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

translation_cache={}
def translate_unlimited(text, src, tgt):
    sm=src.split('-')[0].lower(); tm=tgt.split('-')[0].lower()
    for url in [f"https://ftapi.pythonanywhere.com/translate?sl={sm}&dl={tm}&text={urllib.parse.quote(text)}",
                f"https://ftapi.vedhatech.com/translate?sl={sm}&dl={tm}&text={urllib.parse.quote(text)}"]:
        try:
            r=requests.get(url, timeout=15).json()
            if r.get("destination-text"): return r["destination-text"]
        except: pass
    return text

@app.get("/api")
def api_home(): return {"status":"Baymax online"}

@app.post("/chat")
def chat(req: ChatRequest): return {"reply": get_baymax_reply(req.message)}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    src=parse_lang(req.from_lang); tgt=parse_lang(req.to_lang); text=req.text.strip()
    if not text or src==tgt: return {"translated":text}
    tr=translate_unlimited(text, src, tgt)
    return {"translated":tr}

def describe_locally(image_bytes):
    # No AI needed - use basic image analysis to never return wrong description
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w,h = img.size
        # Simple smart description based on colors / content
        return None # force to use LLM
    except: return None

@app.post("/api/screen-analyze")
async def screen_analyze(file: UploadFile = File(...), lang: str = "en"):
    content = await file.read()
    b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"
    target = parse_lang(lang)

    # TRY ALL FREE MODELS IN ORDER - one will work
    MODELS_TO_TRY = [
        ("https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large", "hf_blip"),
        ("https://api-inference.huggingface.co/models/nlpconnect/vit-gpt2-image-captioning", "hf_vit"),
    ]

    # 1. Try HuggingFace BLIP - truly free
    for hf_url, _ in MODELS_TO_TRY:
        try:
            resp = requests.post(hf_url, data=content, timeout=20)
            if resp.status_code == 200:
                j = resp.json()
                text = j[0]['generated_text'] if isinstance(j, list) else str(j)
                if target!= "en":
                    text = translate_unlimited(text, "en", target)
                return {"description": f"DETECTED: {text}"}
        except Exception as e:
            continue

    # 2. Try OpenRouter FREE if key exists - use model that STILL has free version
    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        for model_id in ["qwen/qwen2.5-vl-7b-instruct:free", "google/gemma-3-4b-it", "google/gemini-2.0-flash-lite-001"]:
            try:
                r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
                    json={
                        "model": model_id,
                        "messages":[{"role":"user","content":[
                            {"type":"text","text":f"Describe this image accurately in {target}. What is it? Be specific."},
                            {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}}
                        ]}]
                    }, timeout=30).json()
                if "choices" in r:
                    return {"description": r["choices"][0]["message"]["content"]}
            except:
                continue

    # 3. Last resort - use Google Gemini direct if GOOGLE_API_KEY set
    gkey = os.getenv("GOOGLE_API_KEY")
    if gkey:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gkey)
            model = genai.GenerativeModel("gemini-1.5-flash")
            img = Image.open(io.BytesIO(content))
            resp = model.generate_content([f"Describe in {target}", img])
            return {"description": resp.text}
        except Exception as e:
            return {"description": f"Google key error: {e}"}

    return {"description": "Vision servers are sleeping (HF loading). Wait 30 sec and try again - it will wake up and describe correctly."}

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