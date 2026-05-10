from pydantic import BaseModel
from typing import Optional

class FetalMeasurements(BaseModel):
    patient_id: str
    gestational_age_weeks: int
    bpd: float 
    ac: float  
    fl: float  
    efw: Optional[float] = None 
    doctor_observations: str
