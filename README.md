[![ontology CI](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml/badge.svg)](https://github.com/micheldumontier/ontostart/actions/workflows/branch.yml)

# OntoStart

OntoStart is a project to create FAIR (Findable, Accessible, Interoperable, and Reusable) OWL ontologies through predefined GitHub Actions.

Features
* w3id.org persistent identifier for versioned ontologies
* content-type negotiation to get the ontology in different formats
* rich ontology metadata, as per the FAIR principles
* github actions to:
   * automatically setup w3id.org redirects
   * automatically increment the ontology version on commit
   * automatically check the consistency of the ontology using Robot with Hermit reasoner
   * automatically generate ontology documentation using OntoSpy and Pylode
   * automatically run FAIRness assessment using FOOPS!
   * automatically publish the website to github pages

See an [example](https://micheldumontier.github.io/ontostart/main/) processing of the Ontostart default ontology template.

Retrieve different syntaxes of the ontology with content-type negotiation
```
curl -L -H "Accept: text/turtle" https://w3id.org/ontostart/
curl -L -H "Accept: application/rdf+xml" https://w3id.org/ontostart/
curl -L -H "Accept: application/ld+json" https://w3id.org/ontostart/
curl -L -H "Accept: application/n-triples" https://w3id.org/ontostart/
```

Retrieve the latest or specific versions of the ontology
```
curl -L -H "Accept: text/turtle" https://w3id.org/ontostart/main/versions/latest/
curl -L -H "Accept: text/turtle" https://w3id.org/ontostart/main/versions/0.0.1/
```


## Getting Started
1. Devise a short name or acronym for the ontology. I'll use `myawesomeontology` as a short name for illustrative purposes. A lot of the automatic processing depends on this.

2. Fork and rename the repository with your short name. In doing so, it should be at `youruserororg/myawesomeontology`.

3. Rename `ontostart.ttl` to `myawesomeontology.ttl`, and update `ONTO_FILE` and `ONTO_ABBREV` at the top of `.github/workflows/main.yml` to match.

4. Modify the ontology metadata. I recommend using a tool such as VS Code or Protégé to make sure that you don't introduce syntax errors. In particular, replace the template placeholders:
   * the ontology IRI and prefix (`https://w3id.org/ontostart/`, `ontostart`)
   * the creator, contributor and author ORCIDs (`https://orcid.org/0000-0000-0000-0000`)
   * the publisher, homepage, citation, funding and license
   * the LOV catalog entry (`https://lov.linkeddata.es/dataset/lov/vocabs/replace_me`)

5. Set up GitHub Actions.

   1. Set up a public Gist that will store the information used to create the GitHub badges. From your GitHub user account (top right-hand corner), select 'Gists' on the menu. Create a new Gist (+ sign next to your user account). The content of the Gist can't be empty, so add a character. Create a public Gist: click on the drop-down list to the right of "Create secret gist" and pick "Create public gist". Copy the Gist ID (`gist:xxxxxxxx`) to the clipboard, without the `gist:` prefix. Now go to your forked repository's settings, select Actions under Secrets and variables, select Variables, and create a new repository variable called `GIST_ID`. Paste the Gist ID (without the `gist:` prefix) into the value field and click on Add variable.

   2. Set up two Personal Access Tokens (PATs): one for GitHub Actions to write the badge info to the Gist, and the second for a GitHub Action to make a pull request to the w3id.org repository. Go to your account, select Settings, then Developer settings, then Personal access tokens, then Tokens (classic).

      a. Create a classic PAT with the `gist` scope and store it as a secret named `GIST_TOKEN` in this repository. Generate a new token (classic) and name it "gists for ontostart badges". Choose a long expiration date. Check the "gist" box to give permission to create gists, then click on Generate token and copy it. Go to the repository settings, Secrets and variables, Actions, and create a new repository secret named `GIST_TOKEN`. Paste the PAT into the secret and click on Add secret.

      b. Create a classic PAT with the `repo` and `read:org` scopes and store it as a repository secret named `W3ID_TOKEN`.

   3. In the repository settings, under Pages, set the source to "Deploy from a branch" and select the `gh-pages` branch (`/` root). The workflows publish each branch's site into its own folder on that branch.

6. Customize a pull request to w3id.org.
   * Edit `apache/web/ontostart/README.md` to describe your ontology and add your contact info.
   * Edit `apache/web/ontostart/.htaccess` to change the owner and repository names.
   * Manually run the `Propose w3id.org redirects` GitHub Action. You can see the pull request at [https://github.com/perma-id/w3id.org/pulls](https://github.com/perma-id/w3id.org/pulls).
   * Once the w3id.org maintainers merge the pull request, your ontology IRI will be of the form `https://w3id.org/myawesomeontology/`.
