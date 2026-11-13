import json
from pathlib import Path

import pytest

from ontostart.checks import CheckReport, ReasonResult
from ontostart.cli import main
from ontostart.site import SiteContext, build_site
from ontostart.targets import Target

IRI = "https://w3id.org/ontostart/pizza/"
TTL = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
<%s> a owl:Ontology ; rdfs:label "%s" ; dcterms:description "A <pizza> ontology" ;
  dcterms:modified "2026-11-13" ; owl:versionInfo "1.0.2" .
"""
CTX = SiteContext("o/r", "main", "https://github.com", "https://gist/raw/", True)


def make(tmp_path, status="stable", label="Pizza", name="pizza", path=None, versions=("1.0.2", "1.0.10", "1.0.1")):
    folder = tmp_path / "ontologies" / name
    folder.mkdir(parents=True)
    file = folder / f"{name}.ttl"
    file.write_text(TTL % (IRI, label))
    for v in versions:
        d = folder / "versions" / v
        d.mkdir(parents=True)
        for e in ("ttl", "jsonld", "nt", "owl"):
            (d / f"{name}.{e}").write_text(v)
    return Target(name, path or name, folder, file, status, name, IRI, None, None)


def build(tmp_path, **kw):
    t = make(tmp_path, **kw)
    out = tmp_path / "site"
    build_site(t, "1.0.2", out, CTX)
    return t, out


def test_index_has_title_description_and_source(tmp_path):
    _, out = build(tmp_path)
    page = (out / "index.html").read_text()
    assert "<h1>Pizza</h1>" in page
    assert "A &lt;pizza&gt; ontology" in page
    assert 'href="https://github.com/o/r/tree/main/ontologies/pizza"' in page
    assert 'href="https://github.com/o/r/blob/main/ontologies/pizza/pizza.ttl"' in page
    assert 'href="versions/1.0.2/pizza.ttl"' in page and 'href="docs/pylode/"' in page
    assert 'href="foops/"' in page and "ontology-ci-foops-pizza.json" in page
    assert page.count("<img") == 7


def test_no_badges_or_foops_when_disabled(tmp_path):
    t = make(tmp_path)
    build_site(t, "1.0.2", tmp_path / "s", SiteContext("o/r", "main", "https://github.com", "", False))
    page = (tmp_path / "s" / "index.html").read_text()
    assert "<img" not in page and "foops" not in page


def test_index_escapes_html(tmp_path):
    _, out = build(tmp_path, label="<b>x</b>")
    page = (out / "index.html").read_text()
    assert "&lt;b&gt;x&lt;/b&gt;" in page and "<b>x</b>" not in page


def test_status_banners(tmp_path):
    _, out = build(tmp_path, status="experimental")
    assert ('<div class="banner banner-experimental">Experimental: this ontology is generated or '
            "still changing, and may change without notice.</div>") in (out / "index.html").read_text()
    _, out = build(tmp_path / "b", status="sandbox", name="testo", path="sandbox/testo")
    assert ('<div class="banner banner-sandbox">Sandbox: a tutorial ontology. It is not persistent '
            "and may be removed.</div>") in (out / "index.html").read_text()
    _, out = build(tmp_path / "c")
    assert "banner banner-" not in (out / "index.html").read_text()


def test_meta_json(tmp_path):
    _, out = build(tmp_path)
    meta = json.loads((out / "meta.json").read_text())
    assert set(meta) == {"name", "path", "status", "title", "description", "iri", "version",
                         "versions", "modified"}
    assert meta["versions"] == ["1.0.10", "1.0.2", "1.0.1"]
    assert meta["iri"] == IRI and meta["modified"] == "2026-11-13" and meta["title"] == "Pizza"


def test_version_landing_pages(tmp_path):
    _, out = build(tmp_path)
    page = (out / "1.0.1" / "index.html").read_text()
    assert 'href="pizza.ttl"' in page and 'href="../1.0.2/"' in page
    assert (out / "versions" / "latest" / "pizza.ttl").read_text() == "1.0.2"
    assert (out / "versions" / "1.0.10" / "pizza.owl").exists()


def test_missing_version_folder(tmp_path):
    t = make(tmp_path)
    with pytest.raises(FileNotFoundError, match="9.9.9"):
        build_site(t, "9.9.9", tmp_path / "s", CTX)


def test_site_cli_and_badges_cli(tmp_path, monkeypatch):
    t = make(tmp_path)
    monkeypatch.chdir(tmp_path)
    report = CheckReport(True, ReasonResult("consistent"), None, None, None)
    (tmp_path / "report.json").write_text(json.dumps(report.to_json()))
    (tmp_path / "foops.json").write_text((Path(__file__).parent / "fixtures" / "foops.json").read_text())
    rc = main(["site", "--target-json", json.dumps(t.to_json()), "--version", "1.0.2",
               "--out", "site", "--report", "report.json", "--step", "ontospy=true",
               "--step", "pylode=false", "--foops-json", "foops.json", "--result", "result.json",
               "--repo", "o/r", "--ref", "main"])
    assert rc == 0
    assert (tmp_path / "site" / "foops" / "index.html").exists()
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["steps"] == {"ontospy": True, "pylode": False}
    assert result["foops"]["label"] == "75.0% (1.50 in 2 tests)"

    pushed = []
    monkeypatch.setattr("ontostart.cli.push_badges", lambda g, tok, files: pushed.append((g, tok, files)))
    monkeypatch.delenv("GIST_TOKEN", raising=False)
    assert main(["badges", "--results", ".", "--gist", "g"]) == 0 and not pushed
    monkeypatch.setenv("GIST_TOKEN", "tok")
    assert main(["badges", "--results", ".", "--gist", "g", "--deployed", "pizza"]) == 0
    g, tok, files = pushed[0]
    assert (g, tok) == ("g", "tok") and len(files) == 7
    assert files["ontology-ci-deploy-pizza.json"]["message"] == "success"


def test_site_cli_bad_foops(tmp_path, monkeypatch):
    t = make(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "report.json").write_text(json.dumps(
        CheckReport(True, ReasonResult("consistent"), None, None, None).to_json()))
    (tmp_path / "bad.json").write_text("not json <")
    assert main(["site", "--target-json", json.dumps(t.to_json()), "--version", "1.0.2",
                 "--out", "site", "--report", "report.json", "--foops-json", "bad.json",
                 "--result", "result.json", "--repo", "o/r", "--ref", "main"]) == 0
    assert json.loads((tmp_path / "result.json").read_text())["foops"] is None
    assert "Could not load FOOPS results" in (tmp_path / "site/foops/index.html").read_text()


def test_site_cli_result_only(tmp_path, monkeypatch):
    t = make(tmp_path, versions=())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "report.json").write_text(json.dumps(
        CheckReport(False, ReasonResult("error"), None, None, None).to_json()))
    assert main(["site", "--target-json", json.dumps(t.to_json()), "--version", "",
                 "--report", "report.json", "--result-only", "--result", "result.json",
                 "--repo", "o/r", "--ref", "main"]) == 0
    assert not (tmp_path / "site").exists()
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["steps"] == {} and result["foops"] is None and result["version"] == ""
    assert result["report"]["profile_ok"] is False


def test_site_cli_requires_out_unless_result_only(tmp_path, monkeypatch, capsys):
    t = make(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "report.json").write_text(json.dumps(
        CheckReport(True, ReasonResult("consistent"), None, None, None).to_json()))
    assert main(["site", "--target-json", json.dumps(t.to_json()), "--version", "1.0.2",
                 "--report", "report.json", "--result", "result.json",
                 "--repo", "o/r", "--ref", "main"]) == 1
    assert "--out" in capsys.readouterr().err
