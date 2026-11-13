"""Reading and bumping ontology versions, and writing syntax variants."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from xml.sax import SAXParseException

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, XSD
from rdflib.plugins.parsers.notation3 import BadSyntax

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# What rdflib raises for a file it cannot parse (Turtle/N3, RDF/XML, and the rest).
PARSE_ERRORS = (BadSyntax, SAXParseException, ValueError)


class OntologyIRIError(Exception):
    """The file has no owl:Ontology with the expected IRI."""


def describe_parse_error(e: Exception) -> str:
    """One line with the line number and the parser's message."""
    if isinstance(e, BadSyntax):
        return f"line {e.lines + 1}: {e._why}"
    if isinstance(e, SAXParseException):
        return f"line {e.getLineNumber()}: {e.getMessage()}"
    return " ".join(str(e).split())


def _load(file: Path, base_iri: str) -> Graph:
    g = Graph()
    g.parse(file)
    onto = URIRef(base_iri)
    if (onto, RDF.type, OWL.Ontology) not in g:
        found = ", ".join(sorted(str(s) for s in g.subjects(RDF.type, OWL.Ontology)))
        raise OntologyIRIError(
            f"expected owl:Ontology <{base_iri}> in {file}; found: {found or 'none'}"
        )
    return g


def check_ontology_iri(file: Path, base_iri: str) -> None:
    _load(file, base_iri)


def current_version(file: Path, base_iri: str) -> str | None:
    g = _load(file, base_iri)
    value = g.value(URIRef(base_iri), OWL.versionInfo)
    return None if value is None else str(value)


def bump_version(file: Path, base_iri: str, versions_dir: Path, now: datetime) -> str:
    """Bump the patch version in place and return the new version."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    check_ontology_iri(file, base_iri)
    g = Graph()
    g.parse(file)
    onto = URIRef(base_iri)
    old = g.value(onto, OWL.versionInfo)
    old = "0.0.0" if old is None else str(old).strip()
    m = SEMVER_RE.match(old)
    major, minor, patch = map(int, m.groups()) if m else (0, 0, 0)
    new = f"{major}.{minor}.{patch + 1}"

    for prop in (OWL.versionIRI, OWL.versionInfo, DCTERMS.modified, DCTERMS.issued,
                 OWL.priorVersion, OWL.backwardCompatibleWith):
        g.remove((onto, prop, None))

    stamp = Literal(now.isoformat(), datatype=XSD.dateTime)
    g.add((onto, OWL.versionIRI, URIRef(f"{base_iri}{new}")))
    g.add((onto, OWL.versionInfo, Literal(new, datatype=XSD.string)))
    if (onto, DCTERMS.created, None) not in g:
        g.add((onto, DCTERMS.created, stamp))
    g.add((onto, DCTERMS.modified, stamp))
    g.add((onto, DCTERMS.issued, Literal(now.date().isoformat(), datatype=XSD.date)))
    if (Path(versions_dir) / old / f"{file.stem}.ttl").exists():
        g.add((onto, OWL.priorVersion, URIRef(f"{base_iri}{old}")))
        g.add((onto, OWL.backwardCompatibleWith, URIRef(f"{base_iri}{old}")))

    g.serialize(destination=file, format="turtle")
    return new


def write_variants(file: Path, out_dir: Path, name: str) -> list[Path]:
    """Write <name>.ttl, .jsonld, .nt and .owl (RDF/XML) into out_dir."""
    g = Graph()
    g.parse(file)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = [("ttl", "turtle"), ("jsonld", "json-ld"), ("nt", "nt"), ("owl", "xml")]
    paths = []
    for ext, fmt in formats:
        path = out_dir / f"{name}.{ext}"
        g.serialize(destination=path, format=fmt, encoding="utf-8")
        paths.append(path)
    return paths
