[![branch CI](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml/badge.svg?branch=testo)](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml?query=branch%3Atesto)
![Version](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-version-testo.json) ![OWL DL profile](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-profile-testo.json) ![Reasoning](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-reason-testo.json) ![FOOPS!](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-foops-testo.json)

# Ontostart Test Ontology

The Ontostart Test Ontology.

A test ontology with no terms of its own. It exists to exercise the OntoStart CI on a branch; it isn't meant for reuse.

| | |
|---|---|
| IRI | <https://w3id.org/ontostart/testo/> |
| Prefix | `testo:` |
| Documentation | [Website](https://micheldumontier.github.io/ontostart/testo/) · [OntoSpy](https://micheldumontier.github.io/ontostart/testo/docs/ontospy/index.html) · [pyLODE](https://micheldumontier.github.io/ontostart/testo/docs/pylode/index.html) |
| License | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0) |
| Imports | [SULO](https://w3id.org/sulo/) |
| Source | [`testo.ttl`](https://github.com/micheldumontier/ontostart/blob/testo/testo.ttl) on the `testo` branch |

## Get the ontology

The IRI resolves to the website in a browser, and to the ontology file when you ask for an RDF format:

```
curl -L -H "Accept: text/turtle" https://w3id.org/ontostart/testo/
curl -L -H "Accept: application/rdf+xml" https://w3id.org/ontostart/testo/
curl -L -H "Accept: application/ld+json" https://w3id.org/ontostart/testo/
curl -L -H "Accept: application/n-triples" https://w3id.org/ontostart/testo/
```

## Making changes

Edit `testo.ttl` on this branch and push. The [branch CI](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml) then:

1. checks the OWL 2 DL profile and consistency (ROBOT with HermiT),
2. bumps the patch version and commits it, with the Turtle, RDF/XML, JSON-LD and N-Triples files under `versions/`,
3. regenerates the OntoSpy and pyLODE documentation and the FOOPS! FAIRness report,
4. publishes everything to the [website](https://micheldumontier.github.io/ontostart/testo/).

Don't edit `versions/` by hand: CI writes it.

## About OntoStart

This ontology is published with [OntoStart](https://github.com/micheldumontier/ontostart), a template for publishing FAIR OWL ontologies with w3id.org IRIs and GitHub Actions. Each branch of the repository holds one ontology. See the [`main` branch](https://github.com/micheldumontier/ontostart/tree/main#readme) to set up your own.
