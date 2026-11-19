import json
import shutil
from pathlib import Path

import pytest

from ontostart.cli import main
from ontostart.config import ConfigError, load_config
from ontostart.init import init_repo
from ontostart.targets import make_plan

TEMPLATE = Path(__file__).resolve().parent.parent / "template"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(TEMPLATE, root)
    return root


def test_init_rewrites_iris(repo):
    changed = init_repo(repo, "myonto", "alice", "my-repo", "abc123")
    assert changed == sorted(changed)
    assert not [p for p in repo.rglob("*") if p.is_file() and "CHANGEME" in p.read_text()]
    assert "https://w3id.org/myonto/testo/" in (repo / "ontologies/testo/testo.ttl").read_text()
    config = load_config(repo / "ontostart.yaml")
    assert (config.w3id, config.pages, config.gist_id) == (
        "myonto", "https://alice.github.io/my-repo", "abc123")
    assert (repo / "apache/web/myonto/.htaccess").is_file()
    readme = (repo / "apache/web/myonto/README.md").read_text()
    assert "https://github.com/alice/my-repo" in readme and "@alice" in readme
    assert "W3ID_FOLDER: myonto" in (repo / ".github/workflows/w3id-pr.yml").read_text()


def test_init_is_idempotent(repo):
    init_repo(repo, "myonto", "alice", "my-repo")
    assert init_repo(repo, "myonto", "alice", "my-repo") == []


def test_init_rejects_reinit_with_other_name(repo):
    init_repo(repo, "myonto", "alice", "my-repo")
    with pytest.raises(ConfigError, match="already initialised as myonto"):
        init_repo(repo, "other", "alice", "my-repo")


@pytest.mark.parametrize("w3id, owner, repo_name", [
    ("My Onto", "alice", "r"), ("sandbox", "alice", "r"),
    ("ok", "bad owner", "r"), ("ok", "alice", "bad/repo"),
])
def test_init_rejects_bad_name(repo, w3id, owner, repo_name):
    with pytest.raises(ConfigError):
        init_repo(repo, w3id, owner, repo_name)
    assert "CHANGEME" in (repo / "ontostart.yaml").read_text()


def test_template_plan(repo):
    init_repo(repo, "myonto", "alice", "my-repo")
    plan = make_plan(repo, load_config(repo / "ontostart.yaml"), "main", "push", None)
    assert [t.path for t in plan.targets] == ["testo"]


def test_cli_init(repo, capsys):
    code = main(["init", "--w3id", "myonto", "--owner", "alice", "--repo", "r", "--root", str(repo)])
    assert code == 0 and "ontostart.yaml" in capsys.readouterr().out
    assert main(["init", "--w3id", "Bad", "--owner", "alice", "--repo", "r", "--root", str(repo)]) == 2
    assert "error" in capsys.readouterr().err


def test_template_does_not_leak_identity():
    allowed = {"README.md", ".github/workflows/ontostart.yml", ".github/workflows/w3id-pr.yml",
               ".github/dependabot.yml"}
    for path in TEMPLATE.rglob("*"):
        rel = path.relative_to(TEMPLATE).as_posix()
        if path.is_file() and rel not in allowed:
            assert "micheldumontier" not in path.read_text(), rel
    for rel in (".github/workflows/ontostart.yml", ".github/workflows/w3id-pr.yml"):
        for line in (TEMPLATE / rel).read_text().splitlines():
            if "micheldumontier" in line:
                assert "uses: micheldumontier/ontostart/.github/workflows/" in line or line.lstrip().startswith("#")
    mentions = [line.strip() for line in (TEMPLATE / ".github/dependabot.yml").read_text().splitlines()
                if "micheldumontier" in line]
    assert mentions == ['- "micheldumontier/ontostart*"']


def test_plan_skips_uninitialised_template(repo, capsys, monkeypatch):
    monkeypatch.chdir(repo)
    assert main(["plan", "--ref", "main", "--event", "push"]) == 0
    out = capsys.readouterr()
    assert json.loads(out.out)["targets"] == []
    assert "ontostart init" in out.err


def test_init_rerun_with_other_owner_updates_pages_and_readme(repo):
    init_repo(repo, "myonto", "alice", "my-repo")
    changed = init_repo(repo, "myonto", "bob", "onto")
    assert repo / "ontostart.yaml" in changed
    assert load_config(repo / "ontostart.yaml").pages == "https://bob.github.io/onto"
    readme = (repo / "apache/web/myonto/README.md").read_text()
    assert "https://github.com/bob/onto" in readme and "@bob" in readme


def test_init_keeps_a_custom_pages_domain(repo):
    init_repo(repo, "myonto", "alice", "my-repo")
    config = repo / "ontostart.yaml"
    config.write_text(config.read_text().replace("https://alice.github.io/my-repo", "https://onto.example.org"))
    init_repo(repo, "myonto", "bob", "onto")
    assert load_config(config).pages == "https://onto.example.org"


def test_init_gist_kept_when_omitted_and_cleared_when_empty(repo):
    init_repo(repo, "myonto", "alice", "my-repo", "abc123")
    assert init_repo(repo, "myonto", "alice", "my-repo") == []
    assert load_config(repo / "ontostart.yaml").gist_id == "abc123"
    init_repo(repo, "myonto", "alice", "my-repo", "def456")
    assert load_config(repo / "ontostart.yaml").gist_id == "def456"
    init_repo(repo, "myonto", "alice", "my-repo", "")
    assert load_config(repo / "ontostart.yaml").gist_id == ""
    assert 'gist_id: ""' in (repo / "ontostart.yaml").read_text()


def test_cli_init_gist_flag(repo):
    args = ["init", "--w3id", "myonto", "--owner", "alice", "--repo", "r", "--root", str(repo)]
    assert main(args + ["--gist", "abc123"]) == 0
    assert main(args) == 0
    assert load_config(repo / "ontostart.yaml").gist_id == "abc123"
    assert main(args + ["--gist", ""]) == 0
    assert load_config(repo / "ontostart.yaml").gist_id == ""


def test_template_upgrades_through_uses_lines_only():
    import yaml

    from ontostart.targets import REBUILD_ALL

    workflow = yaml.safe_load((TEMPLATE / ".github/workflows/ontostart.yml").read_text())
    triggers = workflow[True]  # PyYAML reads the key "on" as True
    for event in ("push", "pull_request"):
        assert ".github/workflows/ontostart.yml" in triggers[event]["paths"]
    assert ".github/workflows/ontostart.yml" in REBUILD_ALL
    for rel in (".github/workflows/ontostart.yml", ".github/workflows/w3id-pr.yml"):
        assert "engine-ref" not in (TEMPLATE / rel).read_text(), rel
