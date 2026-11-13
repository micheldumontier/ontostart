import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL
import rdflib.namespace as rdfns

from ontostart.cli import main
from ontostart.versioning import (
    OntologyIRIError,
    bump_version,
    check_ontology_iri,
    current_version,
    write_variants,
)

BASE = "https://w3id.org/ontostart/sandbox/testo/"
ONTO = URIRef(BASE)
FIXTURE = Path(__file__).parent / "fixtures" / "minimal.ttl"
NOW = datetime(2026, 11, 13, 10, 30, tzinfo=timezone.utc)


@pytest.fixture
def ttl(tmp_path):
    folder = tmp_path / "sandbox" / "testo"
    folder.mkdir(parents=True)
    f = folder / "testo.ttl"
    shutil.copy(FIXTURE, f)
    return f


def load(f):
    return Graph().parse(f)


def test_bump_patch(ttl):
    assert bump_version(ttl, BASE, ttl.parent / "versions", NOW) == "0.0.2"
    g = load(ttl)
    assert g.value(ONTO, OWL.versionIRI) == URIRef(BASE + "0.0.2")
    assert [str(o) for o in g.objects(ONTO, OWL.versionInfo)] == ["0.0.2"]
    assert g.value(ONTO, DCTERMS.issued) == Literal("2026-11-13", datatype=rdfns.XSD.date)
    assert g.value(ONTO, DCTERMS.modified).toPython() == NOW


def test_bump_rejects_naive_now(ttl):
    with pytest.raises(ValueError, match="timezone-aware"):
        bump_version(ttl, BASE, ttl.parent / "versions", datetime(2026, 11, 13))


def test_bump_links_prior_version(ttl):
    prior = ttl.parent / "versions" / "0.0.1"
    prior.mkdir(parents=True)
    (prior / "testo.ttl").write_text(FIXTURE.read_text())
    bump_version(ttl, BASE, ttl.parent / "versions", NOW)
    g = load(ttl)
    assert g.value(ONTO, OWL.priorVersion) == URIRef(BASE + "0.0.1")
    assert g.value(ONTO, OWL.backwardCompatibleWith) == URIRef(BASE + "0.0.1")


def test_bump_no_prior_without_snapshot(ttl):
    bump_version(ttl, BASE, ttl.parent / "versions", NOW)
    assert load(ttl).value(ONTO, OWL.priorVersion) is None


def test_bump_keeps_created(ttl):
    g = load(ttl)
    created = Literal("2020-01-01T00:00:00+00:00", datatype=rdfns.XSD.dateTime)
    g.add((ONTO, DCTERMS.created, created))
    g.serialize(ttl, format="turtle")
    bump_version(ttl, BASE, ttl.parent / "versions", NOW)
    g = load(ttl)
    assert [str(o) for o in g.objects(ONTO, DCTERMS.created)] == [str(created)]
    assert g.value(ONTO, DCTERMS.modified).toPython() == NOW


def test_bump_sets_created_when_missing(ttl):
    bump_version(ttl, BASE, ttl.parent / "versions", NOW)
    assert load(ttl).value(ONTO, DCTERMS.created).toPython() == NOW


@pytest.mark.parametrize("old", [None, "v2"])
def test_bump_without_version_info(ttl, old):
    g = load(ttl)
    g.remove((ONTO, OWL.versionInfo, None))
    if old:
        g.add((ONTO, OWL.versionInfo, Literal(old)))
    g.serialize(ttl, format="turtle")
    assert bump_version(ttl, BASE, ttl.parent / "versions", NOW) == "0.0.1"


def test_bump_rejects_wrong_ontology_iri(ttl):
    with pytest.raises(OntologyIRIError, match="https://w3id.org/ontostart/sandbox/alice/"):
        bump_version(ttl, "https://w3id.org/ontostart/sandbox/alice/", ttl.parent / "v", NOW)


def test_check_ontology_iri(ttl):
    check_ontology_iri(ttl, BASE)
    with pytest.raises(OntologyIRIError, match="found: " + BASE):
        check_ontology_iri(ttl, BASE + "other/")


def test_current_version(ttl):
    assert current_version(ttl, BASE) == "0.0.1"
    g = load(ttl)
    g.remove((ONTO, OWL.versionInfo, None))
    g.serialize(ttl, format="turtle")
    assert current_version(ttl, BASE) is None


def test_write_variants(ttl, tmp_path):
    out = tmp_path / "out"
    paths = write_variants(ttl, out, "testo")
    assert [p.name for p in paths] == ["testo.ttl", "testo.jsonld", "testo.nt", "testo.owl"]
    n = len(load(ttl))
    for p in paths:
        assert len(Graph().parse(p)) == n


def _target_json(ttl):
    root = ttl.parents[2]
    return json.dumps({
        "name": "testo", "path": "sandbox/testo", "folder": "sandbox/testo",
        "file": "sandbox/testo/testo.ttl", "status": "sandbox", "safe": "sandbox-testo",
        "base_iri": BASE, "catalog": None, "compare_with": None,
    }), root


def test_cli_version_and_variants(ttl, monkeypatch, capsys):
    tj, root = _target_json(ttl)
    monkeypatch.chdir(root)
    assert main(["version", "--target-json", tj]) == 0
    assert capsys.readouterr().out.strip() == "0.0.1"
    assert main(["version", "--target-json", tj, "--bump"]) == 0
    assert capsys.readouterr().out.strip() == "0.0.2"
    assert main(["variants", "--target-json", tj, "--version", "0.0.2"]) == 0
    lines = capsys.readouterr().out.split()
    assert len(lines) == 4 and all(Path(p).exists() for p in lines)


def test_cli_reports_iri_error(ttl, monkeypatch, capsys):
    tj, root = _target_json(ttl)
    data = json.loads(tj)
    data["base_iri"] = "https://w3id.org/ontostart/sandbox/alice/"
    monkeypatch.chdir(root)
    assert main(["version", "--target-json", json.dumps(data), "--bump"]) == 1
    assert "expected owl:Ontology" in capsys.readouterr().err


def test_cli_version_without_version_info(ttl, monkeypatch, capsys):
    g = load(ttl)
    g.remove((ONTO, OWL.versionInfo, None))
    g.serialize(ttl, format="turtle")
    tj, root = _target_json(ttl)
    monkeypatch.chdir(root)
    assert main(["version", "--target-json", tj]) == 1
    assert "no owl:versionInfo" in capsys.readouterr().err
