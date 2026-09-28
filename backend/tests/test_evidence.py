from app.evidence import EvidenceLedger


def test_citations_must_be_observed():
    ledger = EvidenceLedger()
    ledger.record("read_file", {"path": "src/app.py"}, "1 | first\n2 | second")
    assert ledger.validate("because [src/app.py:2]") == []
    assert ledger.validate("because [src/app.py:3]")
    assert ledger.validate("no citation")


def test_search_results_add_citable_lines():
    ledger = EvidenceLedger()
    ledger.record("search_code", {"query": "bug"}, "./app.py:7:bug here")
    assert ledger.validate("see [app.py:7]") == []


def test_quote_must_match_source_and_snapshot_survives():
    ledger = EvidenceLedger()
    ledger.record("read_file", {"path": "app.py"}, "7 | return value + 1")
    restored = EvidenceLedger.from_snapshot(ledger.snapshot())
    assert restored.validate_quote("[app.py:7]", "value + 1") is None
    assert "不符" in restored.validate_quote("[app.py:7]", "value - 1")
