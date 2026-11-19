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
MAX_RATE_WAIT = 60  # longest rate-limit wait honoured; a longer one gives up at once


class BadgeError(Exception):
    """The gist could not be updated."""


def _api_message(e: urllib.error.HTTPError) -> str:
    try:
        return json.loads(e.read() or b"{}").get("message", "") or e.reason
    except (ValueError, AttributeError, OSError):
        return str(e.reason)


def _rate_limit_wait(e: urllib.error.HTTPError, message: str, now: float) -> float | None:
    """Seconds GitHub asks us to wait, or None when the error is not a rate limit.

    GitHub signals rate limits with a 403 or 429 and, in order of precedence, a
    Retry-After header, an exhausted X-RateLimit-Remaining with its reset time, or
    only a message; for the last it asks clients to wait at least a minute.
    """
    if e.code not in (403, 429):
        return None
    headers = e.headers or {}
    try:
        if headers.get("Retry-After") is not None:
            return max(1.0, float(headers["Retry-After"]))
        if headers.get("X-RateLimit-Remaining") == "0" and headers.get("X-RateLimit-Reset"):
            return max(1.0, float(headers["X-RateLimit-Reset"]) - now)
    except ValueError:
        pass
    if e.code == 429 or "rate limit" in message.lower():
        return 60.0
    return None


def push_badges(
    gist_id: str,
    token: str,
    files: dict[str, dict],
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.time,
) -> None:
    """Update the gist in one PATCH, retrying server errors, connection errors and
    short rate limits.

    Raises BadgeError on any other 4xx (not retried), on a rate limit longer than
    MAX_RATE_WAIT, or when every attempt failed.
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
        wait: float = 2 ** attempt
        try:
            with urllib.request.urlopen(req, timeout=30):
                return
        except urllib.error.HTTPError as e:
            if e.code < 500:
                message = _api_message(e)
                rate_wait = _rate_limit_wait(e, message, now())
                if rate_wait is None:
                    raise BadgeError(
                        f"HTTP {e.code} from the gist API: {message} (check GIST_TOKEN and gist_id)"
                    ) from None
                if rate_wait > MAX_RATE_WAIT:
                    raise BadgeError(
                        f"rate limited by the gist API; it asks to wait {rate_wait:.0f} s"
                    ) from None
                problem, wait = f"HTTP {e.code} (rate limited)", rate_wait
            else:
                problem = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            problem = f"connection error ({getattr(e, 'reason', None) or type(e).__name__})"
        if attempt < ATTEMPTS:
            print(f"badges: {problem}; retrying in {wait:.0f} s", flush=True)
            sleep(wait)
    raise BadgeError(f"{problem} after {ATTEMPTS} attempts")
