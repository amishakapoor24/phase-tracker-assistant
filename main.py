from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Create the FastAPI app
app = FastAPI(
    title="STS AI Assistant",
    description="Speech-to-Speech AI Assistant powered by Groq",
    version="1.0.0"
)

# CORS setup — allows React frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "https://phase-tracker.vercel.app"  # PhaseTracker on Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────
from routes.chat import router as chat_router
from routes.stt import router as stt_router
from routes.tts import router as tts_router

app.include_router(chat_router, prefix="/api/chat", tags=["LLM Chat"])
app.include_router(stt_router, prefix="/api/stt", tags=["Speech to Text"])
app.include_router(tts_router, prefix="/api/tts", tags=["Text to Speech"])

# ── Health Check ─────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "running",
        "message": "STS AI Assistant backend is live!",
        "endpoints": {
            "chat": "/api/chat",
            "stt": "/api/stt",
            "tts": "/api/tts",
            "docs": "/docs"
        }
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "STS AI Assistant"}
