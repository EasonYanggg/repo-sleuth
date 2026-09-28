from types import SimpleNamespace

import pytest

from app.agent import investigate
from app.repository import Repository


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(id="r1", output=[SimpleNamespace(type="function_call", name="read_file", arguments='{"path":"bug.py"}', call_id="c1")], output_text="")
        return SimpleNamespace(id="r2", output=[], output_text="[bug.py:1] is the cause")


def test_tool_result_returns_to_model(tmp_path):
    (tmp_path / "bug.py").write_text("broken = True", encoding="utf-8")
    fake = FakeResponses()
    events = []
    result = investigate(Repository(str(tmp_path)), "Why is this broken?", lambda *args: events.append(args), client=SimpleNamespace(responses=fake), model="fake")
    assert "[bug.py:1]" in result
    assert fake.calls[1]["previous_response_id"] == "r1"
    assert fake.calls[1]["input"][0]["call_id"] == "c1"
    assert "1 | broken = True" in fake.calls[1]["input"][0]["output"]
    assert [item[0] for item in events] == ["tool", "result", "verification", "report"]


class RepairResponses:
    def __init__(self, repair_succeeds):
        self.calls = []
        self.repair_succeeds = repair_succeeds

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            output = [SimpleNamespace(type="function_call", name="read_file", arguments='{"path":"bug.py"}', call_id="c1")]
            answer = ""
        elif len(self.calls) == 2:
            output, answer = [], "Wrong line [bug.py:99]"
        else:
            output, answer = [], "Correct line [bug.py:1]" if self.repair_succeeds else "Still wrong [bug.py:99]"
        return SimpleNamespace(id=f"r{len(self.calls)}", output=output, output_text=answer)


@pytest.mark.parametrize("repair_succeeds", [True, False])
def test_invalid_citation_is_repaired_or_rejected(tmp_path, repair_succeeds):
    (tmp_path / "bug.py").write_text("broken = True", encoding="utf-8")
    fake = RepairResponses(repair_succeeds)
    events = []
    call = lambda: investigate(Repository(str(tmp_path)), "Why is this broken?", lambda *args: events.append(args), client=SimpleNamespace(responses=fake), model="fake")
    if repair_succeeds:
        assert "[bug.py:1]" in call()
        assert events[-1][0] == "report"
    else:
        with pytest.raises(RuntimeError, match="证据引用校验"):
            call()
    assert len(fake.calls) == 3
    assert any(item[0] == "verification" and "未通过" in item[1] for item in events)
