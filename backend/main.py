from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llama_brain import get_baymax_reply

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {"status": "Baymax online - 100% round head"}

@app.post("/chat")
def chat(req: ChatRequest):
    reply = get_baymax_reply(req.message)
    return {"reply": reply}