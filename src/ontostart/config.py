"""Reading ``ontostart.yaml``."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
RESERVED = {"sandbox", "versions", "docs", "catalog", "main"}


class ConfigError(Exception):
    """The repository or its ``ontostart.yaml`` is not valid."""


@dataclass(frozen=True)
class OntologySettings:
    status: str | None = None
    compare_unsatisfiable_with: str | None = None


@dataclass(frozen=True)
class LegacyRoot:
    path: str
    name: str


@dataclass(frozen=True)
class Config:
    w3id: str
    pages: str
    gist_id: str = ""
    sandbox: bool = True
    foops: bool = True
    term_docs: str = "ontospy"
    aliases: dict[str, str] = field(default_factory=dict)
    legacy_root: LegacyRoot | None = None
    ontologies: dict[str, OntologySettings] = field(default_factory=dict)


def _text(data: dict, key: str, *, required: bool = False, default: str = "") -> str:
    value = data.get(key)
    if value is None or value == "":
        if required:
            raise ConfigError(f"ontostart.yaml: '{key}' is required")
        return default
    if not isinstance(value, str):
        raise ConfigError(f"ontostart.yaml: '{key}' must be a string")
    return value


def _flag(data: dict, key: str) -> bool:
    value = data.get(key, True)
    if not isinstance(value, bool):
        raise ConfigError(f"ontostart.yaml: '{key}' must be true or false")
    return value


def _aliases(data: dict) -> dict[str, str]:
    aliases = data.get("aliases") or {}
    if not isinstance(aliases, dict):
        raise ConfigError("ontostart.yaml: 'aliases' must be a mapping")
    aliases = {str(k): str(v).strip("/") for k, v in aliases.items()}
    for key, target in aliases.items():
        if not NAME_RE.match(key) or key in RESERVED:
            raise ConfigError(
                f"ontostart.yaml: alias '{key}' must match {NAME_RE.pattern} and not be reserved"
            )
        if target.split("/")[0] in aliases:
            raise ConfigError(f"ontostart.yaml: alias '{key}' points to another alias: '{target}'")
    return aliases


def load_config(path: Path) -> Config:
    try:
        data = yaml.safe_load(Path(path).read_text()) or {}
    except (OSError, yaml.YAMLError) as e:
        raise ConfigError(f"cannot read {path}: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping")

    term_docs = _text(data, "term_docs", default="ontospy")
    if term_docs not in ("ontospy", "site"):
        raise ConfigError("ontostart.yaml: 'term_docs' must be 'ontospy' or 'site'")

    aliases = _aliases(data)

    legacy = data.get("legacy_root")
    legacy_root = None
    if legacy:
        if not isinstance(legacy, dict) or not legacy.get("path") or not legacy.get("name"):
            raise ConfigError("ontostart.yaml: 'legacy_root' needs 'path' and 'name'")
        legacy_root = LegacyRoot(path=str(legacy["path"]), name=str(legacy["name"]))

    ontologies = {}
    for name, settings in (data.get("ontologies") or {}).items():
        settings = settings or {}
        ontologies[str(name)] = OntologySettings(
            status=settings.get("status"),
            compare_unsatisfiable_with=settings.get("compare_unsatisfiable_with"),
        )

    return Config(
        w3id=_text(data, "w3id", required=True),
        pages=_text(data, "pages", required=True).rstrip("/"),
        gist_id=_text(data, "gist_id"),
        sandbox=_flag(data, "sandbox"),
        foops=_flag(data, "foops"),
        term_docs=term_docs,
        aliases=aliases,
        legacy_root=legacy_root,
        ontologies=ontologies,
    )
