
from datetime import datetime, timedelta, timezone
from math import isfinite
from statistics import median

TREND_THRESHOLDS = {
    "heart_rate": 10.0,
    "spo2": 2.0,
    "body_temperature": 0.4,
    "glucose": 20.0
}

MIN_READINGS = 6
WINDOW_MINUTES = 60
MAX_AGE_MINUTES = 15
MIN_SPAN_MINUTES = 20
MAX_FUTURE_MINUTES = 2


def parse_timestamp(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except (ValueError, TypeError, AttributeError):
        return None


def insufficient(field, reason, **extra):
    return {
        "field": field,
        "status": "insufficient_data",
        "reason": reason,
        **extra
    }


def analyze_trend(history, field, device_id=None, now=None):
    if field not in TREND_THRESHOLDS:
        return {
            "field": field,
            "status": "unsupported",
            "reason": "Indicador sin análisis temporal configurado."
        }

    if not isinstance(history, list):
        return insufficient(field, "Historial no válido.")

    now = now or datetime.now(timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    now = now.astimezone(timezone.utc)

    # Validar la identidad de los dispositivos.
    device_ids = {
        item.get("device_id")
        for item in history
        if isinstance(item, dict) and item.get("device_id") is not None
    }

    has_missing_device = any(
        isinstance(item, dict) and item.get("device_id") is None
        for item in history
    )

    if device_id is None:
        if len(device_ids) > 1:
            return {
                "field": field,
                "status": "mixed_devices",
                "reason": "El historial contiene varios dispositivos."
            }

        if device_ids and has_missing_device:
            return {
                "field": field,
                "status": "ambiguous_device",
                "reason": "Hay mediciones sin identificar el dispositivo."
            }

    readings = []

    for item in history:
        if not isinstance(item, dict):
            continue

        if device_id is not None:
            if item.get("device_id") != device_id:
                continue

        value = item.get(field)
        timestamp = parse_timestamp(item.get("timestamp"))

        if value is None or timestamp is None:
            continue

        if isinstance(value, bool):
            continue

        try:
            value = float(value)
        except (ValueError, TypeError):
            continue

        if not isfinite(value):
            continue

        # Rechazar fechas demasiado adelantadas.
        if timestamp > now + timedelta(minutes=MAX_FUTURE_MINUTES):
            continue

        readings.append({
            "value": value,
            "timestamp": timestamp
        })

    if not readings:
        return insufficient(
            field,
            "No existen mediciones válidas para este dispositivo."
        )

    # Orden cronológico.
    readings.sort(key=lambda item: item["timestamp"])

    # Descartar todas las mediciones que compartan una marca temporal.
    timestamp_counts = {}

    for item in readings:
        timestamp = item["timestamp"]
        timestamp_counts[timestamp] = timestamp_counts.get(timestamp, 0) + 1

    readings = [
        item for item in readings
        if timestamp_counts[item["timestamp"]] == 1
    ]

    if not readings:
        return insufficient(
            field,
            "Todas las mediciones tienen marcas temporales duplicadas."
        )

    # Utilizar una ventana respecto al momento actual.
    cutoff = now - timedelta(minutes=WINDOW_MINUTES)

    readings = [
        item for item in readings
        if cutoff <= item["timestamp"] <= now
    ]

    if not readings:
        return insufficient(
            field,
            "No hay mediciones dentro de la ventana temporal."
        )

    latest_timestamp = readings[-1]["timestamp"]

    # Comprobar que el historial no esté obsoleto.
    age = now - latest_timestamp

    if age > timedelta(minutes=MAX_AGE_MINUTES):
        return insufficient(
            field,
            "La última medición es demasiado antigua.",
            latest_age_minutes=round(age.total_seconds() / 60, 2)
        )

    if len(readings) < MIN_READINGS:
        return insufficient(
            field,
            f"Se necesitan al menos {MIN_READINGS} mediciones válidas.",
            readings_count=len(readings)
        )

    # Comprobar la cobertura temporal.
    span = readings[-1]["timestamp"] - readings[0]["timestamp"]
    span_minutes = span.total_seconds() / 60

    if span_minutes < MIN_SPAN_MINUTES:
        return insufficient(
            field,
            f"Las mediciones deben abarcar al menos {MIN_SPAN_MINUTES} minutos.",
            readings_count=len(readings),
            span_minutes=round(span_minutes, 2)
        )

    # Comparar la mitad inicial con la mitad reciente.
    midpoint = len(readings) // 2

    first_group = readings[:midpoint]
    second_group = readings[midpoint:]

    baseline = median([
        item["value"] for item in first_group
    ])

    current = median([
        item["value"] for item in second_group
    ])

    change = current - baseline
    threshold = TREND_THRESHOLDS[field]

    if change >= threshold:
        status = "rising"
        reason = "Se observa un incremento relevante."

    elif change <= -threshold:
        status = "falling"
        reason = "Se observa una disminución relevante."

    else:
        status = "stable"
        reason = "No se observa una variación relevante."

    return {
        "field": field,
        "status": status,
        "baseline": round(baseline, 2),
        "current": round(current, 2),
        "change": round(change, 2),
        "threshold": threshold,
        "readings_count": len(readings),
        "window_minutes": WINDOW_MINUTES,
        "span_minutes": round(span_minutes, 2),
        "device_id": device_id or (
            next(iter(device_ids)) if device_ids else None
        ),
        "reason": reason
    }


def analyze_all_trends(history, device_id=None, now=None):
    return {
        field: analyze_trend(
            history,
            field,
            device_id=device_id,
            now=now
        )
        for field in TREND_THRESHOLDS
    }
