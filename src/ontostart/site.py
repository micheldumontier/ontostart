"""The per-ontology site: ontology page, meta.json, versions and landing pages."""

from __future__ import annotations

import html as h
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, URIRef
from rdflib.namespace import DCTERMS, RDFS

from .targets import Target
from .versioning import SEMVER_RE

EXTS = ["ttl", "jsonld", "nt", "owl"]
KINDS = ["profile", "reason", "version", "ontospy", "pylode", "deploy", "foops"]
BANNERS = {
    "experimental": "Experimental: this ontology is generated or still changing, and may change without notice.",
    "sandbox": "Sandbox: a tutorial ontology. It is not persistent and may be removed.",
}

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} — {version} ({safe})</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; margin: 2rem; line-height: 1.5; }}
    header h1 {{ margin: 0 0 .25rem 0; }}
    .description {{ max-width: 900px; margin: .25rem 0 1rem 0; font-size: 1.05rem; }}
    .banner {{ max-width: 900px; padding: .5rem .75rem; border-radius: 8px; margin: 0 0 1rem 0; }}
    .banner-experimental {{ background: #fef3c7; border: 1px solid #d97706; }}
    .banner-sandbox {{ background: #dbeafe; border: 1px solid #2563eb; }}
    .meta {{ color: #555; margin-bottom: 1rem; }}
    .badges img {{ margin-right: .5rem; vertical-align: middle; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 1rem; max-width: 900px; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem; }}
    code, a {{ color: #0b5fff; word-break: break-all; }}
    ul {{ margin: .25rem 0 .5rem 1.25rem; }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    {description}
    {banner}
    <div class="meta">
      <div><strong>Ontology IRI:</strong> <code>{iri}</code></div>
      <div><strong>Source:</strong> <a href="{tree}">{repo} (<code>{ref}</code>)</a> · <a href="{blob}">{file}</a></div>
      <div><strong>Version:</strong> <code>{version}</code></div>
      <div><strong>Modified:</strong> <code>{modified}</code></div>
    </div>
    {badges}
  </header>

  <div class="grid">
    <section class="card">
      <h2>Downloads (version {version})</h2>
      <ul>
{downloads}
      </ul>
    </section>

    <section class="card">
      <h2>Documentation</h2>
      <ul>
        <li><a href="docs/pylode/">PyLODE</a></li>
        <li><a href="docs/ontospy/">Ontospy</a></li>
        {foops}
      </ul>
    </section>

    <section class="card">
      <h2>All Versions</h2>
      <ul>
{versions}
      </ul>
    </section>
  </div>
</body>
</html>
"""

LANDING = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{name} {v}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.5; }}
    h1 {{ margin-bottom: .25rem; }}
    .meta {{ color: #555; margin-bottom: 1.5rem; }}
    a {{ color: #0b5fff; }}
    ul {{ margin: .25rem 0 .5rem 1.25rem; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem; max-width: 600px; margin-bottom: 1rem; }}
  </style>
</head>
<body>
  <h1>{name} <code>{v}</code>{current}</h1>
  <div class="meta"><a href="../">← back to {name}</a></div>
  <div class="card">
    <h2>Downloads</h2>
    <ul>
{links}
    </ul>
  </div>
  <div class="card">
    <h2>Other versions</h2>
    <ul>
{others}
    </ul>
  </div>
</body>
</html>
"""


@dataclass(frozen=True)
class SiteContext:
    repo: str
    ref: str
    server_url: str
    badge_base: str
    foops_enabled: bool


def _semver_key(v: str) -> tuple[int, ...]:
    return tuple(map(int, SEMVER_RE.match(v).groups()))


def _text(g: Graph, onto: URIRef, *props) -> str:
    for prop in props:
        vals = list(g.objects(onto, prop))
        for v in vals:
            if getattr(v, "language", None) in ("en", None):
                return str(v).strip()
        if vals:
            return str(vals[0]).strip()
    return ""


def _metadata(target: Target) -> tuple[str, str, str]:
    g = Graph()
    g.parse(target.file)
    onto = URIRef(target.base_iri)
    title = _text(g, onto, RDFS.label, DCTERMS.title) or target.name
    description = _text(g, onto, DCTERMS.description, RDFS.comment)
    modified = next((str(v) for v in g.objects(onto, DCTERMS.modified)), "")
    return title, description, modified


def _versions(target: Target) -> list[str]:
    base = target.folder / "versions"
    found = [d.name for d in base.iterdir() if d.is_dir() and SEMVER_RE.match(d.name)] if base.is_dir() else []
    return sorted(found, key=_semver_key, reverse=True)


def _badges(target: Target, ctx: SiteContext) -> str:
    if not ctx.badge_base:
        return ""
    kinds = [k for k in KINDS if k != "foops" or ctx.foops_enabled]
    imgs = "\n      ".join(
        f'<img alt="{k}" src="{h.escape(ctx.badge_base)}ontology-ci-{k}-{h.escape(target.safe)}.json" />'
        for k in kinds
    )
    return f'<div class="badges">\n      {imgs}\n    </div>'


def build_site(target: Target, version: str, out: Path, ctx: SiteContext) -> None:
    out = Path(out)
    src_versions = target.folder / "versions"
    if not (src_versions / version).is_dir():
        raise FileNotFoundError(f"no {version} folder in {src_versions}; run `ontostart variants` first")
    versions = _versions(target)
    if version not in versions:
        raise FileNotFoundError(f"version '{version}' is not x.y.z")
    title, description, modified = _metadata(target)
    name = target.name

    for v in versions:
        shutil.copytree(src_versions / v, out / "versions" / v, dirs_exist_ok=True)
    shutil.copytree(src_versions / version, out / "versions" / "latest", dirs_exist_ok=True)

    for v in versions:
        d = out / v
        d.mkdir(parents=True, exist_ok=True)
        present = [e for e in EXTS if (src_versions / v / f"{name}.{e}").exists()]
        for e in present:
            shutil.copy(src_versions / v / f"{name}.{e}", d / f"{name}.{e}")
        links = "\n".join(f'      <li><a href="{name}.{e}">{name}.{e}</a></li>' for e in present)
        others = "\n".join(
            f'      <li><a href="../{ov}/">{ov}</a>{" (current)" if ov == version else ""}</li>'
            for ov in versions if ov != v
        )
        (d / "index.html").write_text(LANDING.format(
            name=h.escape(name), v=v, links=links, others=others,
            current=" <strong>(current)</strong>" if v == version else "",
        ), encoding="utf-8")

    repo_url = f"{ctx.server_url.rstrip('/')}/{ctx.repo}"
    rel = target.to_json()
    ref = quote(ctx.ref, safe="/")
    rows = "\n".join(
        f'        <li><a href="versions/{v}/{name}.ttl">{v}</a> — '
        + " | ".join(f'<a href="versions/{v}/{name}.{e}">{e}</a>' for e in EXTS)
        + (" <strong>(current)</strong>" if v == version else "") + "</li>"
        for v in versions
    )
    downloads = "\n".join(
        f'        <li><a href="versions/{version}/{name}.{e}">{name}.{e}</a></li>' for e in EXTS
    )
    banner = BANNERS.get(target.status)
    page = PAGE.format(
        title=h.escape(title), version=h.escape(version), safe=h.escape(target.safe),
        description=f'<p class="description">{h.escape(description)}</p>' if description else "",
        banner=f'<div class="banner banner-{h.escape(target.status)}">{h.escape(banner)}</div>' if banner else "",
        iri=h.escape(target.base_iri),
        tree=h.escape(f"{repo_url}/tree/{ref}/{rel['folder']}"),
        blob=h.escape(f"{repo_url}/blob/{ref}/{rel['file']}"),
        repo=h.escape(ctx.repo), ref=h.escape(ctx.ref), file=h.escape(rel["file"]),
        modified=h.escape(modified), badges=_badges(target, ctx),
        downloads=downloads, versions=rows,
        foops='<li><a href="foops/">FOOPS! detailed report</a></li>' if ctx.foops_enabled else "",
    )
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "meta.json").write_text(json.dumps({
        "name": name, "path": target.path, "status": target.status, "title": title,
        "description": description, "iri": target.base_iri, "version": version,
        "versions": versions, "modified": modified,
    }, indent=2) + "\n", encoding="utf-8")
