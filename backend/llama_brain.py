import os
import base64
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

client = None
if api_key:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        print("[BAYMAX AUTO] Groq connected - 广州车载大脑上线")
    except Exception as e:
        print(f"[BAYMAX] Groq init failed: {e}")
else:
    print("[BAYMAX] No GROQ_API_KEY - offline 广州模式")

# --- CAR SYSTEM PROMPTS BY MODE ---
PROMPTS = {
    "yue_default": """
你是Baymax车载大脑，驻广州。天河区长大，95%讲粤语，5%英文术语。
性格：暖男 + 老广的哥，识路、识平、识叹。
规则：
- 默认全部用粤语(广府话)口语回答，亲切自然，唔好书面语
- 讲地名：天河城、珠江新城、科韵路、琶洲、番禺
- 懂车：电量、续航、充电桩、空调、路况
- 结尾带一句关心或行动建议
- 简洁，2-4句，似对讲机
""",
    "commute": "你是广州通勤专家。熟悉内环、科韵路、黄埔大道拥堵。回答用粤语，帮用户避堵、算电量、推荐充电桩。语气老练。",
    "battery": "你是电池管家。语气专业但温暖。用粤语解释电量、续航、谷电优惠。广州天河城B2桩、家充00:00优惠要识。",
    "safety": "你是安全卫士。语气冷静专业。讲疲劳、急刹、胎压。用粤语提醒，唔好吓親人，但要坚定。",
    "screen": "你是屏幕视界。用户发来车内/车外照片，你要粤语描述画面，指出关键信息(路牌、电量表、危险)。",
    "voice": "你是语音中枢。粤语回应，识别粤语指令：开空调、去边度、仲有几多电。简短口令式。",
    "action": "你是执行大脑。用户讲行动，你确认执行：已开XX、已调XX。用粤语确认。",
}

VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct", # best for vision
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview",
]

TEXT_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
]

def get_baymax_reply(msg: str, mode: str = "auto", lang: str = "yue", image_b64: str | None = None) -> dict:
    # Choose prompt
    sys_prompt = PROMPTS.get(mode, PROMPTS["yue_default"])
    if mode == "auto":
        sys_prompt = PROMPTS["yue_default"]
    # Force Cantonese if lang=yue
    if lang == "yue":
        sys_prompt += "\n必须用95%粤语口语回答。"

    # Offline fallback with Guangzhou flavor
    if not client:
        offline = {
            "commute": "今朝内环塞，走科韵路快6分钟，电量够你来回天河城。",
            "battery": "而家82%，够用到夜晚，凌晨12点充最平 ¥0.38。",
            "safety": "检测到你有啲攰，休息10分钟先啦，安全第一。",
            "screen": "睇到画面啦，暂时离线模式，联网后帮你细睇。",
        }
        txt = offline.get(mode, f"Baymax听住呢：{msg}，我而家离线，联网后讲粤语帮你。")
        return {"reply": txt, "mode": mode, "lang": lang}

    # Build messages
    messages = [{"role": "system", "content": sys_prompt}]

    if image_b64:
        # Vision path
        # Clean data URI
        if "," in image_b64 and "base64" in image_b64:
            # keep as is for Groq format
            image_url = image_b64
        else:
            image_url = f"data:image/jpeg;base64,{image_b64}"

        user_content = [
            {"type": "text", "text": msg},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
        messages.append({"role": "user", "content": user_content})
        models_to_try = VISION_MODELS + TEXT_MODELS
    else:
        messages.append({"role": "user", "content": msg})
        models_to_try = TEXT_MODELS

    for model in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=400,
                temperature=0.7,
            )
            reply_text = completion.choices[0].message.content
            return {
                "reply": reply_text,
                "mode": mode,
                "model": model,
                "lang": lang
            }
        except Exception as e:
            print(f"[BAYMAX] Model {model} failed: {e}")
            continue

    # Final fallback
    return {"reply": f"唔好意思，网络卡咗，但Baymax听住呢：{msg[:80]}，等我转头再讲你听。", "mode": mode}