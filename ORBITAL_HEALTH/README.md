# ORBITAL HEALTH

Prototipo experimental de monitorización biométrica y apoyo al bienestar de tripulaciones en misiones espaciales.

## Estado del prototipo

- **IN-SHIP:** dashboard biométrico, indicadores, alertas, gráficas e historial.
- **EVA:** entorno de simulación con indicadores prioritarios y alertas simplificadas.
- **Bienestar:** check-in de ánimo/estrés y asistente conversacional guiado con respuestas locales basadas en reglas.
- **Persistencia:** SQLite local para telemetría y registros de bienestar.
- **Tiempo real:** Flask-SocketIO cuando la biblioteca cliente está disponible; el dashboard conserva actualización periódica como alternativa.
- **Voz:** lectura de respuestas mediante las voces disponibles en el navegador/dispositivo. La entrada de voz local offline todavía requiere integrar un motor y un modelo local.

> **Aviso:** ORBITAL HEALTH es un prototipo educativo/experimental. Los umbrales son ilustrativos, no están validados clínicamente y no deben usarse para diagnóstico, tratamiento ni decisiones médicas reales. EVA utiliza telemetría simulada y no se conecta a un traje espacial.

## Requisitos

- Python 3.11 o superior (desarrollado y probado inicialmente con Python 3.13).
- Navegador moderno.
- Conexión a Internet para cargar Chart.js y Socket.IO desde CDN en esta versión. El empaquetado de dependencias locales forma parte de la preparación offline.

## Instalación en Windows (PowerShell)

```powershell
cd ruta\a\ORBITAL_HEALTH
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m backend.app
```

Abrir en el navegador:

```text
http://127.0.0.1:5000/
```

La base de datos se crea automáticamente en `data/orbital_health.db` al iniciar el servidor. La base de datos local está excluida de Git para evitar publicar telemetría o registros personales.

## API principal

| Método | Ruta | Función |
|---|---|---|
| GET | `/api/status` | Estado del servidor y total de mediciones |
| GET | `/api/dashboard` | Última medición e historial reciente |
| POST | `/api/telemetry` | Validar, analizar y guardar telemetría |
| GET | `/api/history` | Consultar historial |
| GET | `/api/trends?device_id=...` | Analizar tendencias por dispositivo |
| POST | `/api/wellbeing/chat` | Conversación guiada local |
| GET | `/api/wellbeing/history` | Historial de conversación |
| POST | `/api/wellbeing/checkin` | Guardar check-in de ánimo y estrés |
| GET | `/api/wellbeing/checkins` | Consultar check-ins |

### Ejemplo de telemetría

```json
{
  "device_id": "SIM-EVA-001",
  "heart_rate": 78,
  "spo2": 98,
  "body_temperature": 36.8,
  "systolic_pressure": 118,
  "diastolic_pressure": 76,
  "glucose": 95,
  "sleep_hours": 7.5,
  "mood_score": 8
}
```

Enviar el JSON a `POST /api/telemetry` con `Content-Type: application/json`.

## Estructura

```text
backend/
  analysis/       # motor biométrico y tendencias
  database/       # SQLite
  app.py          # aplicación Flask y API
frontend/
  templates/      # interfaz
  static/
    css/
    js/
data/             # base de datos local (ignorada por Git)
tests/            # pruebas automatizadas
```

## Privacidad y seguridad

- No subir `data/orbital_health.db`, archivos `.env`, credenciales ni datos reales de tripulación.
- Usar únicamente datos sintéticos en demostraciones públicas.
- El servidor de desarrollo no está endurecido para producción ni para redes públicas.
- Antes de conectar sensores reales o utilizar información personal, implementar autenticación, autorización, cifrado, auditoría y validación clínica/ciberseguridad.

## Próximas etapas

1. Completar y probar los entornos IN-SHIP y EVA.
2. Integrar voz bidireccional completamente local.
3. Empaquetar Chart.js y Socket.IO para operación sin Internet.
4. Ejecutar pruebas integrales.
5. Preparar el empaquetado Android (APK) reutilizando el núcleo del sistema.
