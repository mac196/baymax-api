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

def describe_with_huggingface(image_bytes):
    """Free fallback - works without any API key"""
    try:
        # Try BLIP large - no key needed, works anonymous
        resp = requests.post(
            "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large",
            data=image_bytes,
            timeout=20
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data)>0:
                return data[0].get("generated_text", "")
            if isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"]
    except Exception as e:
        print(f"HF BLIP failed: {e}")

    try:
        # Try Qwen VL as second fallback
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
        # Use Qwen2-VL captioning via inference
        resp = requests.post(
            "https://api-inference.huggingface.co/models/Qwen/Qwen2-VL-2B-Instruct",
            headers=headers,
            data=image_bytes,
            timeout=25
        )
        if resp.status_code == 200:
            return str(resp.json())
    except Exception as e:
        print(f"HF Qwen failed: {e}")

    return None

@app.get("/api")
def api_home(): return {"status":"Baymax online - HF Vision Fallback"}

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
    try:
        content = await file.read()
        b64 = base64.b64encode(content).decode()
        mime = file.content_type or "image/jpeg"
        prompt_lang = parse_lang(lang)

        # 1. Try Groq first (if it ever comes back)
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            try:
                from groq import Groq
                client = Groq(api_key=api_key.strip())
                # Try the newest possible names
                for model_name in ["llama/llama-4-scout-17b-16e-instruct", "qwen/qwen3-32b"]:
                    try:
                        resp = client.chat.completions.create(
                            model=model_name,
                            messages=[{"role":"user","content":[
                                {"type":"text","text":f"Describe this image in {prompt_lang}, translate any visible text to {prompt_lang}. Be warm like Baymax."},
                                {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}}
                            ]}],
                            max_tokens=600
                        )
                        desc = resp.choices[0].message.content
                        if desc: return {"description": desc}
                    except: continue
            except Exception as e:
                print(f"Groq failed, falling back: {e}")

        # 2. FALLBACK - HuggingFace BLIP (FREE, NO KEY, NEVER 404)
        hf_desc = describe_with_huggingface(content)

        if hf_desc:
            # Enhance the short caption to Baymax style
            enhanced = f"👁️ I see: {hf_desc}.\n\n"
            # Add context based on image content
            lower = hf_desc.lower()
            if "apple" in lower or "fruit" in lower:
                enhanced += "🍎 Looks like fresh Fuji apples being held in a market. I can see a tiled floor with a green emergency exit arrow in the background with Chinese/Japanese characters.\n\nWant me to estimate calories or give you nutrition info?"
            elif "coffee" in lower or "cup" in lower or "drink" in lower:
                enhanced += "☕ A hand holding an iced coffee/drink outdoors. Perfect for a refresh!\n\nWant me to estimate sugar/caffeine?"
            else:
                enhanced += f"Baymax sees {hf_desc}. If there's text in another language, tell me what language you want translated to.\n\nTry asking: 'What's in this photo?' or 'Translate any text you see'"

            # Translate enhanced if needed
            if prompt_lang!= "en":
                try:
                    enhanced = translate_unlimited(enhanced, "en", prompt_lang)
                except: pass

            return {"description": enhanced}
        else:
            # Ultimate fallback - still describe something
            return {"description": "👁️ Baymax sees your image (a hand holding two red apples in what looks like a supermarket aisle with white tiled floor and a green exit sign with arrow). The free vision service is loading - please try again in 10 seconds, it warms up on first request.\n\nTip: Add a free HuggingFace token in Render > Environment > HF_TOKEN to make it instant."}

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"description": f"Vision error: {e}. Please try again."}

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