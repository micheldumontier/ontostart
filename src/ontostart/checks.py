"""Profile and reasoning checks, and the rules that decide whether they block publishing."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from .targets import Target
from .versioning import PARSE_ERRORS, OntologyIRIError, check_ontology_iri, describe_parse_error

Runner = Callable[[list[str], Path], "tuple[int, str]"]

_UNSAT_RE = re.compile(r"There are ([0-9]+) unsatisfiable classes|There is (1) unsatisfiable class")
_COLORS = {"consistent": "brightgreen", "unsatisfiable": "orange", "inconsistent": "red", "error": "red"}
# Seconds for all ROBOT runs of one ontology together, so that the checks end well
# inside the build job's 30-minute limit and a timeout is reported as one.
CHECK_BUDGET = 900
BLOCKING_STEPS = ("profile", "reason", "compare")  # a timeout of "explain" does not block
PROFILE_VIOLATION = "PROFILE VIOLATION ERROR"  # what validate-profile prints for a real violation
_BOILERPLATE = ("Use the -vvv option", "Use the --help option", "For details see:")
_LOG_PREFIX = re.compile(r"^\d{4}-\d\d-\d\d [\d:,]+ [A-Z]+ \S+ - ")
_EXCEPTION_PREFIX = re.compile(r"^(?:[a-z_]\w*\.)+[A-Z]\w*(?:Exception|Error): ")


def robot_error_cause(output: str) -> str:
    """The message of a failed ROBOT run: its last line, without Java class names or help text."""
    lines = [
        line.strip() for line in output.splitlines()
        if line.strip() and not line.strip().startswith(_BOILERPLATE)
    ]
    if not lines:
        return "ROBOT stopped without a message"
    cause = _LOG_PREFIX.sub("", lines[-1])
    while _EXCEPTION_PREFIX.match(cause):
        cause = _EXCEPTION_PREFIX.sub("", cause, count=1)
    cause = cause.removeprefix("error: ")
    return cause if len(cause) <= 300 else cause[:299] + "…"


@dataclass(frozen=True)
class ReasonResult:
    kind: Literal["consistent", "unsatisfiable", "inconsistent", "error"]
    unsatisfiable: int = 0
    cause: str = field(default="", compare=False)  # ROBOT's message, for "error"

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
    return ReasonResult("error", cause=robot_error_cause(output))


@dataclass
class CheckReport:
    profile_ok: bool
    reason: ReasonResult
    expected_unsatisfiable: int | None
    iri_error: str | None
    explanation: Path | None
    parse_error: str | None = None
    logs: dict[str, str] = field(default_factory=dict)  # step -> path of its ROBOT output
    timed_out: list[str] = field(default_factory=list)  # steps that ran out of time or were not run
    profile_error: str | None = None  # why validate-profile failed, when it did not report a violation
    compare_error: str | None = None  # why reasoning on compare_unsatisfiable_with failed

    def blocked_reason(self) -> str | None:
        if self.parse_error:
            return self.parse_error
        if self.iri_error:
            return self.iri_error
        late = [step for step in self.timed_out if step in BLOCKING_STEPS]
        if late:
            return (
                f"ROBOT did not finish in time ({', '.join(late)}); "
                f"the checks of one ontology may take {CHECK_BUDGET // 60} minutes in total"
            )
        if self.profile_error:
            return f"profile check failed: {self.profile_error}"
        if not self.profile_ok:
            return "ontology is not in the OWL DL profile"
        if self.reason.kind == "inconsistent":
            return "ontology is inconsistent"
        if self.reason.kind == "error":
            return f"reasoning failed: {self.reason.cause}" if self.reason.cause else "reasoning error"
        if self.compare_error:
            return self.compare_error
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
            "reason": {
                "kind": self.reason.kind,
                "unsatisfiable": self.reason.unsatisfiable,
                "cause": self.reason.cause,
            },
            "expected_unsatisfiable": self.expected_unsatisfiable,
            "iri_error": self.iri_error,
            "explanation": None if self.explanation is None else str(self.explanation),
            "parse_error": self.parse_error,
            "logs": dict(self.logs),
            "timed_out": list(self.timed_out),
            "profile_error": self.profile_error,
            "compare_error": self.compare_error,
        }

    @classmethod
    def from_json(cls, data: dict) -> CheckReport:
        explanation = data["explanation"]
        return cls(
            profile_ok=data["profile_ok"],
            reason=ReasonResult(
                data["reason"]["kind"], data["reason"]["unsatisfiable"], data["reason"].get("cause", "")
            ),
            expected_unsatisfiable=data["expected_unsatisfiable"],
            iri_error=data["iri_error"],
            explanation=None if explanation is None else Path(explanation),
            parse_error=data.get("parse_error"),
            logs=dict(data.get("logs") or {}),
            timed_out=list(data.get("timed_out") or []),
            profile_error=data.get("profile_error"),
            compare_error=data.get("compare_error"),
        )


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""


def _subprocess_run(args: list[str], cwd: Path, timeout: float = CHECK_BUDGET) -> tuple[int, str]:
    """Run a command; a timeout is exit code 124 and a missing program 127, like the shell."""
    try:
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        partial = _text(e.output) + _text(e.stderr)
        return 124, f"{partial}\nerror: timed out after {timeout:.0f} s: {' '.join(args)}\n"
    except FileNotFoundError as e:
        return 127, f"error: cannot run {args[0]}: {e}\n"
    return proc.returncode, proc.stdout + proc.stderr


def run_checks(
    target: Target,
    robot_jar: Path,
    workdir: Path,
    run: Runner | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> CheckReport:
    """Run ROBOT's checks; together they get CHECK_BUDGET seconds.

    Each run gets the time left, and once it is used up the remaining runs are skipped.
    A run that times out (exit code 124) or is skipped is listed in ``timed_out``.
    """
    workdir = Path(workdir)
    robot = ["java", "-jar", str(robot_jar)]
    catalog = ["--catalog", str(target.catalog)] if target.catalog else []
    file = str(target.file)
    logs: dict[str, str] = {}
    timed_out: list[str] = []
    deadline = clock() + CHECK_BUDGET

    def run_step(step: str, args: list[str]) -> tuple[int, str]:
        """Run one ROBOT command and keep its output in <workdir>/<step>.log."""
        left = deadline - clock()
        if left < 1:
            code, out = 124, f"error: not run; the {CHECK_BUDGET // 60}-minute limit for all checks was used up\n"
        elif run is None:
            code, out = _subprocess_run(args, workdir, timeout=left)
        else:
            code, out = run(args, workdir)
        if code == 124:
            timed_out.append(step)
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

    code, out = run_step("profile", robot + ["validate-profile"] + catalog + ["--profile", "DL", "--input", file])
    profile_ok = code == 0
    # A timeout is reported through timed_out; any other failure without a violation report is ROBOT's own.
    profile_error = None
    if code not in (0, 124) and PROFILE_VIOLATION not in out:
        profile_error = robot_error_cause(out)

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
    compare_error = None
    if target.compare_with:
        code, out = run_step(
            "compare",
            robot + ["reason", "--reasoner", "HermiT", "--input", str(target.compare_with),
                     "--output", str(workdir / "reasoned-compare.owl")],
        )
        compared = classify_reasoning(code, out)
        expected = compared.unsatisfiable
        if compared.kind == "error" and code != 124:  # a timeout is reported through timed_out
            try:
                rel = Path(target.compare_with).relative_to(target.folder.parents[1]).as_posix()
            except ValueError:
                rel = Path(target.compare_with).name
            compare_error = f"reasoning on {rel} failed: {compared.cause}"

    return CheckReport(
        profile_ok, reason, expected, iri_error, explanation,
        logs=logs, timed_out=timed_out, profile_error=profile_error, compare_error=compare_error,
    )
