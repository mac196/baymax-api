import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

client = None
if api_key:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        print("[BAYMAX] Groq connected")
    except Exception as e:
        print(f"[BAYMAX] Groq init failed: {e}")
        client = None
else:
    print("[BAYMAX] No GROQ_API_KEY found in.env - using offline mode")

def get_baymax_reply(message: str) -> str:
    if not client:
        return f"Baymax here (offline mode): I heard '{message}'. Add your GROQ_API_KEY to.env to enable AI."

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are Baymax, a personal healthcare companion. Be caring, concise."},
                {"role": "user", "content": message}
            ],
            max_tokens=300
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq error: {e}")
        return f"Baymax (error fallback): {message[:100]}"