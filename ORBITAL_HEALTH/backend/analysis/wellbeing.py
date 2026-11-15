"""Asistente guiado de bienestar, sin diagnóstico clínico."""

def wellbeing_reply(message):
    """Respuesta guiada local; no realiza diagnósticos ni sustituye apoyo profesional."""
    normalized = message.casefold()
    if any(term in normalized for term in ("hacerme daño", "suicid", "no quiero vivir", "quitarme la vida")):
        return (
            "Lo que describes requiere apoyo humano inmediato. Contacta ahora mismo "
            "a un compañero de tripulación y al centro de control, y sigue el protocolo "
            "de emergencia de la misión. No tienes que manejarlo a solas."
        )
    if any(term in normalized for term in ("ansiedad", "ansioso", "estres", "estrés", "nervioso", "agobiado", "presion")):
        return (
            "Hagamos una pausa breve. Si es seguro hacerlo, inhala suavemente durante "
            "4 segundos, mantén 2 y exhala durante 6. Repite tres veces. Después, "
            "identifica qué situación concreta está generando más tensión."
        )
    if any(term in normalized for term in ("dormir", "sueño", "insomnio", "cansancio", "fatiga")):
        return (
            "El descanso es importante para el rendimiento de la tripulación. Registra "
            "cuánto has dormido y cómo te sientes. Si la fatiga afecta tus tareas, "
            "comunícalo al equipo médico y al centro de control."
        )
    if any(term in normalized for term in ("solo", "soledad", "aislado", "triste", "extraño", "familia")):
        return (
            "El aislamiento puede pesar durante una misión. Considera hablar con un "
            "compañero de confianza y mantener una rutina breve de contacto social. "
            "¿Qué sería lo más útil para ti en este momento?"
        )
    return (
        "Te escucho. Describe con tus propias palabras cómo te encuentras y qué "
        "necesitarías ahora. Podemos ordenar la situación paso a paso. Este módulo "
        "ofrece apoyo guiado, no evaluación ni diagnóstico psicológico."
    )

