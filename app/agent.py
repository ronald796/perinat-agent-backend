import math

def calculate_hadlock_efw(bpd, ac, fl):
    """Calcula el peso fetal estimado usando la fórmula de Hadlock"""
    # Convertimos mm a cm para la fórmula
    b = bpd / 10
    a = ac / 10
    f = fl / 10

    # Fórmula de Hadlock: Log10 BW = 1.335 - 0.0034AC(FL) + 0.0316BPD + 0.0457AC + 0.190FL
    log10_bw = 1.335 - (0.0034 * a * f) + (0.0316 * b) + (0.0457 * a) + (0.190 * f)
    weight_kg = 10**log10_bw
    return round(weight_kg * 1000, 2)  # Retornamos en gramos

def generate_perinatology_report(data):
    # Ejecutamos el cálculo automático
    efw_calculado = calculate_hadlock_efw(data.bpd, data.ac, data.fl)

    # Análisis de desarrollo
    status = "desarrollo acorde a edad gestacional"
    if data.gestational_age_weeks > 0 and efw_calculado < 300 and data.gestational_age_weeks >= 20:
        status = "alerta: peso por debajo del percentil esperado (RCIU?)"

    # Construcción del informe
    report_text = (
        f"INFORME MÉDICO DE PERINATOLOGÍA\n"
        f"Paciente: {data.patient_name} | ID: {data.patient_id}\n"
        f"Edad Gestacional: {data.gestational_age_weeks} semanas.\n\n"
        f"HALLAZGOS BIOMÉTRICOS:\n"
        f"- Diámetro Biparietal (DBP): {data.bpd} mm\n"
        f"- Circunferencia Abdominal (CA): {data.ac} mm\n"
        f"- Longitud Femoral (LF): {data.fl} mm\n"
        f"- PESO FETAL ESTIMADO (HADLOCK): {efw_calculado} g.\n\n"
        f"INTERPRETACIÓN: Se observa {status}."
    )

    if data.doctor_observations:
        report_text += f"\n\nNOTAS DEL FACULTATIVO: {data.doctor_observations}"

    return {
        "summary": report_text,
        "recommendation": "Control de crecimiento en 2-4 semanas según protocolo."
    }
