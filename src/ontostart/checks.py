"""Profile and reasoning checks, and the rules that decide whether they block publishing."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from .targets import Target
from .versioning import PARSE_ERRORS, OntologyIRIError, check_ontology_iri, describe_parse_error

Runner = Callable[[list[str], Path], "tuple[int, str]"]

_UNSAT_RE = re.compile(r"There are ([0-9]+) unsatisfiable classes|There is (1) unsatisfiable class")
_COLORS = {"consistent": "brightgreen", "unsatisfiable": "orange", "inconsistent": "red", "error": "red"}
ROBOT_TIMEOUT = 900  # seconds, per ROBOT invocation


@dataclass(frozen=True)
class ReasonResult:
    kind: Literal["consistent", "unsatisfiable", "inconsistent", "error"]
    unsatisfiable: int = 0

    @property
    def message(self) -> str:
        return f"{self.unsatisfiable} unsatisfiable" if self.kind == "unsatisfiable" else self.kind

    @property
    def color(self) -> str:
        return _COLORS[self.kind]


def classify_reasoning(exit_code: int, output: str) -> ReasonResult:
    if exit_code == 0:
        return ReasonResult("consistent")
    if "ontology is inconsistent" in output:
        return ReasonResult("inconsistent")
    match = _UNSAT_RE.search(output)
    if match:
        return ReasonResult("unsatisfiable", int(match.group(1) or match.group(2)))
    return ReasonResult("error")


@dataclass
class CheckReport:
    profile_ok: bool
    reason: ReasonResult
    expected_unsatisfiable: int | None
    iri_error: str | None
    explanation: Path | None
    parse_error: str | None = None
    logs: dict[str, str] = field(default_factory=dict)  # step -> path of its ROBOT output

    def blocked_reason(self) -> str | None:
        if self.parse_error:
            return self.parse_error
        if self.iri_error:
            return self.iri_error
        if not self.profile_ok:
            return "ontology is not in the OWL DL profile"
        if self.reason.kind == "inconsistent":
            return "ontology is inconsistent"
        if self.reason.kind == "error":
            return "reasoning error"
        if (
            self.expected_unsatisfiable is not None
            and self.reason.unsatisfiable != self.expected_unsatisfiable
        ):
            return (
                f"{self.reason.unsatisfiable} unsatisfiable classes, "
                f"source has {self.expected_unsatisfiable}"
            )
        return None

    def to_json(self) -> dict:
        return {
            "profile_ok": self.profile_ok,
            "reason": {"kind": self.reason.kind, "unsatisfiable": self.reason.unsatisfiable},
            "expected_unsatisfiable": self.expected_unsatisfiable,
            "iri_error": self.iri_error,
            "explanation": None if self.explanation is None else str(self.explanation),
            "parse_error": self.parse_error,
            "logs": dict(self.logs),
        }

    @classmethod
    def from_json(cls, data: dict) -> CheckReport:
        explanation = data["explanation"]
        return cls(
            profile_ok=data["profile_ok"],
            reason=ReasonResult(data["reason"]["kind"], data["reason"]["unsatisfiable"]),
            expected_unsatisfiable=data["expected_unsatisfiable"],
            iri_error=data["iri_error"],
            explanation=None if explanation is None else Path(explanation),
            parse_error=data.get("parse_error"),
            logs=dict(data.get("logs") or {}),
        )


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""


def _subprocess_run(args: list[str], cwd: Path) -> tuple[int, str]:
    """Run a command; a timeout is exit code 124 and a missing program 127, like the shell."""
    try:
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=ROBOT_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        partial = _text(e.output) + _text(e.stderr)
        return 124, f"{partial}\nerror: timed out after {ROBOT_TIMEOUT} s: {' '.join(args)}\n"
    except FileNotFoundError as e:
        return 127, f"error: cannot run {args[0]}: {e}\n"
    return proc.returncode, proc.stdout + proc.stderr


def run_checks(
    target: Target, robot_jar: Path, workdir: Path, run: Runner | None = None
) -> CheckReport:
    workdir = Path(workdir)
    robot = ["java", "-jar", str(robot_jar)]
    catalog = ["--catalog", str(target.catalog)] if target.catalog else []
    file = str(target.file)
    logs: dict[str, str] = {}

    def run_step(step: str, args: list[str]) -> tuple[int, str]:
        """Run one ROBOT command and keep its output in <workdir>/<step>.log."""
        code, out = (run or _subprocess_run)(args, workdir)
        log = workdir / f"{step}.log"
        log.write_text(out)
        logs[step] = str(log)
        return code, out

    iri_error = None
    try:
        check_ontology_iri(target.file, target.base_iri)
    except OntologyIRIError as e:
        iri_error = str(e)
    except PARSE_ERRORS as e:
        rel = target.file.relative_to(target.folder.parents[1]).as_posix()
        parse_error = f"cannot parse {rel}: {describe_parse_error(e)}"
        # ROBOT would fail on the same file; skip it.
        return CheckReport(False, ReasonResult("error"), None, None, None, parse_error=parse_error)

    code, _ = run_step("profile", robot + ["validate-profile"] + catalog + ["--profile", "DL", "--input", file])
    profile_ok = code == 0

    code, out = run_step(
        "reason",
        robot + ["reason"] + catalog
        + ["--reasoner", "HermiT", "--input", file, "--output", str(workdir / "reasoned.owl")],
    )
    reason = classify_reasoning(code, out)

    explanation = None
    mode = {
        "inconsistent": ["--mode", "inconsistency"],
        "unsatisfiable": ["--mode", "unsatisfiability", "--unsatisfiable", "all"],
    }.get(reason.kind)
    if mode:
        path = workdir / "reason.explanation.md"
        run_step(
            "explain",
            robot + ["explain"] + catalog
            + ["--reasoner", "HermiT", "--input", file] + mode + ["--explanation", str(path)],
        )
        explanation = path if path.is_file() else None

    expected = None
    if target.compare_with:
        code, out = run_step(
            "compare",
            robot + ["reason", "--reasoner", "HermiT", "--input", str(target.compare_with),
                     "--output", str(workdir / "reasoned-compare.owl")],
        )
        expected = classify_reasoning(code, out).unsatisfiable

    return CheckReport(profile_ok, reason, expected, iri_error, explanation, logs=logs)
