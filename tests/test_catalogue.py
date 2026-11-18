import pytest
import json
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from ontostart.catalogue import build_catalogue
from ontostart.config import Config

DCAT = Namespace("http://www.w3.org/ns/dcat#")
CONFIG = Config(w3id="ontostart", pages="https://example.github.io/ontostart")


def _meta(root: Path, path: str, status: str, title: str, name: str):
    d = root / path
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({
        "name": name, "path": path, "status": status, "title": title,
        "description": f"About {title}", "iri": f"https://w3id.org/ontostart/{path}",
        "version": "1.2.3", "versions": ["1.2.3"], "modified": "2026-01-01",
        **({} if name == "pizza" else {"source": f"https://github.com/o/r/tree/main/{path}"}),
    }))


def _site(tmp_path: Path) -> Path:
    _meta(tmp_path, "pizza", "stable", "Pizza", "pizza")
    _meta(tmp_path, "suloized-pizza", "experimental", "Suloized", "suloized-pizza")
    _meta(tmp_path, "sandbox/testo", "sandbox", "Testo", "testo")
    (tmp_path / "main").mkdir()
    (tmp_path / "testo").mkdir()
    return tmp_path


def test_catalogue_lists_sections(tmp_path):
    build_catalogue(_site(tmp_path), CONFIG)
    page = (tmp_path / "index.html").read_text()
    assert "<title>ontostart ontologies</title>" in page
    i, j, k = page.index("Ontologies</h2>"), page.index("Experimental</h2>"), page.index("Sandbox</h2>")
    assert i < page.index('href="pizza/"') < j < page.index('href="suloized-pizza/"') < k
    assert k < page.index('href="sandbox/testo/"')


def test_catalogue_ignores_dirs_without_meta(tmp_path):
    build_catalogue(_site(tmp_path), CONFIG)
    page = (tmp_path / "index.html").read_text()
    assert 'href="main/"' not in page and 'href="testo/"' not in page


def test_dcat_excludes_sandbox(tmp_path):
    build_catalogue(_site(tmp_path), CONFIG)
    g = Graph().parse(tmp_path / "catalog.ttl")
    assert len(list(g.subjects(RDF.type, DCAT.Dataset))) == 2
    assert len(list(g.subjects(RDF.type, DCAT.Distribution))) == 8
    assert (URIRef("https://w3id.org/ontostart/"), RDF.type, DCAT.Catalog) in g
    assert "sandbox/testo" not in (tmp_path / "catalog.ttl").read_text()


def test_catalog_files_parse(tmp_path):
    build_catalogue(_site(tmp_path), CONFIG)
    sizes = {
        e: len(Graph().parse(tmp_path / f"catalog.{e}", format=f))
        for e, f in [("ttl", "turtle"), ("jsonld", "json-ld"), ("nt", "nt"), ("owl", "xml")]
    }
    assert len(set(sizes.values())) == 1 and sizes["ttl"] > 0


def test_catalogue_is_deterministic(tmp_path):
    # Unchanged content must give byte-identical files, so concurrent publishes rebase cleanly.
    site = _site(tmp_path)
    build_catalogue(site, CONFIG)
    first = {e: (site / f"catalog.{e}").read_bytes() for e in ("ttl", "jsonld", "nt", "owl")}
    first["index.html"] = (site / "index.html").read_bytes()
    build_catalogue(site, CONFIG)
    for name, data in first.items():
        path = site / (name if name == "index.html" else f"catalog.{name}")
        assert path.read_bytes() == data, name


def test_catalogue_is_deterministic_across_hash_seeds(tmp_path):
    # Blank-node ids and serialisation order must not depend on PYTHONHASHSEED.
    import os
    import subprocess
    import sys

    code = (
        "import sys; from pathlib import Path; from ontostart.catalogue import build_catalogue; "
        "from ontostart.config import Config; "
        "build_catalogue(Path(sys.argv[1]), Config(w3id='ontostart', pages='https://example.github.io/ontostart'))"
    )
    outputs = []
    for seed in ("1", "2"):
        site = _site(tmp_path / seed)
        env = {**os.environ, "PYTHONHASHSEED": seed}
        subprocess.run([sys.executable, "-c", code, str(site)], check=True, env=env)
        outputs.append({e: (site / f"catalog.{e}").read_bytes() for e in ("ttl", "jsonld", "nt", "owl")})
    for ext in outputs[0]:
        assert outputs[0][ext] == outputs[1][ext], ext


def test_catalogue_shows_iri_source_and_status_notes(tmp_path):
    build_catalogue(_site(tmp_path), CONFIG)
    page = (tmp_path / "index.html").read_text()
    assert '<a href="https://w3id.org/ontostart/">https://w3id.org/ontostart/</a>' in page
    sandbox = page[page.index("Sandbox</h2>"):]
    assert '<a href="https://w3id.org/ontostart/sandbox/testo">https://w3id.org/ontostart/sandbox/testo</a>' in sandbox
    assert '<a href="https://github.com/o/r/tree/main/sandbox/testo">source</a>' in sandbox
    assert "not persistent" in sandbox
    assert "may change without notice" in page[page.index("Experimental</h2>"):page.index("Sandbox</h2>")]
    # Older meta.json files have no "source": the card simply has no source link.
    stable = page[page.index("Ontologies</h2>"):page.index("Experimental</h2>")]
    assert ">source<" not in stable and 'href="https://w3id.org/ontostart/pizza"' in stable


def test_catalogue_escapes_source(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({
        "name": "x", "path": "x", "status": "stable", "title": "X",
        "iri": "https://w3id.org/ontostart/x/", "source": 'javascript:alert(1)"',
    }))
    build_catalogue(tmp_path, CONFIG)
    page = (tmp_path / "index.html").read_text()
    assert "javascript:" not in page


HOME_CONFIG = Config(w3id="ontostart", pages="https://example.github.io/ontostart", home="site/index.html")


def test_catalogue_with_home_page(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "site").mkdir(parents=True)
    (repo / "site/index.html").write_text("<!doctype html><title>Landing</title>")
    monkeypatch.chdir(repo)
    site = _site(tmp_path / "site-out")
    build_catalogue(site, HOME_CONFIG)
    assert (site / "index.html").read_text() == "<!doctype html><title>Landing</title>"
    page = (site / "catalog/index.html").read_text()
    assert 'href="../pizza/"' in page and 'href="../sandbox/testo/"' in page
    assert 'href="../catalog.ttl"' in page and 'href="../">' in page
    assert (site / "catalog.ttl").is_file()


def test_catalogue_without_home_has_no_catalog_page(tmp_path):
    build_catalogue(_site(tmp_path), CONFIG)
    assert not (tmp_path / "catalog").exists()
    assert 'href="pizza/"' in (tmp_path / "index.html").read_text()


def test_catalogue_missing_home_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    site = _site(tmp_path / "site-out")
    with pytest.raises(FileNotFoundError, match="site/index.html"):
        build_catalogue(site, HOME_CONFIG)


def test_catalogue_keeps_home_when_not_writing_it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no site/index.html here: it must not be read
    site = _site(tmp_path / "site-out")
    (site / "index.html").write_text("published home")
    build_catalogue(site, HOME_CONFIG, write_home=False)
    assert (site / "index.html").read_text() == "published home"
    assert 'href="../pizza/"' in (site / "catalog/index.html").read_text()


def test_catalogue_cli_no_home(tmp_path, monkeypatch):
    from ontostart.cli import main
    (tmp_path / "ontostart.yaml").write_text("w3id: ontostart\npages: https://x\nhome: site/index.html\n")
    monkeypatch.chdir(tmp_path)
    site = _site(tmp_path / "site-out")
    assert main(["catalogue", "--site", str(site), "--no-home"]) == 0
    assert (site / "catalog/index.html").is_file() and not (site / "index.html").exists()
