from pathlib import Path

import yaml

from ontostart.checks import CHECK_BUDGET

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"

# Steps that call slow or external tools and so need their own limit.
SLOW_STEPS = {
    "Download ROBOT (checksum-verified)",
    "Install OntoSpy and pyLODE",
    "OntoSpy docs",
    "pyLODE docs",
    "FOOPS! assessment",
}
OTHER_STEPS_MINUTES = 8  # checkout, setup, engine install, version, variants, site, upload


def test_build_job_fits_its_time_limit():
    job = yaml.safe_load((WORKFLOWS / "build.yml").read_text())["jobs"]["build"]
    steps = {s["name"]: s for s in job["steps"]}
    assert SLOW_STEPS <= set(steps)
    limits = {name: steps[name].get("timeout-minutes") for name in SLOW_STEPS}
    assert all(limits.values()), limits
    worst_case = sum(limits.values()) + CHECK_BUDGET / 60 + OTHER_STEPS_MINUTES
    assert worst_case <= job["timeout-minutes"], (worst_case, job["timeout-minutes"])
