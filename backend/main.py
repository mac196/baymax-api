from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

@app.get("/docs-test")
def docs_test():
    return {"docs": "should be at /docs"}

@app.post("/chat")
def chat(req: ChatRequest):
    # temporary test - no AI yet
    return {"reply": f"You said: {req.message} - Baymax is testing!"}