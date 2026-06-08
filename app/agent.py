import os
import json
import re
import httpx
from fastapi import HTTPException
from .schemas import ReportRequest


def calculate_hadlock_efw(bpd_mm: float, ac_mm: float, fl_mm: float, hc_mm: float = None) -> tuple:
    b = bpd_mm / 10
    a = ac_mm / 10
    f = fl_mm / 10
    if hc_mm is not None:
        h = hc_mm / 10
        log10_bw = 1.3596 + 0.0064*h + 0.0424*a + 0.174*f + 0.00061*b*a - 0.00386*a*f
        formula = "Hadlock 4 parámetros (DBP+CC+CA+FL)"
    else:
        log10_bw = 1.335 - (0.0034 * a * f) + (0.0316 * b) + (0.0457 * a) + (0.190 * f)
        formula = "Hadlock 3 parámetros (DBP+CA+FL)"
    return round(10**log10_bw, 2), formula


def estimate_ga_from_bpd(bpd_mm: float) -> float:
    b = bpd_mm / 10
    return round(9.54 + 1.482 * b + 0.1676 * b**2, 1)


_SECTION_LABELS = {
    "obstetricos":     "Datos obstétricos",
    "biometria":       "Biometría",
    "anatomia":        "Anatomía fetal",
    "funcional":       "Parámetros funcionales",
    "placenta":        "Placenta y cordón",
    "ecocardiografia": "Ecocardiografía",
    "perfil_biofisico":"Perfil biofísico",
    "doppler":         "Doppler",
}


def build_data_inventory(data: ReportRequest) -> tuple:
    """
    Devuelve (datos_provistos, no_reportado).
    datos_provistos: lista de strings con cada campo que tiene valor real.
    no_reportado:    lista de nombres de secciones que llegaron vacías o null.
    """
    datos = [
        f"Paciente: {data.patient_name} (ID: {data.patient_id})",
        f"Edad gestacional clínica: {data.gestational_age_weeks} semanas",
    ]
    if data.doctor_observations and data.doctor_observations.strip():
        datos.append(f"Observaciones del médico: {data.doctor_observations.strip()}")

    no_reportado = []

    for field, title in _SECTION_LABELS.items():
        section = getattr(data, field, None)
        if section is None:
            no_reportado.append(title)
            continue
        section_data = section.model_dump(exclude_none=True)
        if not section_data:
            no_reportado.append(title)
            continue
        for k, v in section_data.items():
            datos.append(f"{title} → {k}: {v}")

    return datos, no_reportado


async def generate_structured_report(data: ReportRequest) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada en el servidor")

    # Biometría derivada
    bio = data.biometria
    efw, formula = None, None
    eg_estimada = None

    if bio and bio.dbp and bio.ca and bio.femur:
        efw, formula = calculate_hadlock_efw(bio.dbp, bio.ca, bio.femur, bio.cc)
    if bio and bio.dbp:
        eg_estimada = estimate_ga_from_bpd(bio.dbp)

    # Inventario de datos
    datos_provistos, no_reportado = build_data_inventory(data)

    efw_entry = (
        f"Peso fetal estimado ({formula}): {efw} g"
        if efw else
        "Peso fetal estimado: NO CALCULABLE — biometría insuficiente (faltan dbp, ca o femur)"
    )
    datos_provistos.append(efw_entry)

    datos_str = "\n".join(f"  - {d}" for d in datos_provistos)
    no_rep_str = (
        "\n".join(f"  - {n}" for n in no_reportado)
        if no_reportado else "  (ninguna sección ausente)"
    )

    system_msg = (
        "Eres un asistente clínico de perinatología de alta precisión. "
        "Tu única función es analizar EXACTAMENTE los datos que se te presentan. "
        "NUNCA inventas, asumes, inferies ni completas información no presente. "
        "Respondes SOLO con JSON válido, sin texto adicional."
    )

    prompt = f"""Analiza este estudio ultrasonográfico perinatal con los datos disponibles.

=== DATOS PROVISTOS — los ÚNICOS que puedes mencionar ===
{datos_str}

=== SECCIONES NO REPORTADAS EN ESTE ESTUDIO — PROHIBIDO mencionarlas ===
{no_rep_str}

=== REGLAS DE SEGURIDAD CLÍNICA — obligatorias, sin excepciones ===
1. Solo puedes mencionar datos presentes en DATOS PROVISTOS. Ni uno más.
2. PROHIBIDO mencionar, inferir, asumir o declarar como normal cualquier hallazgo de las
   secciones NO REPORTADAS (presentación, placenta, anatomía, Doppler, líquido amniótico,
   ecocardiografía, perfil biofísico, etc.).
3. NUNCA uses frases como "el resto es normal", "sin otras alteraciones", "evaluación normal
   de estructuras no evaluadas", ni ninguna generalización sobre lo no reportado.
4. Si falta biometría, indica únicamente que el peso no pudo calcularse; no rellenes con
   hallazgos clínicos que no fueron registrados.
5. Si los datos provistos son escasos, la impresión debe reflejar esa limitación
   explícitamente: qué no se evaluó y qué falta para completar el estudio.
6. Impresión diagnóstica y recomendaciones se basan EXCLUSIVAMENTE en DATOS PROVISTOS.

Responde ÚNICAMENTE con este JSON (sin texto antes ni después):
{{
  "impresion_diagnostica": ["frase basada solo en datos provistos", ...],
  "recomendaciones": ["recomendación concreta para el médico tratante", ...]
}}"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=60.0
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error de conexión con Groq: {str(e)}")

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Error de Groq ({response.status_code}): {response.text}")

    ai_text = response.json()["choices"][0]["message"]["content"]

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
            "Completar el estudio con biometría y evaluación anatómica."
        ),
    }
