"""Finding ontology folders and deciding which ones a CI run builds."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config, ConfigError

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
RESERVED = {"sandbox", "versions", "docs", "catalog", "main"}
STATUSES = {"stable", "experimental"}


@dataclass(frozen=True)
class Target:
    name: str
    path: str  # "<name>" or "sandbox/<name>"
    folder: Path
    file: Path
    status: str
    safe: str
    base_iri: str
    catalog: Path | None
    compare_with: Path | None

    def to_json(self) -> dict:
        """Paths are repo-relative POSIX strings (the folder is <root>/<kind>/<name>)."""
        base = self.folder.parents[1]

        def rel(p: Path | None) -> str | None:
            return None if p is None else p.relative_to(base).as_posix()

        return {
            "name": self.name,
            "path": self.path,
            "folder": rel(self.folder),
            "file": rel(self.file),
            "status": self.status,
            "safe": self.safe,
            "base_iri": self.base_iri,
            "catalog": rel(self.catalog),
            "compare_with": rel(self.compare_with),
        }

    @classmethod
    def from_json(cls, data: dict, root: Path) -> Target:
        def res(value: str | None) -> Path | None:
            return None if value is None else root / value

        return cls(
            name=data["name"],
            path=data["path"],
            folder=root / data["folder"],
            file=root / data["file"],
            status=data["status"],
            safe=data["safe"],
            base_iri=data["base_iri"],
            catalog=res(data["catalog"]),
            compare_with=res(data["compare_with"]),
        )


@dataclass(frozen=True)
class Plan:
    targets: list[Target]
    publish: bool
    bump: bool


def _build(root: Path, config: Config, kind: str, name: str) -> Target:
    sandbox = kind == "sandbox"
    where = f"{kind}/{name}"
    if not NAME_RE.match(name):
        raise ConfigError(f"{where}: folder name must match {NAME_RE.pattern}")
    if not sandbox and (name in RESERVED or name in config.aliases):
        raise ConfigError(f"{where}: '{name}' is a reserved name or an alias")
    folder = root / kind / name
    file = folder / f"{name}.ttl"
    if not file.is_file():
        raise ConfigError(f"{where}: expected {kind}/{name}/{name}.ttl")

    settings = config.ontologies.get(name) if not sandbox else None
    status = "sandbox" if sandbox else ((settings and settings.status) or "stable")
    if not sandbox and status not in STATUSES:
        raise ConfigError(f"{where}: status must be one of {sorted(STATUSES)}, not '{status}'")
    path = where if sandbox else name
    catalog = folder / "catalog-v001.xml"
    compare = settings.compare_unsatisfiable_with if settings else None
    return Target(
        name=name,
        path=path,
        folder=folder,
        file=file,
        status=status,
        safe=path.replace("/", "-"),
        base_iri=f"https://w3id.org/{config.w3id}/{path}/",
        catalog=catalog if catalog.is_file() else None,
        compare_with=folder / compare if compare else None,
    )


def find_targets(root: Path, config: Config) -> list[Target]:
    root = Path(root)
    kinds = ["ontologies"] + (["sandbox"] if config.sandbox else [])
    targets = []
    for kind in kinds:
        base = root / kind
        if base.is_dir():
            targets += [_build(root, config, kind, d.name) for d in base.iterdir() if d.is_dir()]
    return sorted(targets, key=lambda t: t.path)


def _inside(changed: str, target: Target, root: Path) -> bool:
    return changed.startswith(target.folder.relative_to(root).as_posix() + "/")


def make_plan(
    root: Path,
    config: Config,
    ref: str,
    event: str,
    changed: list[str] | None,
    only: str | None = None,
    bump: bool | None = None,
) -> Plan:
    root = Path(root)
    all_targets = find_targets(root, config)
    on_sandbox = ref.startswith("sandbox/")
    on_main = ref == "main"

    if on_sandbox:
        name = ref[len("sandbox/"):]
        if not config.sandbox:
            raise ConfigError(f"ref {ref}: sandbox is disabled in ontostart.yaml")
        if "/" in name or not NAME_RE.match(name):
            raise ConfigError(f"ref {ref}: sandbox branches are sandbox/<name> with a plain name")
        targets = [t for t in all_targets if t.path == ref]
        if not targets:
            raise ConfigError(f"ref {ref}: expected sandbox/{name}/{name}.ttl")
    elif changed is None or "ontostart.yaml" in changed:
        targets = all_targets
    else:
        targets = [t for t in all_targets if any(_inside(c, t, root) for c in changed)]

    if only is not None:
        targets = [t for t in targets if t.path == only]
        if not targets:
            raise ConfigError(f"no target '{only}'")

    publishing_ref = on_main or on_sandbox
    publish = publishing_ref and event in ("push", "workflow_dispatch")
    if bump is None:
        bump = publishing_ref and event == "push"
    return Plan(targets=targets, publish=publish, bump=bump and publish)
