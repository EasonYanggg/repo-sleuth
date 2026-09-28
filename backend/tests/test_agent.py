import json
from types import SimpleNamespace

import pytest

from app.agent import investigate, investigate_report
from app.repository import Repository


def report(citation="[bug.py:1]", quote="broken = True"):
    return json.dumps({
        "hypothesis": "An incorrect value is set.",
        "evidence": [{"citation": citation, "quote": quote, "explanation": "This line sets the value."}],
        "alternatives": [], "confidence": "中", "next_steps": ["Check the caller."], "limitations": [],
    })


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(id="r1", output=[SimpleNamespace(type="function_call", name="read_file", arguments='{"path":"bug.py"}', call_id="c1")], output_text="")
        return SimpleNamespace(id="r2", output=[], output_text=report())


def test_tool_result_returns_to_model(tmp_path):
    (tmp_path / "bug.py").write_text("broken = True", encoding="utf-8")
    fake = FakeResponses()
    events = []
    result = investigate(Repository(str(tmp_path)), "Why is this broken?", lambda *args: events.append(args), client=SimpleNamespace(responses=fake), model="fake")
    assert "[bug.py:1]" in result
    assert fake.calls[1]["previous_response_id"] == "r1"
    assert fake.calls[1]["input"][0]["call_id"] == "c1"
    assert "1 | broken = True" in fake.calls[1]["input"][0]["output"]
    assert [item[0] for item in events if item[0] != "stage"] == ["tool", "result", "verification", "report"]


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
            output, answer = [], report(citation="[bug.py:99]")
        else:
            output, answer = [], report() if self.repair_succeeds else report(citation="[bug.py:99]")
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
        with pytest.raises(RuntimeError, match="证据报告校验"):
            call()
    assert len(fake.calls) == 3
    assert any(item[0] == "verification" and "未通过" in item[1] for item in events)


def test_quote_must_match_observed_source(tmp_path):
    (tmp_path / "bug.py").write_text("broken = True", encoding="utf-8")

    class BadQuote(FakeResponses):
        def create(self, **kwargs):
            response = super().create(**kwargs)
            if not response.output:
                response.output_text = report(quote="broken = False")
            return response

    with pytest.raises(RuntimeError, match="原文与实际代码不符"):
        investigate(Repository(str(tmp_path)), "Why is this broken?", lambda *_: None, client=SimpleNamespace(responses=BadQuote()), model="fake")


def test_graph_resumes_from_sqlite_checkpoint(tmp_path):
    (tmp_path / "bug.py").write_text("broken = True", encoding="utf-8")
    checkpoint = tmp_path / "checkpoints.sqlite"

    class Interrupted(FakeResponses):
        def create(self, **kwargs):
            if self.calls:
                raise ConnectionError("simulated restart")
            return super().create(**kwargs)

    with pytest.raises(ConnectionError):
        investigate_report(Repository(str(tmp_path)), "Why is this broken?", lambda *_: None,
                           client=SimpleNamespace(responses=Interrupted()), model="fake", run_id="run-1", checkpoint_path=checkpoint)

    class Resumed:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(id="r2", output=[], output_text=report())

    resumed = Resumed()
    result = investigate_report(Repository(str(tmp_path)), "Why is this broken?", lambda *_: None,
                                client=SimpleNamespace(responses=resumed), model="fake", run_id="run-1", checkpoint_path=checkpoint, resume=True)
    assert result.evidence[0].citation == "[bug.py:1]"
    assert len(resumed.calls) == 1
    assert resumed.calls[0]["previous_response_id"] == "r1"
    assert resumed.calls[0]["input"][0]["call_id"] == "c1"

    class UnexpectedCall:
        def create(self, **kwargs):
            raise AssertionError("completed graph should not call the model again")

    completed = investigate_report(Repository(str(tmp_path)), "Why is this broken?", lambda *_: None,
                                    client=SimpleNamespace(responses=UnexpectedCall()), model="fake", run_id="run-1", checkpoint_path=checkpoint, resume=True)
    assert completed.hypothesis == result.hypothesis
