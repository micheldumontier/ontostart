import json
from pathlib import Path

from ontostart.foops import FoopsSummary, summarize_foops, write_foops_page

DATA = json.loads((Path(__file__).parent / "fixtures" / "foops.json").read_text())


def test_summarize_foops():
    assert summarize_foops(DATA).label == "75.0% (1.50 in 2 tests)"


def test_foops_page_escapes(tmp_path):
    write_foops_page(summarize_foops(DATA), tmp_path, "<T>", "http://x/?a=1&b=2")
    page = (tmp_path / "foops" / "index.html").read_text()
    assert "Has &lt;license&gt;" in page and "&lt;T&gt;" in page and "a=1&amp;b=2" in page
    assert "75.0%" in page and "1/2" in page


def test_foops_page_error(tmp_path):
    write_foops_page(None, tmp_path, "T", "iri", "<boom>")
    page = (tmp_path / "foops" / "index.html").read_text()
    assert "&lt;boom&gt;" in page and "N/A" in page


def test_foops_page_escapes_counts(tmp_path):
    data = {"checks": [{"id": "X", "title": "t", "total_passed_tests": "<b>1</b>",
                        "total_tests_run": "<i>2</i>"}]}
    write_foops_page(FoopsSummary("x", data["checks"]), tmp_path, "T", "iri")
    page = (tmp_path / "foops" / "index.html").read_text()
    assert "<b>1</b>" not in page and "&lt;b&gt;1&lt;/b&gt;/&lt;i&gt;2&lt;/i&gt;" in page
