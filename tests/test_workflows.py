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


ENGINE_PATHS = {"src/**", "pyproject.toml", "uv.lock", ".github/workflows/build.yml"}


def test_this_repository_checks_ontologies_on_engine_pull_requests():
    # Dependabot's pull requests for the engine's actions and packages change only these
    # files; the collection workflow must run on them and plan every ontology.
    workflow = yaml.safe_load((WORKFLOWS / "ontostart.yml").read_text())
    pr_paths = set(workflow[True]["pull_request"]["paths"])  # PyYAML reads "on" as True
    assert ENGINE_PATHS <= pr_paths
    assert ".github/workflows/ontostart.yml" in pr_paths
    plan = (WORKFLOWS / "build.yml").read_text()
    assert 'if [ -z "$ENGINE_REF" ]; then args+=(--self-engine); fi' in plan
