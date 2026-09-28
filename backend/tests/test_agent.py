from types import SimpleNamespace

from app.agent import investigate
from app.repository import Repository


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(id="r1", output=[SimpleNamespace(type="function_call", name="read_file", arguments='{"path":"bug.py"}', call_id="c1")], output_text="")
        return SimpleNamespace(id="r2", output=[], output_text="bug.py:1 is the cause")


def test_tool_result_returns_to_model(tmp_path):
    (tmp_path / "bug.py").write_text("broken = True", encoding="utf-8")
    fake = FakeResponses()
    events = []
    result = investigate(Repository(str(tmp_path)), "Why is this broken?", lambda *args: events.append(args), client=SimpleNamespace(responses=fake), model="fake")
    assert "bug.py:1" in result
    assert fake.calls[1]["previous_response_id"] == "r1"
    assert fake.calls[1]["input"][0]["call_id"] == "c1"
    assert "broken = True" in fake.calls[1]["input"][0]["output"]
    assert [item[0] for item in events] == ["tool", "result", "report"]
