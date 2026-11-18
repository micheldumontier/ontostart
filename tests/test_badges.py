import io
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from ontostart import cli
from ontostart.badges import BadgeError, badge_files, push_badges
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


def test_missing_steps_and_version_omitted():
    files = badge_files(target(), REPORT, "", {}, False, None)
    kinds = {name.split("-")[2] for name in files}
    assert kinds == {"profile", "reason", "deploy"}


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


def _http_error(code, message=""):
    body = json.dumps({"message": message}).encode() if message else b""
    return urllib.error.HTTPError("https://api.github.com/gists/gid", code, "err", {}, io.BytesIO(body))


def _urlopen(monkeypatch, outcomes):
    """Each call takes the next outcome: an exception to raise, or None for success."""
    calls = []

    def fake(req, *a, **k):
        calls.append(req)
        outcome = outcomes[len(calls) - 1]
        if outcome is not None:
            raise outcome
        return io.BytesIO(b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return calls


def test_push_badges_retries_server_errors_with_backoff(monkeypatch):
    calls = _urlopen(monkeypatch, [_http_error(500), _http_error(502), None])
    waits = []
    push_badges("gid", "tok", {"a.json": {}}, sleep=waits.append)
    assert len(calls) == 3
    assert waits == [2, 4]


def test_push_badges_retries_connection_errors(monkeypatch):
    calls = _urlopen(monkeypatch, [urllib.error.URLError("reset"), TimeoutError(), None])
    push_badges("gid", "tok", {"a.json": {}}, sleep=lambda s: None)
    assert len(calls) == 3


def test_push_badges_gives_up_after_four_attempts(monkeypatch):
    calls = _urlopen(monkeypatch, [_http_error(503)] * 4)
    waits = []
    with pytest.raises(BadgeError, match="HTTP 503 after 4 attempts"):
        push_badges("gid", "tok", {"a.json": {}}, sleep=waits.append)
    assert len(calls) == 4
    assert waits == [2, 4, 8]


def test_push_badges_client_error_is_not_retried(monkeypatch):
    calls = _urlopen(monkeypatch, [_http_error(401, "Bad credentials")])
    with pytest.raises(BadgeError) as e:
        push_badges("gid", "tok", {"a.json": {}}, sleep=lambda s: pytest.fail("retried"))
    assert len(calls) == 1
    assert str(e.value) == "HTTP 401 from the gist API: Bad credentials (check GIST_TOKEN and gist_id)"


def test_badges_command_reports_failure_in_one_line(monkeypatch, tmp_path, capsys):
    def fail(*a, **k):
        raise BadgeError("HTTP 401 from the gist API: Bad credentials (check GIST_TOKEN and gist_id)")

    monkeypatch.setattr(cli, "push_badges", fail)
    monkeypatch.setenv("GIST_TOKEN", "tok")
    assert cli.main(["badges", "--results", str(tmp_path), "--gist", "gid"]) == 1
    out = capsys.readouterr()
    assert out.out == "::warning title=Badges not updated::HTTP 401 from the gist API: Bad credentials (check GIST_TOKEN and gist_id)\n"
    assert "Traceback" not in out.err


@pytest.mark.parametrize("report,message,color", [
    (CheckReport(True, ReasonResult("consistent"), None, None, None), "success", "brightgreen"),
    (CheckReport(False, ReasonResult("consistent"), None, None, None), "failure", "red"),
    (CheckReport(False, ReasonResult("error"), None, None, None, profile_error="Could not load"), "error", "red"),
    (CheckReport(False, ReasonResult("error"), None, None, None, timed_out=["profile"]), "error", "red"),
])
def test_profile_badge_tells_failure_from_error(report, message, color):
    badge = badge_files(target(), report, "", {}, None, None)["ontology-ci-profile-sandbox-testo.json"]
    assert (badge["message"], badge["color"]) == (message, color)
