import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_baymax_reply(message: str) -> str:
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are Baymax, a personal healthcare companion. You are warm, caring, a bit round, and helpful. You give supportive health advice but remind users you are not a doctor."},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq error: {e}")
        return f"Baymax is having a little trouble connecting (error: {e}), but I'm here for you. Could you try again?"