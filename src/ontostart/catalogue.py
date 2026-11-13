"""The root catalogue: an HTML index and a DCAT description of every published ontology."""

from __future__ import annotations

import html as h
import json
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF

from .config import Config

DCAT = Namespace("http://www.w3.org/ns/dcat#")
FORMATS = [
    ("ttl", "turtle", "text/turtle"),
    ("jsonld", "json-ld", "application/ld+json"),
    ("nt", "nt", "application/n-triples"),
    ("owl", "xml", "application/rdf+xml"),
]
SECTIONS = [("stable", "Ontologies"), ("experimental", "Experimental"), ("sandbox", "Sandbox")]

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; margin: 2rem; line-height: 1.5; }}
    h1 {{ margin: 0 0 .25rem 0; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem; max-width: 900px; margin-bottom: 1rem; }}
    .description {{ margin: .25rem 0; }}
    code, a {{ color: #0b5fff; word-break: break-all; }}
    ul {{ margin: .25rem 0 .5rem 1.25rem; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>Catalogue files: {files}</p>
{sections}
</body>
</html>
"""


def _load(site_root: Path) -> list[dict]:
    entries = []
    for path in sorted(site_root.glob("*/meta.json")) + sorted(site_root.glob("sandbox/*/meta.json")):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(meta, dict) and meta.get("path") and meta.get("status"):
            entries.append(meta)
    return entries


def _section(label: str, entries: list[dict]) -> str:
    items = []
    for m in sorted(entries, key=lambda m: str(m.get("title") or m.get("name") or m["path"]).lower()):
        title = str(m.get("title") or m.get("name") or m["path"])
        desc = str(m.get("description") or "")
        items.append(
            f'    <div><a href="{h.escape(str(m["path"]))}/">{h.escape(title)}</a>'
            f' <code>{h.escape(str(m.get("version") or ""))}</code>'
            + (f'<p class="description">{h.escape(desc)}</p>' if desc else "")
            + "</div>"
        )
    return f'  <section class="card">\n    <h2>{label}</h2>\n' + "\n".join(items) + "\n  </section>"


def _dcat(entries: list[dict], config: Config) -> Graph:
    # SimpleMemory keeps insertion order (the default store iterates a set), so the
    # N-Triples and RDF/XML files are byte-identical when nothing changed.
    g = Graph(store="SimpleMemory")
    g.bind("dcat", DCAT)
    g.bind("dcterms", DCTERMS)
    g.bind("owl", OWL)
    catalog = URIRef(f"https://w3id.org/{config.w3id}/")
    g.add((catalog, RDF.type, DCAT.Catalog))
    g.add((catalog, DCTERMS.title, Literal(f"{config.w3id} ontologies")))
    for m in entries:
        if m["status"] not in ("stable", "experimental") or not m.get("iri"):
            continue
        ds = URIRef(m["iri"])
        landing = f"{config.pages}/{m['path']}/"
        g.add((catalog, DCAT.dataset, ds))
        g.add((ds, RDF.type, DCAT.Dataset))
        g.add((ds, DCTERMS.title, Literal(m.get("title") or m.get("name") or m["path"])))
        if m.get("description"):
            g.add((ds, DCTERMS.description, Literal(m["description"])))
        if m.get("version"):
            g.add((ds, OWL.versionInfo, Literal(m["version"])))
        g.add((ds, DCAT.landingPage, URIRef(landing)))
        safe = str(m["path"]).replace("/", "-")
        for ext, _, media in FORMATS:
            # A fixed blank-node id keeps the files byte-identical when nothing changed.
            dist = BNode(f"dist-{safe}-{ext}")
            g.add((ds, DCAT.distribution, dist))
            g.add((dist, RDF.type, DCAT.Distribution))
            g.add((dist, DCAT.downloadURL, URIRef(f"{landing}versions/latest/{m['name']}.{ext}")))
            g.add((dist, DCAT.mediaType, Literal(media)))
    return g


def build_catalogue(site_root: Path, config: Config) -> None:
    site_root = Path(site_root)
    entries = _load(site_root)
    sections = "\n".join(
        _section(label, [m for m in entries if m["status"] == status])
        for status, label in SECTIONS
        if any(m["status"] == status for m in entries)
    )
    files = " | ".join(f'<a href="catalog.{ext}">catalog.{ext}</a>' for ext, _, _ in FORMATS)
    (site_root / "index.html").write_text(
        PAGE.format(title=h.escape(f"{config.w3id} ontologies"), files=files, sections=sections),
        encoding="utf-8",
    )
    g = _dcat(entries, config)
    for ext, fmt, _ in FORMATS:
        text = g.serialize(format=fmt)
        if fmt == "json-ld":
            # rdflib emits the top-level nodes in set order; sort them so the file is stable.
            nodes = json.loads(text)
            if isinstance(nodes, list):
                nodes.sort(key=lambda node: str(node.get("@id", "")))
            text = json.dumps(nodes, indent=2, ensure_ascii=False) + "\n"
        (site_root / f"catalog.{ext}").write_text(text, encoding="utf-8")
