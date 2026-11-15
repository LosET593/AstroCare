
from math import isfinite


# Rangos experimentales para el prototipo.
# No constituyen criterios médicos validados.

THRESHOLDS = {
    "heart_rate": {
        "normal": (55, 95),
        "warning": (45, 120),
    },
    "spo2": {
        "normal": (95, 100),
        "warning": (90, 100),
    },
    "body_temperature": {
        "normal": (36.2, 37.4),
        "warning": (35.5, 38.2),
    },
    "glucose": {
        "normal": (75, 135),
        "warning": (60, 180),
    },
    "sleep_hours": {
        "normal": (6.5, 8.5),
        "warning": (5.0, 10.0),
    },
    "mood_score": {
        "normal": (7, 10),
        "warning": (4, 10),
    },
}

STATUS_PRIORITY = {
    "unknown": 0,
    "normal": 1,
    "warning": 2,
    "critical": 3,
}


def classify_value(field, value):
    """Clasifica una medición individual."""

    if value is None:
        return {
            "status": "unknown",
            "value": None,
            "reason": "No hay una medición disponible."
        }

    if isinstance(value, bool):
        return {
            "status": "unknown",
            "value": value,
            "reason": "Medición inválida."
        }

    try:
        value = float(value)
    except (ValueError, TypeError):
        return {
            "status": "unknown",
            "value": value,
            "reason": "Medición no numérica."
        }

    if not isfinite(value):
        return {
            "status": "unknown",
            "value": value,
            "reason": "Medición no válida."
        }

    if field == "systolic_pressure":
        return None

    if field == "diastolic_pressure":
        return None

    if field not in THRESHOLDS:
        return {
            "status": "unknown",
            "value": value,
            "reason": "Indicador no reconocido."
        }

    limits = THRESHOLDS[field]
    normal_min, normal_max = limits["normal"]
    warning_min, warning_max = limits["warning"]

    if normal_min <= value <= normal_max:
        status = "normal"
        reason = "Dentro del rango nominal experimental."

    elif warning_min <= value <= warning_max:
        status = "warning"
        reason = "Fuera del rango nominal."

    else:
        status = "critical"
        reason = "Fuera del rango de advertencia."

    # SpO2: valores inferiores a 90 son críticos.
    # Valores superiores a 100 no son válidos.
    if field == "spo2" and value > 100:
        status = "unknown"
        reason = "Valor fuera del rango de medición."

    return {
        "status": status,
        "value": value,
        "reason": reason
    }


def classify_blood_pressure(systolic, diastolic):
    """Evalúa conjuntamente presión sistólica y diastólica."""

    if systolic is None or diastolic is None:
        return {
            "status": "unknown",
            "value": None,
            "reason": "Se necesitan ambas mediciones."
        }

    try:
        systolic = float(systolic)
        diastolic = float(diastolic)
    except (ValueError, TypeError):
        return {
            "status": "unknown",
            "value": None,
            "reason": "Mediciones inválidas."
        }

    if not isfinite(systolic) or not isfinite(diastolic):
        return {
            "status": "unknown",
            "value": None,
            "reason": "Mediciones no válidas."
        }

    if systolic < 40 or systolic > 250 or diastolic < 20 or diastolic > 150:
        return {
            "status": "unknown",
            "value": {
                "systolic": systolic,
                "diastolic": diastolic
            },
            "reason": "Valores fuera del rango de validación."
        }

    if systolic <= diastolic:
        return {
            "status": "unknown",
            "value": {
                "systolic": systolic,
                "diastolic": diastolic
            },
            "reason": "Relación sistólica/diastólica inválida."
        }

    critical = (
        systolic < 90 or systolic > 145
        or diastolic < 55 or diastolic > 95
    )

    warning = (
        systolic < 100 or systolic > 130
        or diastolic < 65 or diastolic > 85
    )

    if critical:
        status = "critical"
        reason = "Presión fuera del rango de advertencia."

    elif warning:
        status = "warning"
        reason = "Presión fuera del rango nominal."

    else:
        status = "normal"
        reason = "Dentro del rango nominal experimental."

    return {
        "status": status,
        "value": {
            "systolic": systolic,
            "diastolic": diastolic
        },
        "reason": reason
    }


def analyze_measurements(data):
    """Analiza todos los indicadores recibidos."""

    results = {}

    for field in THRESHOLDS:
        results[field] = classify_value(
            field,
            data.get(field)
        )

    results["blood_pressure"] = classify_blood_pressure(
        data.get("systolic_pressure"),
        data.get("diastolic_pressure")
    )

    available_statuses = [
        item["status"]
        for item in results.values()
        if item["status"] != "unknown"
    ]

    if not available_statuses:
        overall = "unknown"
    else:
        overall = max(
            available_statuses,
            key=lambda status: STATUS_PRIORITY[status]
        )

    return {
        "indicators": results,
        "overall_status": overall
    }
