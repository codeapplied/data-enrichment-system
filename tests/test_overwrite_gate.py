from dataenrich.crm.overwrite_gate import decide_write


def test_empty_current_value_auto_writes():
    decision = decide_write(None, "new value")
    assert decision.action == "write"


def test_identical_value_auto_writes():
    decision = decide_write("same", "same")
    assert decision.action == "write"


def test_real_conflict_is_skipped_not_overwritten():
    decision = decide_write("existing value", "different value")
    assert decision.action == "skip_conflict"
    assert "existing value" in decision.reason
