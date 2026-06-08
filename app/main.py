import uuid
import io
import pydicom
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import FetalMeasurements, AnalysisResponse, DicomData, ReportRequest, ReportResponse
from .agent import generate_structured_report
from .audio_processor import transcribe_audio

app = FastAPI(title="Perinato-AI Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "entorno": "Perinato-AI Node",
        "fase": 5,
        "status": "Ready",
        "agente_ia": "Online"
    }

@app.post("/analyze", response_model=ReportResponse)
async def analyze_ultrasound(data: ReportRequest):
    report_id = str(uuid.uuid4())[:8]

    result = await generate_structured_report(data)

    # Construir dict de secciones con los valores tal cual los envió el médico (AI no los toca)
    secciones = {}
    for field in ["obstetricos", "biometria", "anatomia", "funcional",
                  "placenta", "ecocardiografia", "perfil_biofisico", "doppler"]:
        section = getattr(data, field, None)
        if section is not None:
            secciones[field] = section.model_dump(exclude_none=True)

    return {
        "status": "success",
        "report_id": report_id,
        "biometria_derivada": {
            "efw_g": result["efw"],
            "formula": result["formula"],
            "eg_estimada_semanas": result["eg_estimada"],
        },
        "impresion_diagnostica": result["impresion_diagnostica"],
        "recomendaciones": result["recomendaciones"],
        "secciones": secciones,
    }

def _parse_sr_biometry(ds):
    out = {"bpd": None, "hc": None, "ac": None, "fl": None, "ga_weeks": None}

    def walk(seq):
        for item in seq:
            if (getattr(item, "ValueType", "") == "NUM"
                    and "ConceptNameCodeSequence" in item
                    and "MeasuredValueSequence" in item):
                name = str(item.ConceptNameCodeSequence[0].CodeMeaning).lower()
                try:
                    val = float(item.MeasuredValueSequence[0].NumericValue)
                except Exception:
                    continue
                if "biparietal" in name:
                    out["bpd"] = val
                elif "head circumference" in name or "cefal" in name or "cabeza" in name:
                    out["hc"] = val
                elif "abdominal" in name:
                    out["ac"] = val
                elif "femur" in name or "fémur" in name:
                    out["fl"] = val
                elif "gestational" in name or "gestacional" in name:
                    out["ga_weeks"] = val
            if "ContentSequence" in item:
                walk(item.ContentSequence)

    if "ContentSequence" in ds:
        walk(ds.ContentSequence)
    return out


@app.post("/upload-dicom", response_model=DicomData)
async def upload_dicom(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.dcm'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .dcm")

    content = await file.read()
    try:
        ds = pydicom.dcmread(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"DICOM inválido: {str(e)}")

    patient_name = str(ds.get("PatientName", "Anónimo")).replace("^", " ").strip()
    patient_id = str(ds.get("PatientID", "SIN-ID"))
    modality = str(ds.get("Modality", "SR"))
    manufacturer = str(ds.get("Manufacturer", ""))

    b = _parse_sr_biometry(ds)

    return {
        "status": "success",
        "patient_name": patient_name,
        "patient_id": patient_id,
        "modality": modality,
        "manufacturer": manufacturer,
        "gestational_age_weeks": int(b["ga_weeks"]) if b["ga_weeks"] else None,
        "bpd": b["bpd"],
        "hc": b["hc"],
        "ac": b["ac"],
        "fl": b["fl"],
        "message": f"DICOM de {patient_name} cargado correctamente"
    }

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.mp4', '.webm', '.ogg', '.opus')):
        raise HTTPException(status_code=400, detail="Formato de audio no soportado")

    audio_content = await file.read()
    texto_transcrito = await transcribe_audio(audio_content, file.filename)

    return {
        "status": "success",
        "transcription": texto_transcrito,
        "usage": "Copia este texto en el campo doctor_observations para el análisis final"
    }
