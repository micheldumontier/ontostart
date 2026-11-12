[![branch CI](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml/badge.svg?branch=pizza)](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml?query=branch%3Apizza)
![Version](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-version-pizza.json) ![OWL DL profile](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-profile-pizza.json) ![Reasoning](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-reason-pizza.json) ![FOOPS!](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-foops-pizza.json)

# SULO Pizza Tutorial Ontology

An OWL ontology for the pizza domain, built incrementally through the SULO Pizza Tutorial. Covers spatial composition, qualities, quantities, processes, information entities, time, and spatial containment.

For the community Pizza ontology rewritten into SULO automatically, see the [`suloized-pizza`](https://github.com/micheldumontier/ontostart/tree/suloized-pizza) branch.

| | |
|---|---|
| IRI | <https://w3id.org/ontostart/pizza/> |
| Prefix | `pizza:` |
| Documentation | [Website](https://micheldumontier.github.io/ontostart/pizza/) · [OntoSpy](https://micheldumontier.github.io/ontostart/pizza/docs/ontospy/index.html) · [pyLODE](https://micheldumontier.github.io/ontostart/pizza/docs/pylode/index.html) · [FOOPS! report](https://micheldumontier.github.io/ontostart/pizza/foops/) |
| License | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Imports | [PRO (the `pro` branch)](https://w3id.org/ontostart/pro)<br>[SULO](https://w3id.org/sulo) |
| Source | [`pizza.ttl`](https://github.com/micheldumontier/ontostart/blob/pizza/pizza.ttl) on the `pizza` branch |

## Get the ontology

The IRI resolves to the website in a browser, and to the ontology file when you ask for an RDF format:

```
curl -L -H "Accept: text/turtle" https://w3id.org/ontostart/pizza/
curl -L -H "Accept: application/rdf+xml" https://w3id.org/ontostart/pizza/
curl -L -H "Accept: application/ld+json" https://w3id.org/ontostart/pizza/
curl -L -H "Accept: application/n-triples" https://w3id.org/ontostart/pizza/
```

Each release has its own version IRI, for example `https://w3id.org/ontostart/pizza/1.0.1`. All versions are listed on the [website](https://micheldumontier.github.io/ontostart/pizza/).

Terms resolve too: <https://w3id.org/ontostart/pizza/BakingDuration> opens the term's documentation in a browser, and returns the ontology to RDF clients.

## Making changes

Edit `pizza.ttl` on this branch and push. The [branch CI](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml) then:

1. checks the OWL 2 DL profile and consistency (ROBOT with HermiT),
2. bumps the patch version and commits it, with the Turtle, RDF/XML, JSON-LD and N-Triples files under `versions/`,
3. regenerates the OntoSpy and pyLODE documentation and the FOOPS! FAIRness report,
4. publishes everything to the [website](https://micheldumontier.github.io/ontostart/pizza/).

Don't edit `versions/` by hand: CI writes it.

## About OntoStart

This ontology is published with [OntoStart](https://github.com/micheldumontier/ontostart), a template for publishing FAIR OWL ontologies with w3id.org IRIs and GitHub Actions. Each branch of the repository holds one ontology. See the [`main` branch](https://github.com/micheldumontier/ontostart/tree/main#readme) to set up your own.
