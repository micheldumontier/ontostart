[![branch CI](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml/badge.svg?branch=suloized-pizza)](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml?query=branch%3Asuloized-pizza)
![Version](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-version-suloized-pizza.json) ![OWL DL profile](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-profile-suloized-pizza.json) ![Reasoning](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-reason-suloized-pizza.json) ![FOOPS!](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/micheldumontier/9affe51b863c5144fa82d7b1d23449aa/raw/ontology-ci-foops-suloized-pizza.json)

# Suloized Pizza

The community Pizza ontology re-expressed in SULO-canonical form by ontointegrator. Object-property usages are rewritten to SULO relations (hasPart, hasFeature) with exact range guards, recursively through nested class expressions, and imported alongside SULO and PRO. Distinct from the SULO pizza tutorial ontology (https://w3id.org/ontostart/pizza).

Its classes keep their original co-ode.org IRIs (`http://www.co-ode.org/ontologies/pizza/pizza.owl#...`). For the pizza ontology built by hand in the SULO Pizza Tutorial, see the [`pizza`](https://github.com/micheldumontier/ontostart/tree/pizza) branch.

The source Pizza ontology (2.0.0, CC BY 3.0) is kept in [`imports/pizza.owl`](imports/pizza.owl), and [`catalog-v001.xml`](catalog-v001.xml) maps the import to it, so ROBOT and Protégé load it locally.

| | |
|---|---|
| IRI | <https://w3id.org/ontostart/suloized-pizza/> |
| Prefix | `suloized-pizza:` |
| Documentation | [Website](https://micheldumontier.github.io/ontostart/suloized-pizza/) · [OntoSpy](https://micheldumontier.github.io/ontostart/suloized-pizza/docs/ontospy/index.html) · [pyLODE](https://micheldumontier.github.io/ontostart/suloized-pizza/docs/pylode/index.html) · [FOOPS! report](https://micheldumontier.github.io/ontostart/suloized-pizza/foops/) |
| License | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Imports | [Pizza 2.0.0 (co-ode.org)](https://protege.stanford.edu/ontologies/pizza/pizza.owl)<br>[PRO (the `pro` branch)](https://w3id.org/ontostart/pro/)<br>[SULO](https://w3id.org/sulo) |
| Source | [`suloized-pizza.ttl`](https://github.com/micheldumontier/ontostart/blob/suloized-pizza/suloized-pizza.ttl) on the `suloized-pizza` branch |

## Get the ontology

The IRI resolves to the website in a browser, and to the ontology file when you ask for an RDF format:

```
curl -L -H "Accept: text/turtle" https://w3id.org/ontostart/suloized-pizza/
curl -L -H "Accept: application/rdf+xml" https://w3id.org/ontostart/suloized-pizza/
curl -L -H "Accept: application/ld+json" https://w3id.org/ontostart/suloized-pizza/
curl -L -H "Accept: application/n-triples" https://w3id.org/ontostart/suloized-pizza/
```

Each release has its own version IRI, for example `https://w3id.org/ontostart/suloized-pizza/0.0.1`. All versions are listed on the [website](https://micheldumontier.github.io/ontostart/suloized-pizza/).

## Making changes

Edit `suloized-pizza.ttl` on this branch and push. The [branch CI](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml) then:

1. checks the OWL 2 DL profile and consistency (ROBOT with HermiT),
2. bumps the patch version and commits it, with the Turtle, RDF/XML, JSON-LD and N-Triples files under `versions/`,
3. regenerates the OntoSpy and pyLODE documentation and the FOOPS! FAIRness report,
4. publishes everything to the [website](https://micheldumontier.github.io/ontostart/suloized-pizza/).

Don't edit `versions/` by hand: CI writes it.

## About OntoStart

This ontology is published with [OntoStart](https://github.com/micheldumontier/ontostart), a template for publishing FAIR OWL ontologies with w3id.org IRIs and GitHub Actions. Each branch of the repository holds one ontology. See the [`main` branch](https://github.com/micheldumontier/ontostart/tree/main#readme) to set up your own.
