import httpx
import os
from dotenv import load_dotenv

# Cargamos las variables del archivo .env
load_dotenv()

async def transcribe_audio(file_bytes: bytes, filename: str):
    """
    Envía el archivo de audio a Groq (Whisper-large-v3)
    para obtener la transcripción en texto.
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return "Error: No se encontró la API Key de Groq en el archivo .env"

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    # Preparamos el archivo para la petición multipart/form-data
    files = {
        "file": (filename, file_bytes),
        "model": (None, "whisper-large-v3"),
        "language": (None, "es")  # Forzamos español para términos médicos precisos
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, files=files, timeout=60.0)

            if response.status_code == 200:
                return response.json().get("text", "")
            else:
                return f"Error en la API de Groq ({response.status_code}): {response.text}"
        except Exception as e:
            return f"Error de conexión al procesar audio: {str(e)}"
