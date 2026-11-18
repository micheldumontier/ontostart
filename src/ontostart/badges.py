"""Shields endpoint badge files, kept in a gist."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Callable

from .checks import CheckReport
from .foops import FoopsSummary
from .targets import Target


def _badge(label: str, message: str, color: str) -> dict:
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def _ok(flag: bool) -> tuple[str, str]:
    return ("success", "brightgreen") if flag else ("failure", "red")


def _profile(report: CheckReport) -> tuple[str, str]:
    """"error" when the check could not run (ROBOT failed or timed out), not a profile violation."""
    if report.profile_error or "profile" in report.timed_out:
        return ("error", "red")
    return _ok(report.profile_ok)


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
        "profile": _badge("OWL DL Profile", *_profile(report)),
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


ATTEMPTS = 4  # waits of 2, 4 and 8 seconds between them


class BadgeError(Exception):
    """The gist could not be updated."""


def _api_message(e: urllib.error.HTTPError) -> str:
    try:
        return json.loads(e.read() or b"{}").get("message", "") or e.reason
    except (ValueError, AttributeError, OSError):
        return str(e.reason)


def push_badges(
    gist_id: str, token: str, files: dict[str, dict], sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Update the gist in one PATCH, retrying server and connection errors.

    Raises BadgeError on a 4xx (not retried) or when every attempt failed.
    """
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
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=30):
                return
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise BadgeError(
                    f"HTTP {e.code} from the gist API: {_api_message(e)} (check GIST_TOKEN and gist_id)"
                ) from None
            problem = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            problem = f"connection error ({getattr(e, 'reason', None) or type(e).__name__})"
        if attempt < ATTEMPTS:
            print(f"badges: {problem}; retrying", flush=True)
            sleep(2 ** attempt)
    raise BadgeError(f"{problem} after {ATTEMPTS} attempts")
