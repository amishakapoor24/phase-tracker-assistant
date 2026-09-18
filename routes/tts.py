from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from services.tts_service import generate_audio_from_text

router = APIRouter()

class TTSRequest(BaseModel):
    text: str

def remove_file(path: str):
    """Utility to delete the temporary audio file after it's been sent."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error removing temp file: {e}")

@router.post("/")
async def convert_text_to_speech(request: TTSRequest, background_tasks: BackgroundTasks):
    """
    Accepts text, converts it to speech using gTTS, 
    and returns an MP3 audio file.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")

    try:
        audio_file_path = generate_audio_from_text(request.text)
        
        if audio_file_path.startswith("ERROR:"):
            raise HTTPException(status_code=500, detail=audio_file_path)
            
        # Ensure the file gets deleted after the response is sent to save disk space
        background_tasks.add_task(remove_file, audio_file_path)
        
        return FileResponse(
            path=audio_file_path, 
            media_type="audio/mpeg", 
            filename="response.mp3"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
