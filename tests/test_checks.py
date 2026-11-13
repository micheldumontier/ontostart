from pathlib import Path

import pytest

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
               iri_error="bad", explanation=Path("w/reason.explanation.md"))
    assert CheckReport.from_json(r.to_json()) == r
    r = report()
    assert CheckReport.from_json(r.to_json()) == r


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
            return 0, "ok"
        if sub == "reason":
            n = 3 if str(file) in args else 2
            return 1, f"There are {n} unsatisfiable classes"
        (work / "reason.explanation.md").write_text("why")
        return 0, ""

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
    assert rep == CheckReport(True, ReasonResult("unsatisfiable", 3), 2, None, work / "reason.explanation.md")
    assert rep.blocked_reason() == "3 unsatisfiable classes, source has 2"
