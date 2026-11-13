from pathlib import Path

import pytest

CONFIG = """\
w3id: ontostart
pages: https://micheldumontier.github.io/ontostart/
gist_id: abc
aliases:
  testo: sandbox/testo
ontologies:
  suloized-pizza:
    status: experimental
    compare_unsatisfiable_with: imports/pizza.owl
"""


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    write(tmp_path / "ontostart.yaml", CONFIG)
    write(tmp_path / "ontologies/pizza/pizza.ttl")
    write(tmp_path / "ontologies/suloized-pizza/suloized-pizza.ttl")
    write(tmp_path / "ontologies/suloized-pizza/catalog-v001.xml")
    write(tmp_path / "sandbox/testo/testo.ttl")
    return tmp_path
