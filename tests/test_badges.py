import io
import json
import urllib.request
from pathlib import Path

from ontostart.badges import badge_files, push_badges
from ontostart.checks import CheckReport, ReasonResult
from ontostart.foops import FoopsSummary
from ontostart.targets import Target


def target():
    folder = Path("/r/sandbox/testo")
    return Target("testo", "sandbox/testo", folder, folder / "testo.ttl", "sandbox",
                  "sandbox-testo", "https://w3id.org/x/sandbox/testo/", None, None)


REPORT = CheckReport(True, ReasonResult("unsatisfiable", 2), None, None, None)


def test_badge_files_names_and_colors():
    files = badge_files(target(), REPORT, "0.0.1", {"ontospy": True, "pylode": False}, True,
                        FoopsSummary("75.0% (1.50 in 2 tests)", []))
    assert len(files) == 7
    assert set(files) == {f"ontology-ci-{k}-sandbox-testo.json"
                          for k in "profile reason version ontospy pylode deploy foops".split()}
    reason = files["ontology-ci-reason-sandbox-testo.json"]
    assert reason == {"schemaVersion": 1, "label": "Reasoning", "message": "2 unsatisfiable", "color": "orange"}
    assert files["ontology-ci-pylode-sandbox-testo.json"]["color"] == "red"
    assert files["ontology-ci-foops-sandbox-testo.json"]["label"] == "FOOPS!"


def test_optional_badges_omitted():
    files = badge_files(target(), REPORT, "0.0.1", {"ontospy": True, "pylode": True}, None, None)
    assert len(files) == 5
    assert badge_files(target(), REPORT, "0.0.1", {}, False, None)[
        "ontology-ci-deploy-sandbox-testo.json"]["message"] == "failure"


def test_push_badges_single_request(monkeypatch):
    calls = []

    def fake(req, *a, **k):
        calls.append(req)
        return io.BytesIO(b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    files = {"a.json": {"x": 1}, "b.json": {"y": 2}}
    push_badges("gid", "tok", files)
    assert len(calls) == 1
    req = calls[0]
    assert req.get_method() == "PATCH"
    assert req.full_url == "https://api.github.com/gists/gid"
    assert req.get_header("Authorization") == "Bearer tok"
    body = json.loads(req.data)
    assert body == {"files": {n: {"content": json.dumps(v)} for n, v in files.items()}}
