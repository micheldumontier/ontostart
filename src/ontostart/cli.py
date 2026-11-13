"""The ``ontostart`` command line."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .badges import badge_files, push_badges
from .catalogue import build_catalogue
from .checks import CheckReport, run_checks
from .config import ConfigError, load_config
from .foops import FoopsSummary, summarize_foops, write_foops_page
from .site import SiteContext, _metadata, build_site
from .targets import Target, make_plan
from .versioning import (
    OntologyIRIError,
    bump_version,
    current_version,
    write_variants,
)


def _bool(value: str) -> bool:
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise argparse.ArgumentTypeError("expected true or false")


def _plan(args: argparse.Namespace) -> int:
    root = Path.cwd()
    config = load_config(root / "ontostart.yaml")
    changed = None
    if args.changed_file:
        lines = Path(args.changed_file).read_text().splitlines()
        changed = [line.strip() for line in lines if line.strip()]
    plan = make_plan(root, config, args.ref, args.event, changed, args.only, args.bump)
    print(json.dumps({
        "targets": [t.to_json() for t in plan.targets],
        "publish": plan.publish,
        "bump": plan.bump,
    }))
    return 0


def _target(args: argparse.Namespace) -> Target:
    return Target.from_json(json.loads(args.target_json), Path.cwd())


def _version(args: argparse.Namespace) -> int:
    target = _target(args)
    if args.bump:
        version = bump_version(
            target.file, target.base_iri, target.folder / "versions", datetime.now(timezone.utc)
        )
    else:
        version = current_version(target.file, target.base_iri)
        if version is None:
            print(f"error: no owl:versionInfo in {target.file}", file=sys.stderr)
            return 1
    print(version)
    return 0


def _variants(args: argparse.Namespace) -> int:
    target = _target(args)
    out = target.folder / "versions" / args.version
    for path in write_variants(target.file, out, target.name):
        print(path)
    return 0


def _check(args: argparse.Namespace) -> int:
    target = _target(args)
    out = Path(args.out)
    report = run_checks(target, Path(args.robot), out.resolve().parent)
    out.write_text(json.dumps(report.to_json(), indent=2) + "\n")
    return 0


def _step(value: str) -> tuple[str, bool]:
    kind, _, flag = value.partition("=")
    return kind, _bool(flag)


def _site(args: argparse.Namespace) -> int:
    target = _target(args)
    report = CheckReport.from_json(json.loads(Path(args.report).read_text()))
    steps = dict(args.step or [])
    out = Path(args.out)
    foops = None
    foops_error = ""
    if args.foops_json:
        try:
            foops = summarize_foops(json.loads(Path(args.foops_json).read_text()))
        except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as e:
            foops_error = str(e)
    ctx = SiteContext(args.repo, args.ref, args.server_url, args.badge_base, bool(args.foops_json))
    build_site(target, args.version, out, ctx)
    if args.foops_json:
        title, _, _ = _metadata(target)
        write_foops_page(foops, out, title, target.base_iri, foops_error)
    Path(args.result).write_text(json.dumps({
        "target": target.to_json(),
        "report": report.to_json(),
        "version": args.version,
        "steps": steps,
        "foops": None if foops is None else {"label": foops.label, "checks": foops.checks},
    }, indent=2) + "\n")
    return 0


def _badges(args: argparse.Namespace) -> int:
    token = os.environ.get("GIST_TOKEN", "")
    if not token or not args.gist:
        print("notice: no GIST_TOKEN or gist id; skipping badges")
        return 0
    files: dict[str, dict] = {}
    for path in sorted(Path(args.results).rglob("result.json")):
        data = json.loads(path.read_text())
        target = Target.from_json(data["target"], Path.cwd())
        deployed = None if args.deployed is None else target.safe in args.deployed
        foops = data.get("foops")
        files.update(badge_files(
            target, CheckReport.from_json(data["report"]), data["version"], data["steps"],
            deployed, None if foops is None else FoopsSummary(foops["label"], foops["checks"]),
        ))
    push_badges(args.gist, token, files)
    return 0


def _catalogue(args: argparse.Namespace) -> int:
    config = load_config(Path.cwd() / "ontostart.yaml")
    build_catalogue(Path(args.site), config)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ontostart")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", help="decide which ontologies a CI run builds")
    p.add_argument("--ref", required=True)
    p.add_argument("--event", required=True)
    p.add_argument("--changed-file")
    p.add_argument("--only")
    p.add_argument("--bump", type=_bool)
    p.set_defaults(func=_plan)
    p = sub.add_parser("version", help="print or bump an ontology's version")
    p.add_argument("--target-json", required=True)
    p.add_argument("--bump", action="store_true")
    p.set_defaults(func=_version)
    p = sub.add_parser("variants", help="write syntax variants of a version")
    p.add_argument("--target-json", required=True)
    p.add_argument("--version", required=True)
    p.set_defaults(func=_variants)
    p = sub.add_parser("check", help="run profile and reasoning checks")
    p.add_argument("--target-json", required=True)
    p.add_argument("--robot", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=_check)
    p = sub.add_parser("site", help="build the site for one ontology")
    p.add_argument("--target-json", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--step", action="append", type=_step)
    p.add_argument("--foops-json")
    p.add_argument("--result", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--ref", required=True)
    p.add_argument("--server-url", default="https://github.com")
    p.add_argument("--badge-base", default="")
    p.set_defaults(func=_site)
    p = sub.add_parser("badges", help="push badge files to the gist")
    p.add_argument("--results", required=True)
    p.add_argument("--gist", required=True)
    p.add_argument("--deployed", nargs="*")
    p.set_defaults(func=_badges)
    p = sub.add_parser("catalogue", help="build the root catalogue page and DCAT files")
    p.add_argument("--site", required=True)
    p.set_defaults(func=_catalogue)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, OntologyIRIError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
