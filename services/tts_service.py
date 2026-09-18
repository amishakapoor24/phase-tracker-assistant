from gtts import gTTS
import tempfile
import os

def generate_audio_from_text(text: str) -> str:
    """
    Converts text to speech using Google TTS (gTTS).
    Returns the file path to the generated MP3 file.
    """
    try:
        # Create the TTS object
        tts = gTTS(text=text, lang="en", slow=False)
        
        # Save to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.close() # Close so gTTS can write to it
        
        tts.save(temp_file.name)
        return temp_file.name
        
    except Exception as e:
        return f"ERROR: {str(e)}"
