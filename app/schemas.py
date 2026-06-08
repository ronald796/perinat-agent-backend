from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ── Modelos existentes (no se tocan para no romper /upload-dicom) ──────────

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


# ── Nuevas secciones del informe estructurado ──────────────────────────────

class Obstetricos(BaseModel):
    embarazo: Optional[str] = None       # "Único", "Gemelar", etc.
    situacion: Optional[str] = None      # "Longitudinal", "Transversa", "Oblicua"
    posicion: Optional[str] = None       # "Derecha", "Izquierda"
    feto: Optional[str] = None           # "Vivo", "Muerto"
    presentacion: Optional[str] = None  # "Cefálica de vértice", "Podálica", etc.
    situs: Optional[str] = None         # "Solitus", "Inversus"

class Biometria(BaseModel):
    dbp: Optional[float] = None          # mm — diámetro biparietal
    cc: Optional[float] = None           # mm — circunferencia cefálica (HC)
    ca: Optional[float] = None           # mm — circunferencia abdominal
    femur: Optional[float] = None        # mm — longitud femoral
    cerebelo: Optional[float] = None     # mm
    atrio: Optional[float] = None        # mm — atrio ventricular
    ap_cardiaco: Optional[float] = None  # mm — diámetro AP cardíaco
    ap_torax: Optional[float] = None     # mm — diámetro AP torácico
    transv_abd: Optional[float] = None   # mm — diámetro transverso abdominal
    talla_cm: Optional[float] = None     # cm — talla estimada

class Anatomia(BaseModel):
    polo_cefalico: Optional[str] = None   # "Normal" / "Anormal" / "No evaluado"
    neurocraneo: Optional[str] = None
    columna: Optional[str] = None
    rostro: Optional[str] = None
    torax: Optional[str] = None
    corazon: Optional[str] = None
    abdomen: Optional[str] = None
    rinones: Optional[str] = None
    extremidades: Optional[str] = None
    sexo: Optional[str] = None            # "Masculino" / "Femenino" / "No determinado"

class Funcional(BaseModel):
    actitud_global: Optional[str] = None
    actividad_cardiaca: Optional[str] = None
    tono: Optional[str] = None
    mov_respiratorios: Optional[str] = None
    vejiga: Optional[str] = None
    camara_gastrica: Optional[str] = None
    liquido_amniotico: Optional[str] = None   # "Normal" / "Aumentado" / "Disminuido"
    ila: Optional[float] = None               # cm — índice de líquido amniótico

class Placenta(BaseModel):
    localizacion: Optional[str] = None        # "Anterior", "Posterior", "Fúndica", etc.
    grado_madurez: Optional[str] = None       # "0", "I", "II", "III"
    grosor_cm: Optional[float] = None
    cordon_vasos: Optional[str] = None        # "3 vasos", "2 vasos"

class Ecocardiografia(BaseModel):
    situs: Optional[str] = None
    cuatro_camaras: Optional[str] = None
    tres_vasos_traquea: Optional[str] = None
    arcos: Optional[str] = None
    conexiones: Optional[str] = None
    ritmo: Optional[str] = None
    fc_lpm: Optional[int] = None

class PerfilBiofisico(BaseModel):
    puntaje: Optional[int] = None             # 0–10

class Doppler(BaseModel):
    umbilical_sd: Optional[float] = None
    acm_pi: Optional[float] = None
    uterina_ip_der: Optional[float] = None
    uterina_ip_izq: Optional[float] = None
    ductus_venoso: Optional[str] = None       # "Normal" / "Anormal" / texto libre


# ── Request y Response del informe estructurado ───────────────────────────

class ReportRequest(BaseModel):
    patient_name: Optional[str] = "Paciente Anónimo"
    patient_id: str
    gestational_age_weeks: int
    doctor_observations: Optional[str] = ""
    obstetricos: Optional[Obstetricos] = None
    biometria: Optional[Biometria] = None
    anatomia: Optional[Anatomia] = None
    funcional: Optional[Funcional] = None
    placenta: Optional[Placenta] = None
    ecocardiografia: Optional[Ecocardiografia] = None
    perfil_biofisico: Optional[PerfilBiofisico] = None
    doppler: Optional[Doppler] = None

class ReportResponse(BaseModel):
    status: str
    report_id: str
    biometria_derivada: Dict[str, Any]
    impresion_diagnostica: List[str]
    recomendaciones: List[str]
    secciones: Dict[str, Any]
