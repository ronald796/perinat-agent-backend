import os
import httpx
from .schemas import FetalMeasurements

def calculate_hadlock_efw(bpd, ac, fl):
    import math
    b, a, f = bpd / 10, ac / 10, fl / 10
    log10_bw = 1.335 - (0.0034 * a * f) + (0.0316 * b) + (0.0457 * a) + (0.190 * f)
    return round((10**log10_bw) * 1000, 2)

async def generate_smart_report(data: FetalMeasurements):
    api_key = os.getenv("GROQ_API_KEY")
    efw = calculate_hadlock_efw(data.bpd, data.ac, data.fl)

    prompt = f"""
    Eres un experto Perinatólogo. Redacta un informe médico profesional basado en estos datos:
    - Paciente: {data.patient_name}
    - Edad Gestacional: {data.gestational_age_weeks} semanas
    - Biometría: DBP {data.bpd}mm, CA {data.ac}mm, LF {data.fl}mm.
    - Peso Fetal Estimado: {efw}g.
    - Observaciones del doctor: {data.doctor_observations}

    El informe debe ser formal, estructurado y mencionar si los valores son normales para la edad gestacional.
    Usa un tono clínico. No inventes datos adicionales.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama3-70b-8192",
                "messages": [
                    {"role": "system", "content": "Eres un asistente médico especializado en perinatología."},
                    {"role": "user", "content": prompt}
                ]
            }
        )

    if response.status_code == 200:
        ai_message = response.json()['choices'][0]['message']['content']
        return {
            "summary": ai_message,
            "recommendation": "Seguimiento protocolar según guías ISUOG."
        }
    else:
        return {"summary": "Error generando informe IA", "recommendation": "Revisar conexión con API"}
