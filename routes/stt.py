from fastapi import APIRouter, UploadFile, File, HTTPException
from services.stt_service import transcribe_audio

router = APIRouter()

@router.post("/")
async def convert_speech_to_text(audio: UploadFile = File(...)):
    """
    Accepts an uploaded audio file (WebM, WAV, etc.), processes it using 
    Groq Whisper, and returns the transcribed text.
    """
    try:
        # Read the audio bytes from the upload
        audio_bytes = await audio.read()
        
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file uploaded")
            
        # Process audio to text
        transcription = transcribe_audio(audio_bytes, filename=audio.filename)
        
        # Check for errors from our service
        if transcription.startswith("ERROR:"):
            raise HTTPException(status_code=500, detail=transcription)
            
        return {
            "success": True,
            "text": transcription
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
