import os
import traceback

from fastapi import APIRouter, HTTPException
from typing import Literal

from pydantic import BaseModel, Field
from services.chat_service import generate_chat_response

router = APIRouter()

class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    conversation: list[ConversationMessage] = Field(default_factory=list, max_length=12)
    user: dict | None = None

@router.post("/")
async def chat_with_ai(request: ChatRequest):
    """
    Accepts text (usually from STT), sends it to Groq LLM,
    and returns the AI's response text.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")

    try:
        ai_response = generate_chat_response(
            request.text,
            conversation=[message.model_dump() for message in request.conversation],
            user=request.user,
        )
        
        if ai_response.startswith("ERROR:"):
            raise RuntimeError(ai_response.removeprefix("ERROR: ").strip())
            
        return {
            "success": True,
            "response": ai_response
        }
    except Exception as e:
        print(f"Chat provider error: {e}", flush=True)
        traceback.print_exc()
        detail = str(e) if os.getenv("ENVIRONMENT", "development") != "production" else "Chat service unavailable"
        raise HTTPException(status_code=502, detail=detail) from e
