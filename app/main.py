from fastapi import FastAPI, UploadFile, File, HTTPException
from .schemas import FetalMeasurements
from .agent import generate_perinatology_report
from .audio_processor import transcribe_audio

app = FastAPI()

@app.get("/")
def read_root():
    return {
        "entorno": "Perinato-AI Node",
        "fase": 2,
        "status": "Ready",
        "agente_ia": "Online"
    }

@app.post("/analyze")
async def analyze_ultrasound(data: FetalMeasurements):
    report = generate_perinatology_report(data)
    return {
        "status": "success",
        "report": report
    }

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Endpoint para recibir notas de voz del doctor y convertirlas en texto.
    """
    if not file.filename.endswith(('.mp3', '.wav', '.m4a', '.webm')):
        raise HTTPException(status_code=400, detail="Formato de audio no soportado")

    audio_content = await file.read()

    texto_transcrito = await transcribe_audio(audio_content, file.filename)

    return {
        "status": "success",
        "transcription": texto_transcrito,
        "usage": "Copia este texto en el campo doctor_observations para el análisis final"
    }
