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
