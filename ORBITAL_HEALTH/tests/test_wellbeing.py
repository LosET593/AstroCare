from backend.analysis.wellbeing import wellbeing_reply


def test_stress_prompt_returns_grounding_exercise():
    assert "inhala" in wellbeing_reply("Me siento con estrés").lower()


def test_sleep_prompt_returns_rest_guidance():
    assert "descanso" in wellbeing_reply("No puedo dormir").lower()


def test_emergency_prompt_directs_to_human_support():
    reply = wellbeing_reply("No quiero vivir")
    assert "compañero" in reply.lower()
    assert "centro de control" in reply.lower()
