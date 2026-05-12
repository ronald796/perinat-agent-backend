from pydantic import BaseModel, Field
from typing import Optional

class FetalMeasurements(BaseModel):
    patient_id: str
    patient_name: Optional[str] = "Paciente Anónimo"
    gestational_age_weeks: int
    bpd: float
    ac: float
    fl: float
    efw: Optional[float] = 0
    doctor_observations: str

class AnalysisResponse(BaseModel):
    status: str
    report_id: str
    summary: str
    recommendation: str

class DicomData(BaseModel):
    status: str
    patient_name: str
    patient_id: str
    modality: str
    manufacturer: Optional[str] = ""
    gestational_age_weeks: Optional[int] = None
    bpd: Optional[float] = None
    ac: Optional[float] = None
    fl: Optional[float] = None
    message: str
