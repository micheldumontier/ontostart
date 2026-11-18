"""Setting up a repository made from the OntoStart template."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .config import NAME_RE, RESERVED, ConfigError, load_config
from .htaccess import render_htaccess

PLACEHOLDER = "CHANGEME"
_ACCOUNT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _readme(w3id: str, owner: str, repo: str) -> str:
    return (
        f"# https://w3id.org/{w3id}/\n\n"
        f"Redirects for the ontology collection `{w3id}`, published from "
        f"https://github.com/{owner}/{repo}.\n\n"
        f"Contact: GitHub @{owner}\n"
    )


def _initialised_as(root: Path) -> str | None:
    try:
        data = yaml.safe_load((root / "ontostart.yaml").read_text()) or {}
    except (OSError, yaml.YAMLError) as e:
        raise ConfigError(f"cannot read {root / 'ontostart.yaml'}: {e}") from e
    name = data.get("w3id") if isinstance(data, dict) else None
    return None if name in (None, PLACEHOLDER) else str(name)


def init_repo(root: Path, w3id: str, owner: str, repo: str, gist_id: str | None = None) -> list[Path]:
    """Fill in the template; return the files written. Running it again returns [].

    ``pages:`` follows owner and repo on every run unless it is a custom domain (not
    github.io). ``gist_id``: None keeps the current id, "" clears it, a value sets it.
    """
    root = Path(root)
    if not NAME_RE.match(w3id) or w3id in RESERVED:
        raise ConfigError(f"w3id name '{w3id}' must match {NAME_RE.pattern} and not be reserved")
    for what, value in (("owner", owner), ("repo", repo)):
        if not _ACCOUNT_RE.match(value):
            raise ConfigError(f"{what} '{value}' must match {_ACCOUNT_RE.pattern}")
    if gist_id and not re.fullmatch(r"[A-Za-z0-9]+", gist_id):
        raise ConfigError(f"gist id '{gist_id}' must be letters and digits")
    existing = _initialised_as(root)
    if existing is not None and existing != w3id:
        raise ConfigError(f"already initialised as {existing}")

    changed: list[Path] = []

    def write(path: Path, text: str) -> None:
        if not path.exists() or path.read_text() != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            changed.append(path)

    config_file = root / "ontostart.yaml"
    text = config_file.read_text()
    text = re.sub(r"(?m)^(w3id:[ \t]*)\S+", rf"\g<1>{w3id}", text)
    text = re.sub(
        r"(?m)^(pages:[ \t]*)https://[^\s/]+\.github\.io/[^\s#]*",
        rf"\g<1>https://{owner}.github.io/{repo}", text,
    )
    if gist_id is not None:
        value = gist_id or '""'
        text = re.sub(r"(?m)^(gist_id:[ \t]*)(\"\"|'')?[A-Za-z0-9]*", lambda m: m.group(1) + value, text)
    write(config_file, text.replace(PLACEHOLDER, w3id))

    for ttl in sorted((root / "ontologies").glob("**/*.ttl")):
        write(ttl, ttl.read_text().replace(f"https://w3id.org/{PLACEHOLDER}/", f"https://w3id.org/{w3id}/"))

    workflow = root / ".github/workflows/w3id-pr.yml"
    if workflow.is_file():
        write(workflow, workflow.read_text().replace(PLACEHOLDER, w3id))

    config = load_config(config_file)
    out = root / "apache/web" / w3id
    write(out / ".htaccess", render_htaccess(config))
    write(out / "README.md", _readme(w3id, owner, repo))
    return sorted(changed)
