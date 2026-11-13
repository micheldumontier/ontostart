> **Sandbox.** This is the OntoStart example ontology, published in the sandbox. Sandbox IRIs are not persistent: it may change or be removed at any time. See [the classroom guide](../../docs/classroom.md) to publish your own.

[![CI](https://github.com/micheldumontier/ontostart/actions/workflows/ontostart.yml/badge.svg?branch=main)](https://github.com/micheldumontier/ontostart/actions/workflows/ontostart.yml)
![Version](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-version-sandbox-testo.json) ![OWL DL profile](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-profile-sandbox-testo.json) ![Reasoning](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-reason-sandbox-testo.json) ![FOOPS!](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-foops-sandbox-testo.json)

# Ontostart Test Ontology

The Ontostart Test Ontology.

A test ontology with no terms of its own. It exists to exercise the OntoStart CI and to serve as the template for new sandbox ontologies; it isn't meant for reuse.

| | |
|---|---|
| IRI | <https://w3id.org/ontostart/sandbox/testo/> |
| Prefix | `testo:` |
| Documentation | [Website](https://micheldumontier.github.io/ontostart/sandbox/testo/) · [OntoSpy](https://micheldumontier.github.io/ontostart/sandbox/testo/docs/ontospy/index.html) · [pyLODE](https://micheldumontier.github.io/ontostart/sandbox/testo/docs/pylode/index.html) |
| License | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0) |
| Imports | [SULO](https://w3id.org/sulo/) |
| Source | [`testo.ttl`](testo.ttl) in [`sandbox/testo/`](https://github.com/micheldumontier/ontostart/tree/main/sandbox/testo) |

## Get the ontology

The IRI resolves to the website in a browser, and to the ontology file when you ask for an RDF format:

```
curl -L -H "Accept: text/turtle" https://w3id.org/ontostart/sandbox/testo/
curl -L -H "Accept: application/rdf+xml" https://w3id.org/ontostart/sandbox/testo/
curl -L -H "Accept: application/ld+json" https://w3id.org/ontostart/sandbox/testo/
curl -L -H "Accept: application/n-triples" https://w3id.org/ontostart/sandbox/testo/
```

## Making changes

Edit `testo.ttl` on `main` (or a pull request) and push. The [CI](https://github.com/micheldumontier/ontostart/actions/workflows/ontostart.yml) then:

1. checks the OWL 2 DL profile and consistency (ROBOT with HermiT),
2. bumps the patch version and commits it, with the Turtle, RDF/XML, JSON-LD and N-Triples files under `versions/`,
3. regenerates the OntoSpy and pyLODE documentation and the FOOPS! FAIRness report,
4. publishes everything to the [website](https://micheldumontier.github.io/ontostart/sandbox/testo/).

Don't edit `versions/` by hand: CI writes it.

## About OntoStart

This ontology is published with [OntoStart](https://github.com/micheldumontier/ontostart), a toolkit for publishing FAIR OWL ontologies with w3id.org IRIs and GitHub Actions. Each ontology lives in its own folder of the repository. See the [repository README](https://github.com/micheldumontier/ontostart/tree/main#readme) to set up your own.
