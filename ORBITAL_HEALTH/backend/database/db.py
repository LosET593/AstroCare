
import sqlite3
from pathlib import Path
from contextlib import contextmanager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "orbital_health.db"


@contextmanager
def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
    finally:
        connection.close()


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                heart_rate REAL,
                spo2 REAL,
                body_temperature REAL,
                systolic_pressure REAL,
                diastolic_pressure REAL,
                glucose REAL,
                sleep_hours REAL,
                mood_score REAL
            )
        """)
        # Agregar columnas de análisis si la base de datos ya existía.
        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(telemetry)"
            ).fetchall()
        }
        if "overall_status" not in existing_columns:
            connection.execute(
                "ALTER TABLE telemetry ADD COLUMN overall_status TEXT"
            )
        if "analysis_json" not in existing_columns:
            connection.execute(
                "ALTER TABLE telemetry ADD COLUMN analysis_json TEXT"
            )
            connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_device_timestamp
            ON telemetry (device_id, timestamp)
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS wellbeing_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS wellbeing_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                mood_score INTEGER NOT NULL CHECK(mood_score BETWEEN 1 AND 10),
                stress_level INTEGER NOT NULL CHECK(stress_level BETWEEN 1 AND 10),
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_device_timestamp
            ON telemetry (device_id, timestamp)
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_wellbeing_messages_created
            ON wellbeing_messages (created_at)
        """)
        connection.commit()

def get_device_history(device_id, limit=500):
    """
    Recupera el historial más reciente de un dispositivo.
    Devuelve las mediciones en orden cronológico.
    """
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                device_id,
                timestamp,
                heart_rate,
                spo2,
                body_temperature,
                glucose
            FROM telemetry
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (device_id, limit)).fetchall()

    return [
        dict(row)
        for row in reversed(rows)
    ]