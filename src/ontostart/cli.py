"""The ``ontostart`` command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .targets import make_plan


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
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
