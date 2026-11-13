"""The ``ontostart`` command line."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import ConfigError, load_config
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
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, OntologyIRIError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
