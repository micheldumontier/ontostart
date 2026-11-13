import json

import pytest

from conftest import write
from ontostart.cli import main
from ontostart.config import ConfigError, load_config
from ontostart.targets import Target, find_targets, make_plan


def cfg(repo):
    return load_config(repo / "ontostart.yaml")


def paths(plan):
    return [t.path for t in plan.targets]


def test_find_targets(repo):
    t = {x.path: x for x in find_targets(repo, cfg(repo))}
    assert t["pizza"].base_iri == "https://w3id.org/ontostart/pizza/" and t["pizza"].status == "stable"
    assert t["sandbox/testo"].safe == "sandbox-testo" and t["sandbox/testo"].status == "sandbox"
    assert t["sandbox/testo"].base_iri == "https://w3id.org/ontostart/sandbox/testo/"
    assert t["suloized-pizza"].status == "experimental"
    assert t["suloized-pizza"].catalog.name == "catalog-v001.xml"
    assert t["suloized-pizza"].compare_with == repo / "ontologies/suloized-pizza/imports/pizza.owl"
    assert t["pizza"].catalog is None and t["pizza"].compare_with is None
    assert [x.path for x in find_targets(repo, cfg(repo))] == sorted(t)


def test_find_targets_empty_repo(tmp_path):
    write(tmp_path / "ontostart.yaml", "w3id: x\npages: p\n")
    assert find_targets(tmp_path, load_config(tmp_path / "ontostart.yaml")) == []


@pytest.mark.parametrize("bad", ["Alice", "main", "catalog", "testo", "versions", "docs", "sandbox"])
def test_invalid_and_reserved_names(repo, bad):
    write(repo / "ontologies" / bad / f"{bad}.ttl")
    with pytest.raises(ConfigError, match=bad):
        find_targets(repo, cfg(repo))


def test_folder_without_matching_file(repo):
    write(repo / "ontologies/x/y.ttl")
    with pytest.raises(ConfigError, match="x"):
        find_targets(repo, cfg(repo))


def test_plan_main_push_changed_only(repo):
    p = make_plan(repo, cfg(repo), "main", "push", ["ontologies/pizza/pizza.ttl"])
    assert paths(p) == ["pizza"] and p.publish and p.bump


def test_plan_multiple_changed_folders(repo):
    p = make_plan(repo, cfg(repo), "main", "push",
                  ["ontologies/pizza/pizza.ttl", "sandbox/testo/README.md", "README.md"])
    assert paths(p) == ["pizza", "sandbox/testo"]


def test_plan_prefix_is_not_folder_match(repo):
    p = make_plan(repo, cfg(repo), "main", "push", ["ontologies/pizza-other/x.ttl"])
    assert p.targets == []


def test_plan_config_change_builds_all(repo):
    p = make_plan(repo, cfg(repo), "main", "push", ["ontostart.yaml"])
    assert paths(p) == ["pizza", "sandbox/testo", "suloized-pizza"]


def test_plan_sandbox_branch(repo):
    p = make_plan(repo, cfg(repo), "sandbox/testo", "push", ["ontologies/pizza/pizza.ttl"])
    assert paths(p) == ["sandbox/testo"] and p.publish and p.bump


def test_sandbox_branch_without_folder(repo):
    with pytest.raises(ConfigError, match="sandbox/alice/alice.ttl"):
        make_plan(repo, cfg(repo), "sandbox/alice", "push", [])


def test_nested_sandbox_branch(repo):
    with pytest.raises(ConfigError):
        make_plan(repo, cfg(repo), "sandbox/a/b", "push", [])


def test_plan_pr_from_sandbox_branch_uses_changed_files(repo):
    p = make_plan(repo, cfg(repo), "sandbox/testo", "pull_request", ["ontologies/pizza/pizza.ttl"])
    assert paths(p) == ["pizza"] and not p.publish and not p.bump
    p = make_plan(repo, cfg(repo), "sandbox/a/b", "pull_request", ["sandbox/testo/testo.ttl"])
    assert paths(p) == ["sandbox/testo"] and not p.publish


def test_plan_dispatch_on_sandbox_branch(repo):
    p = make_plan(repo, cfg(repo), "sandbox/testo", "workflow_dispatch", None)
    assert paths(p) == ["sandbox/testo"] and p.publish and not p.bump


def test_plan_other_branch_and_pr(repo):
    p = make_plan(repo, cfg(repo), "feature", "push", ["ontologies/pizza/pizza.ttl"])
    assert paths(p) == ["pizza"] and not p.publish and not p.bump
    p = make_plan(repo, cfg(repo), "main", "pull_request", ["ontologies/pizza/pizza.ttl"])
    assert paths(p) == ["pizza"] and not p.publish and not p.bump


def test_plan_dispatch(repo):
    p = make_plan(repo, cfg(repo), "main", "workflow_dispatch", None, only="pizza", bump=False)
    assert paths(p) == ["pizza"] and p.publish and not p.bump
    p = make_plan(repo, cfg(repo), "main", "workflow_dispatch", None)
    assert len(p.targets) == 3 and p.publish and not p.bump
    p = make_plan(repo, cfg(repo), "main", "workflow_dispatch", None, bump=True)
    assert p.bump


def test_plan_only_unknown(repo):
    with pytest.raises(ConfigError, match="nope"):
        make_plan(repo, cfg(repo), "main", "workflow_dispatch", None, only="nope")


def test_sandbox_disabled(repo):
    (repo / "ontostart.yaml").write_text("w3id: ontostart\npages: p\nsandbox: false\n")
    assert [t.path for t in find_targets(repo, cfg(repo))] == ["pizza", "suloized-pizza"]
    with pytest.raises(ConfigError):
        make_plan(repo, cfg(repo), "sandbox/testo", "push", [])


def test_target_json_round_trip(repo):
    for t in find_targets(repo, cfg(repo)):
        data = json.loads(json.dumps(t.to_json()))
        assert data["file"] == f"{t.folder.relative_to(repo).as_posix()}/{t.name}.ttl"
        assert Target.from_json(data, repo) == t


def test_cli_plan(repo, capsys, monkeypatch):
    monkeypatch.chdir(repo)
    (repo / "changed.txt").write_text("ontologies/pizza/pizza.ttl\n")
    assert main(["plan", "--ref", "main", "--event", "push", "--changed-file", "changed.txt"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    data = json.loads(out)
    assert [t["path"] for t in data["targets"]] == ["pizza"]
    assert data["publish"] is True and data["bump"] is True
    assert data["foops"] is True and data["gist_id"] == "abc"
