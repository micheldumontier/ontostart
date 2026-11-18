import shutil
import subprocess
from pathlib import Path

import pytest

from ontostart import checks
from ontostart.checks import CheckReport, ReasonResult, classify_reasoning, run_checks
from ontostart.targets import Target

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("fixture,code,kind,n", [
    ("consistent", 0, "consistent", 0),
    ("unsat1", 1, "unsatisfiable", 1),
    ("unsat2", 1, "unsatisfiable", 2),
    ("inconsistent", 1, "inconsistent", 0),
    ("error", 1, "error", 0),
])
def test_classify_reasoning(fixture, code, kind, n):
    text = (FIXTURES / "robot" / f"{fixture}.txt").read_text()
    assert classify_reasoning(code, text) == ReasonResult(kind, n)


def test_result_message_and_color():
    assert (ReasonResult("consistent").message, ReasonResult("consistent").color) == ("consistent", "brightgreen")
    assert (ReasonResult("unsatisfiable", 2).message, ReasonResult("unsatisfiable", 2).color) == ("2 unsatisfiable", "orange")
    assert (ReasonResult("inconsistent").message, ReasonResult("inconsistent").color) == ("inconsistent", "red")
    assert (ReasonResult("error").message, ReasonResult("error").color) == ("error", "red")


def report(**kw):
    base = dict(profile_ok=True, reason=ReasonResult("consistent"), expected_unsatisfiable=None,
                iri_error=None, explanation=None)
    base.update(kw)
    return CheckReport(**base)


def test_blocked_reasons():
    assert report().blocked_reason() is None
    assert "OWL DL profile" in report(profile_ok=False).blocked_reason()
    assert "inconsistent" in report(reason=ReasonResult("inconsistent")).blocked_reason()
    assert "reasoning error" in report(reason=ReasonResult("error")).blocked_reason()


def test_unsatisfiable_alone_not_blocked():
    assert report(reason=ReasonResult("unsatisfiable", 2)).blocked_reason() is None


def test_compare_mismatch_blocks():
    r = report(reason=ReasonResult("unsatisfiable", 3), expected_unsatisfiable=2)
    assert r.blocked_reason() == "3 unsatisfiable classes, source has 2"


def test_wrong_iri_blocks():
    assert "expected owl:Ontology <x>" in report(iri_error="expected owl:Ontology <x>").blocked_reason()


def test_report_json_roundtrip():
    r = report(reason=ReasonResult("unsatisfiable", 2), expected_unsatisfiable=2,
               iri_error="bad", explanation=Path("w/reason.explanation.md"),
               parse_error="cannot parse x.ttl: line 3: oops",
               logs={"profile": "w/profile.log", "reason": "w/reason.log"})
    assert CheckReport.from_json(r.to_json()) == r
    r = report()
    assert CheckReport.from_json(r.to_json()) == r


def test_report_from_json_without_new_fields():
    data = report().to_json()
    del data["logs"], data["parse_error"]
    r = CheckReport.from_json(data)
    assert r.logs == {} and r.parse_error is None


def test_parse_error_blocks_first():
    r = report(parse_error="cannot parse x.ttl: line 3: oops", iri_error="bad", profile_ok=False,
               reason=ReasonResult("error"))
    assert r.blocked_reason() == "cannot parse x.ttl: line 3: oops"


def test_run_checks_command_lines(tmp_path):
    folder = tmp_path / "ontologies" / "demo"
    folder.mkdir(parents=True)
    file = folder / "demo.ttl"
    file.write_text(
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "<https://w3id.org/x/demo/> a owl:Ontology .\n"
    )
    target = Target("demo", "demo", folder, file, "stable", "demo", "https://w3id.org/x/demo/",
                    folder / "catalog-v001.xml", folder / "source.ttl")
    work = tmp_path / "work"
    work.mkdir()
    calls = []

    def fake(args, cwd):
        calls.append((args, cwd))
        sub = args[3]
        if sub == "validate-profile":
            return 0, "profile ok"
        if sub == "reason":
            n = 3 if str(file) in args else 2
            return 1, f"There are {n} unsatisfiable classes"
        (work / "reason.explanation.md").write_text("why")
        return 0, "explained"

    rep = run_checks(target, Path("robot.jar"), work, run=fake)
    j = ["java", "-jar", "robot.jar"]
    cat = ["--catalog", str(folder / "catalog-v001.xml")]
    f = str(file)
    assert [c[0] for c in calls] == [
        j + ["validate-profile"] + cat + ["--profile", "DL", "--input", f],
        j + ["reason"] + cat + ["--reasoner", "HermiT", "--input", f, "--output", str(work / "reasoned.owl")],
        j + ["explain"] + cat + ["--reasoner", "HermiT", "--input", f, "--mode", "unsatisfiability",
                                 "--unsatisfiable", "all", "--explanation", str(work / "reason.explanation.md")],
        j + ["reason", "--reasoner", "HermiT", "--input", str(folder / "source.ttl"),
             "--output", str(work / "reasoned-compare.owl")],
    ]
    logs = {step: str(work / f"{step}.log") for step in ("profile", "reason", "explain", "compare")}
    assert rep == CheckReport(True, ReasonResult("unsatisfiable", 3), 2, None, work / "reason.explanation.md",
                              logs=logs)
    assert rep.blocked_reason() == "3 unsatisfiable classes, source has 2"
    assert (work / "profile.log").read_text() == "profile ok"
    assert (work / "reason.log").read_text() == "There are 3 unsatisfiable classes"
    assert (work / "explain.log").read_text() == "explained"
    assert (work / "compare.log").read_text() == "There are 2 unsatisfiable classes"


def test_run_checks_consistent_writes_only_run_logs(tmp_path):
    folder = tmp_path / "ontologies" / "demo"
    folder.mkdir(parents=True)
    file = folder / "demo.ttl"
    file.write_text(
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "<https://w3id.org/x/demo/> a owl:Ontology .\n"
    )
    target = Target("demo", "demo", folder, file, "stable", "demo", "https://w3id.org/x/demo/", None, None)
    rep = run_checks(target, Path("robot.jar"), tmp_path, run=lambda args, cwd: (0, args[3]))
    assert sorted(rep.logs) == ["profile", "reason"]
    assert (tmp_path / "reason.log").read_text() == "reason"
    assert not (tmp_path / "explain.log").exists()


def _parse_error_target(tmp_path):
    folder = tmp_path / "ontologies" / "demo"
    folder.mkdir(parents=True)
    file = folder / "demo.ttl"
    shutil.copy(FIXTURES / "syntax-error.ttl", file)
    return Target("demo", "demo", folder, file, "stable", "demo", "https://w3id.org/x/demo/", None, None)


def test_run_checks_parse_error(tmp_path):
    target = _parse_error_target(tmp_path)
    calls = []
    work = tmp_path / "work"
    work.mkdir()
    rep = run_checks(target, Path("robot.jar"), work, run=lambda args, cwd: calls.append(args) or (0, ""))
    assert calls == []
    assert rep.profile_ok is False and rep.reason.kind == "error"
    assert rep.blocked_reason().startswith("cannot parse ontologies/demo/demo.ttl: line 4")
    assert CheckReport.from_json(rep.to_json()) == rep


def test_check_cli_parse_error_writes_report(tmp_path, monkeypatch):
    import json

    from ontostart import cli

    target = _parse_error_target(tmp_path)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "check" / "report.json"
    out.parent.mkdir()
    code = cli.main(["check", "--target-json", json.dumps(target.to_json()),
                     "--robot", "robot.jar", "--out", str(out)])
    assert code == 0
    rep = CheckReport.from_json(json.loads(out.read_text()))
    assert rep.blocked_reason().startswith("cannot parse")


def test_subprocess_run_passes_timeout(monkeypatch, tmp_path):
    seen = {}

    def fake_run(args, **kw):
        seen.update(kw)
        return subprocess.CompletedProcess(args, 3, "out ", "err")

    monkeypatch.setattr(checks.subprocess, "run", fake_run)
    assert checks._subprocess_run(["java"], tmp_path) == (3, "out err")
    assert seen["timeout"] == 900 and seen["cwd"] == tmp_path


def test_subprocess_run_timeout(monkeypatch, tmp_path):
    def fake_run(args, **kw):
        raise subprocess.TimeoutExpired(args, kw["timeout"], output="partial")

    monkeypatch.setattr(checks.subprocess, "run", fake_run)
    code, out = checks._subprocess_run(["java", "-jar", "robot.jar", "reason"], tmp_path)
    assert code == 124 and "timed out after 900 s" in out and "partial" in out
    assert classify_reasoning(code, out) == ReasonResult("error")


def test_subprocess_run_missing_program(tmp_path):
    code, out = checks._subprocess_run(["ontostart-no-such-program-xyz", "-jar"], tmp_path)
    assert code == 127 and "ontostart-no-such-program-xyz" in out
    assert classify_reasoning(code, out) == ReasonResult("error")


def test_compare_fewer_also_blocks():
    r = report(reason=ReasonResult("unsatisfiable", 1), expected_unsatisfiable=2)
    assert r.blocked_reason() == "1 unsatisfiable classes, source has 2"


def test_check_cli_writes_report(tmp_path, monkeypatch, capsys):
    import json

    from ontostart import cli

    folder = tmp_path / "ontologies" / "demo"
    folder.mkdir(parents=True)
    (folder / "demo.ttl").write_text("")
    target = Target("demo", "demo", folder, folder / "demo.ttl", "stable", "demo",
                    "https://w3id.org/x/demo/", None, None)
    expected = report(reason=ReasonResult("unsatisfiable", 2), expected_unsatisfiable=2,
                      explanation=tmp_path / "reason.explanation.md")
    seen = {}

    def fake_run_checks(t, robot, workdir):
        seen.update(target=t, robot=robot, workdir=workdir)
        return expected

    monkeypatch.setattr(cli, "run_checks", fake_run_checks)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "report.json"
    code = cli.main(["check", "--target-json", json.dumps(target.to_json()),
                     "--robot", "robot.jar", "--out", str(out)])
    assert code == 0
    assert seen["target"].name == "demo" and seen["robot"] == Path("robot.jar")
    assert CheckReport.from_json(json.loads(out.read_text())) == expected


def test_blocked_cli(tmp_path, capsys):
    import json

    from ontostart.cli import main

    blocked = tmp_path / "blocked.json"
    blocked.write_text(json.dumps(report(profile_ok=False).to_json()))
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps(report().to_json()))
    assert main(["blocked", "--report", str(blocked)]) == 0
    assert capsys.readouterr().out == "ontology is not in the OWL DL profile\n"
    assert main(["blocked", "--report", str(ok)]) == 0
    assert capsys.readouterr().out == "\n"


def _demo_target(tmp_path):
    folder = tmp_path / "ontologies" / "demo"
    folder.mkdir(parents=True)
    file = folder / "demo.ttl"
    file.write_text(
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "<https://w3id.org/x/demo/> a owl:Ontology .\n"
    )
    return Target("demo", "demo", folder, file, "stable", "demo", "https://w3id.org/x/demo/", None, None)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_run_checks_shares_one_time_budget(tmp_path, monkeypatch):
    clock = Clock()
    timeouts = []

    def fake_subprocess_run(args, cwd, timeout):
        timeouts.append(timeout)
        clock.now += 300
        return 0, "ok"

    monkeypatch.setattr(checks, "_subprocess_run", fake_subprocess_run)
    rep = run_checks(_demo_target(tmp_path), Path("robot.jar"), tmp_path, clock=clock)
    assert timeouts == [900, 600]
    assert rep.timed_out == [] and rep.blocked_reason() is None


def test_run_checks_profile_timeout_skips_the_rest(tmp_path):
    clock = Clock()
    calls = []

    def fake(args, cwd):
        calls.append(args[3])
        clock.now += 900
        return 124, "error: timed out after 900 s\n"

    rep = run_checks(_demo_target(tmp_path), Path("robot.jar"), tmp_path, run=fake, clock=clock)
    assert calls == ["validate-profile"]
    assert rep.timed_out == ["profile", "reason"]
    assert "not run" in (tmp_path / "reason.log").read_text()
    assert rep.blocked_reason() == (
        "ROBOT did not finish in time (profile, reason); "
        "the checks of one ontology may take 15 minutes in total"
    )
    assert CheckReport.from_json(rep.to_json()) == rep


def test_run_checks_explain_timeout_does_not_block(tmp_path):
    def fake(args, cwd):
        if args[3] == "reason":
            return 1, "There are 2 unsatisfiable classes"
        if args[3] == "explain":
            return 124, "error: timed out\n"
        return 0, ""

    rep = run_checks(_demo_target(tmp_path), Path("robot.jar"), tmp_path, run=fake)
    assert rep.timed_out == ["explain"]
    assert rep.reason == ReasonResult("unsatisfiable", 2)
    assert rep.blocked_reason() is None


def test_report_without_timed_out_field_still_loads():
    data = report().to_json()
    del data["timed_out"]
    assert CheckReport.from_json(data).timed_out == []


# validate-profile output of ROBOT 1.9.8, captured from real runs.
PROFILE_VIOLATION = """OWL 2 DL Profile Report: Ontology and imports closure NOT in profile. The following violations are present:
Cannot pun between properties: <https://w3id.org/x/demo/p> [Declaration(ObjectProperty(<https://w3id.org/x/demo/p>))]

PROFILE VIOLATION ERROR https://w3id.org/x/demo/ violates profile DL
For details see: http://robot.obolibrary.org/validate-profile#profile-violation-error
Use the -vvv option to show the stack trace.
Use the --help option to see usage information.
"""
UNLOADABLE_IMPORT = """org.semanticweb.owlapi.model.UnloadableImportException: Could not load imported ontology: <https://example.invalid/missing.owl> Cause: example.invalid
Use the -vvv option to show the stack trace.
Use the --help option to see usage information.
"""
MISSING_FILE = """org.semanticweb.owlapi.io.OWLOntologyInputSourceException: java.io.FileNotFoundException: nosuchfile.ttl (No such file or directory)
Use the -vvv option to show the stack trace.
Use the --help option to see usage information.
"""


@pytest.mark.parametrize("output,cause", [
    (UNLOADABLE_IMPORT, "Could not load imported ontology: <https://example.invalid/missing.owl> Cause: example.invalid"),
    (MISSING_FILE, "nosuchfile.ttl (No such file or directory)"),
    ("error: cannot run java: [Errno 2] No such file or directory: 'java'\n",
     "cannot run java: [Errno 2] No such file or directory: 'java'"),
    ("2026-11-18 15:03:31,753 ERROR org.obolibrary.robot.IOHelper - Java heap space\n", "Java heap space"),
    ("", "ROBOT stopped without a message"),
])
def test_robot_error_cause(output, cause):
    assert checks.robot_error_cause(output) == cause


def _profile_run(code, output):
    def fake(args, cwd):
        if args[3] == "validate-profile":
            return code, output
        return 0, ""
    return fake


def test_profile_violation_is_reported_as_such(tmp_path):
    rep = run_checks(_demo_target(tmp_path), Path("robot.jar"), tmp_path, run=_profile_run(1, PROFILE_VIOLATION))
    assert rep.profile_ok is False and rep.profile_error is None
    assert rep.blocked_reason() == "ontology is not in the OWL DL profile"


def test_robot_failure_is_not_reported_as_a_profile_violation(tmp_path):
    rep = run_checks(_demo_target(tmp_path), Path("robot.jar"), tmp_path, run=_profile_run(1, UNLOADABLE_IMPORT))
    assert rep.profile_ok is False
    assert rep.blocked_reason() == (
        "profile check failed: Could not load imported ontology: "
        "<https://example.invalid/missing.owl> Cause: example.invalid"
    )
    assert CheckReport.from_json(rep.to_json()) == rep


def test_profile_timeout_sets_no_profile_error(tmp_path):
    rep = run_checks(_demo_target(tmp_path), Path("robot.jar"), tmp_path, run=_profile_run(124, "timed out"))
    assert rep.profile_error is None and rep.timed_out == ["profile"]


def test_report_without_profile_error_field_still_loads():
    data = report().to_json()
    del data["profile_error"]
    assert CheckReport.from_json(data).profile_error is None
