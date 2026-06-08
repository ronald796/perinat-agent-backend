import os
import json
import re
import httpx
from fastapi import HTTPException
from .schemas import ReportRequest


def calculate_hadlock_efw(bpd_mm: float, ac_mm: float, fl_mm: float, hc_mm: float = None) -> tuple:
    """
    Hadlock 4-parámetros si hc disponible, 3-parámetros si no.
    Retorna (efw_gramos, nombre_formula).
    """
    b = bpd_mm / 10
    a = ac_mm / 10
    f = fl_mm / 10
    if hc_mm is not None:
        h = hc_mm / 10
        # Hadlock 1985 – BPD + HC + AC + FL (medidas en cm)
        log10_bw = 1.3596 + 0.0064*h + 0.0424*a + 0.174*f + 0.00061*b*a - 0.00386*a*f
        formula = "Hadlock 4 parámetros (DBP+CC+CA+FL)"
    else:
        # Hadlock 1985 – BPD + AC + FL
        log10_bw = 1.335 - (0.0034 * a * f) + (0.0316 * b) + (0.0457 * a) + (0.190 * f)
        formula = "Hadlock 3 parámetros (DBP+CA+FL)"
    return round((10**log10_bw) * 1000, 2), formula


def estimate_ga_from_bpd(bpd_mm: float) -> float:
    """Estima EG en semanas a partir del DBP usando curva de Hadlock (BPD en cm)."""
    b = bpd_mm / 10
    return round(9.54 + 1.482 * b + 0.1676 * b**2, 1)


def _fmt_section(title: str, obj) -> str:
    if obj is None:
        return ""
    data = obj.model_dump(exclude_none=True)
    if not data:
        return ""
    lines = [f"\n## {title}"]
    for k, v in data.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


async def generate_structured_report(data: ReportRequest) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada en el servidor")

    # Calcular biometría derivada
    bio = data.biometria
    efw, formula = (None, None)
    eg_estimada = None

    if bio and bio.dbp and bio.ca and bio.femur:
        efw, formula = calculate_hadlock_efw(bio.dbp, bio.ca, bio.femur, bio.cc)
    if bio and bio.dbp:
        eg_estimada = estimate_ga_from_bpd(bio.dbp)

    # Construir resumen de datos para el prompt
    sections_text = (
        _fmt_section("Datos obstétricos", data.obstetricos)
        + _fmt_section("Biometría (valores en mm salvo talla_cm)", data.biometria)
        + _fmt_section("Anatomía fetal", data.anatomia)
        + _fmt_section("Parámetros funcionales", data.funcional)
        + _fmt_section("Placenta y cordón", data.placenta)
        + _fmt_section("Ecocardiografía", data.ecocardiografia)
        + _fmt_section("Perfil biofísico", data.perfil_biofisico)
        + _fmt_section("Doppler", data.doppler)
    )

    efw_line = f"- Peso fetal estimado ({formula}): {efw} g" if efw else "- Peso fetal estimado: no calculable (datos biométricos insuficientes)"
    eg_line = f"- EG estimada por DBP: {eg_estimada} semanas" if eg_estimada else ""
    obs_line = f"- Observaciones del médico: {data.doctor_observations}" if data.doctor_observations else ""

    prompt = f"""Eres un perinatólogo experto. Analiza el siguiente estudio ultrasonográfico y genera una evaluación clínica.

PACIENTE: {data.patient_name} | ID: {data.patient_id}
EDAD GESTACIONAL CLÍNICA: {data.gestational_age_weeks} semanas
{efw_line}
{eg_line}
{obs_line}
{sections_text}

REGLAS ABSOLUTAS:
1. NO inventes ni modifiques ningún valor medido. Lo que no esté reportado arriba se describe como "no reportado".
2. Evalúa si la biometría es normal para la edad gestacional indicada.
3. Si hay hallazgos anormales, nómbralos explícitamente.
4. Las recomendaciones deben ser concretas y etiquetadas como sugerencias para el médico tratante.

Responde ÚNICAMENTE con un objeto JSON válido con estas dos claves:
{{
  "impresion_diagnostica": ["frase 1", "frase 2", ...],
  "recomendaciones": ["recomendación 1", "recomendación 2", ...]
}}
No incluyas texto fuera del JSON."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "Eres un asistente médico especializado en perinatología. Respondes SOLO con JSON válido, sin texto adicional."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=60.0
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error de conexión con Groq: {str(e)}")

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Error de Groq ({response.status_code}): {response.text}")

    ai_text = response.json()["choices"][0]["message"]["content"]

    # Parse JSON de forma segura
    try:
        ai_json = json.loads(ai_text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        ai_json = json.loads(match.group()) if match else {}

    def as_list(val, fallback: str) -> list:
        if isinstance(val, list) and val:
            return val
        if isinstance(val, str) and val:
            return [val]
        return [fallback]

    return {
        "efw": efw,
        "formula": formula,
        "eg_estimada": eg_estimada,
        "impresion_diagnostica": as_list(
            ai_json.get("impresion_diagnostica"),
            "No se pudo generar impresión diagnóstica."
        ),
        "recomendaciones": as_list(
            ai_json.get("recomendaciones"),
            "Seguimiento clínico habitual según protocolo."
        ),
    }
