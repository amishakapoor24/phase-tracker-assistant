import os
from groq import Groq

client = None

def get_groq_client():
    global client
    if client is None:
        client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    return client

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribes audio bytes (WebM, WAV, etc.) to text using Groq's Whisper model.
    """
    try:
        c = get_groq_client()
        
        transcription = c.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3-turbo",
            response_format="json"
        )
        return transcription.text
            
    except Exception as e:
        return f"ERROR: Unexpected error during transcription: {str(e)}"
