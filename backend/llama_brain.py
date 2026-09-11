from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODELS_TO_TRY = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "groq/compound-mini"
]

def ask_baymax(user_message: str):
    for model_name in MODELS_TO_TRY:
        try:
            print(f"Trying model: {model_name}")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are Baymax. Warm, caring, short reply under 50 words."},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=150
            )
            text = completion.choices[0].message.content
            if text and text.strip()!= "":
                print(f"SUCCESS with {model_name}: {text}")
                return text
        except Exception as e:
            print(f"Failed {model_name}: {e}")
            continue

    return "Hello, I am Baymax. I am here for you. On a scale of 1 to 10, how are you feeling? Ba-la-la-la~"