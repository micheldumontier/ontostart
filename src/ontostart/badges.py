"""Shields endpoint badge files, kept in a gist."""

from __future__ import annotations

import json
import urllib.request

from .checks import CheckReport
from .foops import FoopsSummary
from .targets import Target


def _badge(label: str, message: str, color: str) -> dict:
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def _ok(flag: bool) -> tuple[str, str]:
    return ("success", "brightgreen") if flag else ("failure", "red")


def badge_files(
    target: Target,
    report: CheckReport,
    version: str,
    steps: dict[str, bool],
    deployed: bool | None,
    foops: FoopsSummary | None,
) -> dict[str, dict]:
    """Badges for steps missing from ``steps``, an empty version, or None flags are omitted."""
    badges = {
        "profile": _badge("OWL DL Profile", *_ok(report.profile_ok)),
        "reason": _badge("Reasoning", report.reason.message, report.reason.color),
    }
    if version:
        badges["version"] = _badge("Version", version, "brightgreen")
    for step in ("ontospy", "pylode"):
        if step in steps:
            badges[step] = _badge(step, *_ok(steps[step]))
    if deployed is not None:
        badges["deploy"] = _badge("deploy", *_ok(deployed))
    if foops is not None:
        badges["foops"] = _badge("FOOPS!", foops.label, "blue")
    return {f"ontology-ci-{kind}-{target.safe}.json": b for kind, b in badges.items()}


def push_badges(gist_id: str, token: str, files: dict[str, dict]) -> None:
    body = {"files": {name: {"content": json.dumps(value)} for name, value in files.items()}}
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gist_id}",
        data=json.dumps(body).encode(),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req):
        pass
