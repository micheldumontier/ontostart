import re
from dataclasses import replace
from pathlib import Path

import pytest

from conftest import write
from ontostart.cli import main
from ontostart.config import ConfigError, load_config
from ontostart.htaccess import render_htaccess

ROOT = Path(__file__).resolve().parents[1]


def config():
    return load_config(ROOT / "ontostart.yaml")


def rules(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("RewriteRule")]


def test_render_matches_committed_file():
    committed = (ROOT / "apache/web/ontostart/.htaccess").read_text()
    assert render_htaccess(config()) == committed


def test_render_has_no_forbidden_constructs():
    text = render_htaccess(config())
    assert "{{" not in text
    for line in rules(text):
        for bad in ("R=301", "REQUEST_URI", "HTTP_HOST", "https://w3id.org"):
            assert bad not in line, line
        target = line.split()[2]
        if target != "-":
            assert target.startswith("https://micheldumontier.github.io/ontostart/"), line
            assert line.endswith("[R=303,L]"), line
    for header in ('Header always set Access-Control-Allow-Origin "*"',
                   'Header always merge Vary "Accept"', "Options -MultiViews", "RewriteEngine On"):
        assert header in text.splitlines()


def test_render_lists_no_ontology_names():
    text = render_htaccess(config())
    for name in ("pizza", "pro", "suloized-pizza"):
        assert not re.search(rf"\b{re.escape(name)}\b", text), name


def test_render_states_it_is_generated():
    text = render_htaccess(config())
    assert text.startswith("###")
    assert "ontostart htaccess" in text.split("\n\n")[0]
    assert "ontostart.yaml" in text.split("\n\n")[0]


def test_alias_and_legacy_root_rendered():
    text = render_htaccess(config())
    assert "^testo(/.*)?$" in text and "E=P:sandbox/testo%1" in text
    assert "E=B:main" in text and "E=BONTO:ontostart" in text
    assert r"^(\d+\.\d+\.\d+(/.*)?|versions(/.*)?|docs(/.*)?|ontostart\." in text
    bare = render_htaccess(replace(config(), legacy_root=None, aliases={}))
    assert "testo" not in bare
    assert "Legacy root" not in bare and "E=B:main" not in bare and "BONTO:ontostart" not in bare


def test_sandbox_disabled_renders_no_sandbox_rules():
    text = render_htaccess(replace(config(), sandbox=False, aliases={}))
    assert "sandbox/[a-z0-9]" not in text
    assert "^sandbox/?$" not in text
    # /sandbox... is still never taken for an ontology
    assert "sandbox|" in text


def test_term_docs_parameter():
    assert "[E=TERM_DOCS:ontospy]" in render_htaccess(config())
    assert "[E=TERM_DOCS:site]" in render_htaccess(replace(config(), term_docs="site"))


@pytest.mark.parametrize("aliases", [{"te sto": "sandbox/testo"}, {"testo": "sandbox/te,sto"},
                                     {"testo": ""}, {"testo": "../x"}])
def test_unsafe_alias_rejected(aliases):
    with pytest.raises(ConfigError):
        render_htaccess(replace(config(), aliases=aliases))


def test_cli_writes_htaccess(tmp_path, monkeypatch):
    write(tmp_path / "ontostart.yaml", (ROOT / "ontostart.yaml").read_text())
    monkeypatch.chdir(tmp_path)
    assert main(["htaccess"]) == 0
    assert (tmp_path / "apache/web/ontostart/.htaccess").read_text() == render_htaccess(config())
    assert main(["htaccess", "--out", "x/h.txt"]) == 0
    assert (tmp_path / "x/h.txt").read_text() == render_htaccess(config())
