from backend.analysis.health_engine import analyze_measurements, classify_value


def test_normal_heart_rate():
    result = classify_value("heart_rate", 78)
    assert result["status"] == "normal"


def test_critical_oxygen_saturation():
    result = classify_value("spo2", 85)
    assert result["status"] == "critical"


def test_unknown_missing_measurement():
    result = classify_value("heart_rate", None)
    assert result["status"] == "unknown"


def test_overall_status_uses_highest_severity():
    result = analyze_measurements({
        "heart_rate": 78,
        "spo2": 85,
        "body_temperature": 36.8,
        "glucose": 95,
        "sleep_hours": 7.5,
        "mood_score": 8,
        "systolic_pressure": 118,
        "diastolic_pressure": 76,
    })
    assert result["overall_status"] == "critical"
