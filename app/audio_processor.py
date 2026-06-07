import httpx
import os
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

async def transcribe_audio(file_bytes: bytes, filename: str):
    """
    Envía el archivo de audio a Groq (Whisper-large-v3)
    para obtener la transcripción en texto.
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada en el servidor")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    files = {
        "file": (filename, file_bytes),
        "model": (None, "whisper-large-v3"),
        "language": (None, "es")
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, files=files, timeout=60.0)

            if response.status_code == 200:
                return response.json().get("text", "")
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"Error de Groq ({response.status_code}): {response.text}"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error de conexión con Groq: {str(e)}")
