from fastapi import FastAPI
from .schemas import FetalMeasurements
from .agent import generate_perinatology_report

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Agente de Perinatologia Online"}

@app.post("/analyze")
async def analyze_ultrasound(data: FetalMeasurements):
    # Llamamos al agente para generar el borrador
    report = generate_perinatology_report(data)
    return {
        "status": "success",
        "report": report
    }
