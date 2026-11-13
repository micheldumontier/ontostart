[![CI](https://github.com/micheldumontier/ontostart/actions/workflows/ontostart.yml/badge.svg?branch=main)](https://github.com/micheldumontier/ontostart/actions/workflows/ontostart.yml)
![Version](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-version-pro.json) ![OWL DL profile](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-profile-pro.json) ![Reasoning](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-reason-pro.json) ![FOOPS!](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-foops-pro.json)

# Process Roles Ontology (PRO)

A small SULO extension that defines reusable subclasses of sulo:Role (agent, patient, instrument, location, etc.) and sulo:Process (transformation, developmental, ...). PRO is intended to be imported by domain ontologies that need a finer-grained vocabulary for describing process participants.

PRO is imported by the [`pizza`](https://github.com/micheldumontier/ontostart/tree/main/ontologies/pizza) and [`suloized-pizza`](https://github.com/micheldumontier/ontostart/tree/main/ontologies/suloized-pizza) ontologies.

| | |
|---|---|
| IRI | <https://w3id.org/ontostart/pro/> |
| Prefix | `pro:` |
| Documentation | [Website](https://micheldumontier.github.io/ontostart/pro/) · [OntoSpy](https://micheldumontier.github.io/ontostart/pro/docs/ontospy/index.html) · [pyLODE](https://micheldumontier.github.io/ontostart/pro/docs/pylode/index.html) · [FOOPS! report](https://micheldumontier.github.io/ontostart/pro/foops/) |
| License | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Imports | [SULO](https://w3id.org/sulo) |
| Source | [`pro.ttl`](pro.ttl) in [`ontologies/pro/`](https://github.com/micheldumontier/ontostart/tree/main/ontologies/pro) |

## Get the ontology

The IRI resolves to the website in a browser, and to the ontology file when you ask for an RDF format:

```
curl -L -H "Accept: text/turtle" https://w3id.org/ontostart/pro/
curl -L -H "Accept: application/rdf+xml" https://w3id.org/ontostart/pro/
curl -L -H "Accept: application/ld+json" https://w3id.org/ontostart/pro/
curl -L -H "Accept: application/n-triples" https://w3id.org/ontostart/pro/
```

Each release has its own version IRI, for example `https://w3id.org/ontostart/pro/1.0.2`. All versions are listed on the [website](https://micheldumontier.github.io/ontostart/pro/).

Terms resolve too: <https://w3id.org/ontostart/pro/AgentRole> opens the term's documentation in a browser, and returns the ontology to RDF clients.

## Making changes

Edit `pro.ttl` on `main` (or a pull request) and push. The [CI](https://github.com/micheldumontier/ontostart/actions/workflows/ontostart.yml) then:

1. checks the OWL 2 DL profile and consistency (ROBOT with HermiT),
2. bumps the patch version and commits it, with the Turtle, RDF/XML, JSON-LD and N-Triples files under `versions/`,
3. regenerates the OntoSpy and pyLODE documentation and the FOOPS! FAIRness report,
4. publishes everything to the [website](https://micheldumontier.github.io/ontostart/pro/).

Don't edit `versions/` by hand: CI writes it.

## About OntoStart

This ontology is published with [OntoStart](https://github.com/micheldumontier/ontostart), a toolkit for publishing FAIR OWL ontologies with w3id.org IRIs and GitHub Actions. Each ontology lives in its own folder of the repository. See the [repository README](https://github.com/micheldumontier/ontostart/tree/main#readme) to set up your own.
