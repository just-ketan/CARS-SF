"""Context Engine inference and timelines."""

from datetime import datetime

from context.engine import ContextInferenceEngine


def test_calendar_rules_and_precedence():
    engine = ContextInferenceEngine()
    assert engine.infer(datetime(2026, 6, 15, 10))[0] == "school"        # Monday 10:00
    assert engine.infer(datetime(2026, 6, 20, 10))[0] == "normal"        # Saturday
    assert engine.infer(datetime(2026, 10, 17, 10))[0] == "harvest"      # Saturday in harvest
    assert engine.infer(datetime(2026, 10, 19, 10))[0] == "school"       # school beats harvest
    engine.raise_alert("flood")
    assert engine.infer(datetime(2026, 10, 19, 10))[0] == "disaster"
    engine.raise_alert("medical_emergency")
    assert engine.infer(datetime(2026, 10, 19, 10))[0] == "medical_emergency"
    engine.set_admin_override("normal")
    assert engine.infer(datetime(2026, 10, 19, 10)) == ("normal", "admin override")


def test_timeline_events_drive_context_changes():
    engine = ContextInferenceEngine(timeline="rural_day")
    contexts = [engine.step(t)["context"] for t in range(30)]
    assert contexts[0] == "harvest"              # 07:00 in October, before school
    assert "school" in contexts[6:12]
    assert contexts[12] == "disaster" and contexts[23] == "disaster"
    assert contexts[24] != "disaster"
    changes = [h for h in engine.get_history() if h["changed"]]
    assert len(changes) >= 3


def test_fixed_context_still_yields_to_alerts():
    engine = ContextInferenceEngine(fixed_context="harvest")
    assert engine.step(0)["context"] == "harvest"
    engine.raise_alert("fiber_cut")
    assert engine.step(1)["context"] == "fiber_cut"
