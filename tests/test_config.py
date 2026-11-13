import pytest

from ontostart.config import ConfigError, load_config


def test_load_config_defaults(repo):
    (repo / "ontostart.yaml").write_text("w3id: x\npages: https://p.example/x/\ngist_id: ''\n")
    c = load_config(repo / "ontostart.yaml")
    assert c.sandbox is True and c.foops is True and c.term_docs == "ontospy"
    assert c.aliases == {} and c.legacy_root is None and c.ontologies == {}
    assert c.pages == "https://p.example/x"


def test_load_config_full(repo):
    c = load_config(repo / "ontostart.yaml")
    assert c.pages == "https://micheldumontier.github.io/ontostart"
    assert c.ontologies["suloized-pizza"].compare_unsatisfiable_with == "imports/pizza.owl"
    assert c.aliases == {"testo": "sandbox/testo"}


def test_load_config_legacy_root(repo):
    (repo / "ontostart.yaml").write_text(
        "w3id: x\npages: p\nlegacy_root:\n  path: main\n  name: ontostart\n"
    )
    c = load_config(repo / "ontostart.yaml")
    assert (c.legacy_root.path, c.legacy_root.name) == ("main", "ontostart")


def test_load_config_rejects_missing_w3id(tmp_path):
    p = tmp_path / "ontostart.yaml"
    p.write_text("pages: https://x\n")
    with pytest.raises(ConfigError, match="w3id"):
        load_config(p)
