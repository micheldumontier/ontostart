"""The w3id.org ``.htaccess``, rendered from ``ontostart.yaml``.

The rules never list ontologies: any ``/<name>/`` or ``/sandbox/<name>/``
resolves to that folder on GitHub Pages. Only aliases and the legacy root
ontology come from the configuration.
"""

from __future__ import annotations

import re
from importlib.resources import files

from .config import RESERVED, Config, ConfigError

_SEGMENT = r"[A-Za-z0-9_][A-Za-z0-9._-]*"
_SAFE_PATH = re.compile(rf"^{_SEGMENT}(/{_SEGMENT})*$")
_EXT = "(ttl|owl|jsonld|nt)"


def _safe(value: str, what: str) -> str:
    value = value.strip("/")
    if not _SAFE_PATH.match(value):
        raise ConfigError(f"ontostart.yaml: {what} '{value}' is not a plain path")
    return value


def _aliases(config: Config) -> str:
    if not config.aliases:
        return ""
    lines = ["### Aliases: old paths rewritten to the current ones (then redirected like them)"]
    for old, new in config.aliases.items():
        old, new = _safe(old, "alias"), _safe(new, "alias target")
        lines += [
            f"RewriteCond %{{ENV:P}} ^{re.escape(old)}(/.*)?$",
            f"RewriteRule ^ - [E=P:{new}%1]",
        ]
    return "\n".join(lines)


def _sandbox_root(config: Config) -> str:
    if not config.sandbox:
        return ""
    return "\n".join([
        "### Sandbox: /sandbox and /sandbox/ are the catalogue",
        "RewriteCond %{ENV:P} ^sandbox/?$",
        f"RewriteRule ^ {config.pages}/ [R=303,L]",
    ])


def _sandbox_split(config: Config) -> str:
    if not config.sandbox:
        return ""
    return "\n".join([
        "RewriteCond %{ENV:B} ^$",
        "RewriteCond %{ENV:P} ^(sandbox/[a-z0-9][a-z0-9-]*)(/(.*))?$",
        "RewriteRule ^ - [E=B:%1,E=REST:%3]",
    ]) + "\n"


def _legacy(config: Config) -> tuple[str, str]:
    if config.legacy_root is None:
        return "", ""
    path = _safe(config.legacy_root.path, "legacy_root path")
    name = _safe(config.legacy_root.name, "legacy_root name")
    block = "\n".join([
        f"### Legacy root: the retired root ontology, in {path}/ as {name}.<ext>",
        f"### /x.y.z, /versions/..., /docs/... and /{name}.<ext> resolve as /{path}/... does",
        f"RewriteCond %{{ENV:P}} ^(\\d+\\.\\d+\\.\\d+(/.*)?|versions(/.*)?|docs(/.*)?"
        f"|{re.escape(name)}\\.{_EXT})$",
        f"RewriteRule ^ - [E=B:{path},E=REST:%1]",
        f"RewriteCond %{{ENV:P}} ^{re.escape(path)}(/(.*))?$",
        f"RewriteRule ^ - [E=B:{path},E=REST:%2]",
    ])
    bonto = "\n".join([
        f"RewriteCond %{{ENV:B}} ^{re.escape(path)}$",
        f"RewriteRule ^ - [E=BONTO:{name}]",
    ]) + "\n"
    return block, bonto


def _layout(config: Config) -> str:
    rows = []
    if config.sandbox:
        rows += [
            ("/sandbox, /sandbox/", "the catalogue"),
            ("/sandbox/N/...", "sandbox ontology N, as /N/..."),
        ]
    for old, new in config.aliases.items():
        rows.append((f"/{old.strip('/')}/...", f"same as /{new.strip('/')}/... (alias)"))
    if config.legacy_root is not None:
        path, name = config.legacy_root.path.strip("/"), config.legacy_root.name
        rows += [
            ("/x.y.z", f"retired root ontology, that version (as /{path}/x.y.z)"),
            ("/x.y.z/...", f"same as /{path}/x.y.z/..."),
            (f"/versions/..., /docs/..., /{name}.<ext>", f"same as /{path}/..."),
        ]
    return "".join(
        f"###   {left:<24} {right}\n" if len(left) <= 24 else f"###   {left}   {right}\n"
        for left, right in rows
    )


def render_htaccess(config: Config) -> str:
    """The ``.htaccess`` for ``https://w3id.org/<w3id>/``."""
    legacy, legacy_bonto = _legacy(config)
    reserved = sorted(RESERVED)
    values = {
        "w3id": config.w3id,
        "pages": config.pages,
        "term_docs": config.term_docs,
        "layout": _layout(config),
        "reserved_list": ", ".join(reserved),
        "reserved": "|".join(reserved),
        "aliases": _aliases(config),
        "sandbox_root": _sandbox_root(config),
        "legacy": legacy,
        "sandbox_split": _sandbox_split(config),
        "legacy_bonto": legacy_bonto,
    }
    text = (files("ontostart") / "templates" / "htaccess.tmpl").read_text()
    text = re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], text)
    # An empty block leaves its placeholder line blank
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip("\n") + "\n"
