from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json, os, requests, urllib.parse, base64
from datetime import datetime

# Optional brain
try:
    from llama_brain import get_baymax_reply
except ImportError:
    def get_baymax_reply(msg):
        return f"Baymax heard: {msg}"

app = FastAPI()
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

def parse_lang(raw: str) -> str:
    s = raw.lower().strip()
    if "chinese" in s or s in ["zh", "cn"]:
        return "zh-CN"
    return s[:6] if len(s) <= 6 else "en"

translation_cache = {}

def translate_unlimited(text, src, tgt):
    sm = src.split('-')[0].lower()
    tm = tgt.split('-')[0].lower()
    if sm == tm or not text.strip():
        return text
    for url in [
        f"https://ftapi.pythonanywhere.com/translate?sl={sm}&dl={tm}&text={urllib.parse.quote(text)}",
        f"https://ftapi.vedhatech.com/translate?sl={sm}&dl={tm}&text={urllib.parse.quote(text)}",
    ]:
        try:
            r = requests.get(url, timeout=15).json()
            if r.get("destination-text"):
                return r["destination-text"]
        except:
            pass
    try:
        r = requests.get(f"https://lingva.ml/api/v1/{sm}/{tm}/{urllib.parse.quote(text)}", timeout=10).json()
        return r.get("translation", text)
    except:
        return text

@app.get("/api")
def api_home():
    return {"status": "Baymax online - FREE vision ready"}

@app.post("/chat")
def chat(req: ChatRequest):
    return {"reply": get_baymax_reply(req.message)}

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    src = parse_lang(req.from_lang)
    tgt = parse_lang(req.to_lang)
    text = req.text.strip()
    if not text or src == tgt:
        return {"translated": text}
    k = f"{src}:{tgt}:{text.lower()}"
    if k in translation_cache:
        return {"translated": translation_cache[k]}
    tr = translate_unlimited(text, src, tgt)
    translation_cache[k] = tr
    return {"translated": tr}

@app.post("/api/screen-analyze")
async def screen_analyze(file: UploadFile = File(...), lang: str = "en"):
    content = await file.read()
    target = parse_lang(lang)
    b64 = base64.b64encode(content).decode()
    mime = file.content_type or "image/jpeg"

    # 1. Try HuggingFace FREE vision (no key needed)
    hf_models = [
        "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large",
        "https://api-inference.huggingface.co/models/nlpconnect/vit-gpt2-image-captioning",
    ]
    for hf_url in hf_models:
        try:
            resp = requests.post(hf_url, data=content, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    caption = data[0].get("generated_text", "")
                    if caption:
                        if target!= "en":
                            caption = translate_unlimited(caption, "en", target)
                        return {"description": f"DETECTED: {caption}"}
        except Exception as e:
            print(f"HF {hf_url} failed: {e}")
            continue

    # 2. Try OpenRouter if you have a key (works with free models too)
    key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_KEY")
    if key:
        for model_id in [
            "qwen/qwen2.5-vl-7b-instruct:free",
            "google/gemma-3-4b-it:free",
            "google/gemma-3-12b-it:free",
        ]:
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_id,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"Describe this image accurately in {target} language. Be specific about what you see."},
                                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                                ],
                            }
                        ],
                    },
                    timeout=40,
                ).json()
                if "choices" in r and len(r["choices"]) > 0:
                    return {"description": r["choices"][0]["message"]["content"]}
            except Exception as e:
                print(f"Model {model_id} failed: {e}")
                continue

    return {"description": "Vision servers are waking up (cold start). Please wait 20 seconds and try again - HuggingFace will respond with real description."}

@app.post("/api/pulse")
def save_pulse(req: PulseRequest):
    entry = {"bpm": req.bpm, "time": datetime.now().isoformat(), "user": req.user_id}
    with open(DATA_FILE, "r") as f:
        h = json.load(f)
    h.append(entry)
    with open(DATA_FILE, "w") as f:
        json.dump(h[-100:], f, indent=2)
    return {"status": "saved", "entry": entry}

@app.get("/api/pulse")
def get_pulse():
    with open(DATA_FILE, "r") as f:
        return json.load(f)[::-1]

@app.get("/api/pulse/latest")
def get_latest():
    with open(DATA_FILE, "r") as f:
        h = json.load(f)
        return h[-1] if h else {}

# Serve frontend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="frontend")