
from datetime import datetime, timezone
from math import isfinite

import json
from backend.analysis.health_engine import analyze_measurements
from backend.analysis.health_trend import analyze_all_trends

from flask import Flask, request, jsonify
from flask_socketio import SocketIO

from flask import Flask, request, jsonify, render_template

from backend.database.db import (
    get_connection,
    get_device_history,
    initialize_database
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "orbital-health-development-key"

socketio = SocketIO(app, cors_allowed_origins=[])
app.template_folder = "../frontend/templates"
app.static_folder = "../frontend/static"
app.static_url_path = "/static"

# Campos permitidos y rangos básicos de validación.
LIMITS = {
    "heart_rate": (20, 250),
    "spo2": (50, 100),
    "body_temperature": (25, 45),
    "systolic_pressure": (40, 250),
    "diastolic_pressure": (20, 150),
    "glucose": (20, 600),
    "sleep_hours": (0, 24),
    "mood_score": (1, 10),
}


def validate_telemetry(data):
    if not isinstance(data, dict):
        return None, "El cuerpo debe ser un objeto JSON"

    device_id = data.get("device_id")

    if not isinstance(device_id, str) or not device_id.strip():
        return None, "device_id es obligatorio"

    clean = {
        "device_id": device_id.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    found_measurement = False

    for field, (minimum, maximum) in LIMITS.items():
        value = data.get(field)

        if value is None:
            clean[field] = None
            continue

        if isinstance(value, bool):
            return None, f"{field} debe ser numérico"

        try:
            value = float(value)
        except (ValueError, TypeError):
            return None, f"{field} debe ser numérico"

        if not isfinite(value):
            return None, f"{field} no es un número válido"

        if not minimum <= value <= maximum:
            return None, (
                f"{field} fuera del rango de validación "
                f"({minimum}-{maximum})"
            )

        clean[field] = value
        found_measurement = True

    if not found_measurement:
        return None, "No se recibió ninguna medición"

    return clean, None

def serialize_measurement(row):
    item = dict(row)

    raw_analysis = item.get("analysis_json")

    if raw_analysis:
        try:
            item["analysis"] = json.loads(raw_analysis)
        except (ValueError, TypeError):
            item["analysis"] = None
    else:
        item["analysis"] = None

    return item

@app.get("/")
def home():
    return render_template("dashboard.html")

@app.get("/api/dashboard")
def dashboard_data():
    with get_connection() as connection:
        latest = connection.execute("""
            SELECT *
            FROM telemetry
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        rows = connection.execute("""
            SELECT *
            FROM telemetry
            ORDER BY id DESC
            LIMIT 60
        """).fetchall()

        return jsonify({
            "latest": serialize_measurement(latest) if latest else None,
            "history": [
                serialize_measurement(row) for row in reversed(rows)
            ]
        })

@app.get("/api/status")
def status():
    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM telemetry"
        ).fetchone()[0]

        latest = connection.execute("""
            SELECT device_id, timestamp
            FROM telemetry
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

    return jsonify({
        "server": "online",
        "total_measurements": total,
        "last_measurement": dict(latest) if latest else None
    })



@app.post("/api/telemetry")
def receive_telemetry():
    data, error = validate_telemetry(
        request.get_json(silent=True)
    )

    if error:
        return jsonify({
            "ok": False,
            "error": error
        }), 400

    # 1. Analizar las mediciones.
    analysis = analyze_measurements(data)

    # 2. Preparar el análisis para SQLite.
    analysis_json = json.dumps(
        analysis,
        ensure_ascii=False
    )

    overall_status = analysis["overall_status"]

    # 3. Guardar datos y análisis.
    fields = [
        "device_id",
        "timestamp",
        *LIMITS.keys(),
        "overall_status",
        "analysis_json"
    ]

    values = [
        data[field] for field in ["device_id", "timestamp", *LIMITS.keys()]
    ]

    values.extend([overall_status, analysis_json])

    placeholders = ", ".join(["?"] * len(fields))
    columns = ", ".join(fields)

    with get_connection() as connection:
        cursor = connection.execute(
            f"INSERT INTO telemetry ({columns}) VALUES ({placeholders})",
            values
        )
        measurement_id = cursor.lastrowid
        connection.commit()

    # 4. Preparar respuesta y actualización en tiempo real.
    result = {
        "id": measurement_id,
        **data,
        "analysis": analysis
    }

    socketio.emit("telemetry_update", result)

    return jsonify({
        "ok": True,
        "message": "Medición almacenada y analizada",
        "data": result
    }), 201


@app.get("/api/history")
def history():
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"error": "limit debe ser un entero"}), 400

    limit = max(1, min(limit, 500))

    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()

    return jsonify({
        "count": len(rows),
        "measurements": [serialize_measurement(row) for row in rows]
    })


@app.get("/api/trends")
def trends():
    # 1. Identificar el dispositivo.
    device_id = request.args.get("device_id", "").strip()

    if not device_id:
        return jsonify({
            "ok": False,
            "error": "El parámetro device_id es obligatorio."
        }), 400

    # 2. Validar el límite de consulta.
    try:
        limit = int(request.args.get("limit", 500))
    except ValueError:
        return jsonify({
            "ok": False,
            "error": "limit debe ser un entero."
        }), 400

    limit = max(1, min(limit, 1000))

    # 3. Recuperar el historial del dispositivo.
    history = get_device_history(
        device_id=device_id,
        limit=limit
    )

    # 4. Analizar las tendencias en Python.
    trends_result = analyze_all_trends(
        history,
        device_id=device_id
    )

    # 5. Responder con resultados estructurados.
    return jsonify({
        "ok": True,
        "device_id": device_id,
        "measurements_analyzed": len(history),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trends": trends_result
    }), 200


if __name__ == "__main__":
    initialize_database()

    print("ORBITAL HEALTH: servidor iniciado")
    print("API disponible en http://127.0.0.1:5000")

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )
