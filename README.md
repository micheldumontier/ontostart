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
   * automatically run FAIRness asssessment using FOOPS!
   * automatically publish the website to github pages
 
See an [example](https://micheldumontier.github.io/ontostart/main/) processing of the Ontostart default ontology template.

## Getting Started 
1. Devise a short name or acronym for the ontology. I'll use `myawesomeontology` as a short name for illustrative purposes. A lot of the automatic processing depends on this.

2. Fork and rename the repository with your short name. In doing so, it should be at `youruserororg/myawesomeontology`

4. Rename `ontostart.ttl` to `myawesomeontology.ttl`. 

5. Modify the ontology metadata. I recommend to use a tool such as VScode or Protege to make sure that you don't introduce syntax errors.

6. Setup for GitHub Actions.
   i) Set up a Public Gist that will store the information to create the GitHub badges. From your github user account (top right hand corner), select 'Gists' on the menu. Create a new Gist (+ sign next to user account). The content of the gist can't be empty, so add a character. Create a Public Gist - click on the drop down list to the right of "Create a Secret Gist) and pick "Create Public Gist). Copy the Gist Id (gist:xxxxxxxx) to the clipboard, without the "gist" prefix.  Now go to your forked ontostart repo settings, select Actions under Secrets and Variables, select Variables, and Create a New Repository Variable called GIST_ID. Paste the gist Id (without the gist:) prefix into the value fiedl and click on Add Variable.
   ii) Set up two Personal Access Tokens (PAT), one for GitHub Actions to write the badge info to the Gist, and the second for a GitHub action to make a pull request to the w3id repo. Go to your account, select Settings, then Developer settings, then Personal Access Tokens, then Tokens (classic).
   a) Create a classic PAT with gist scope and store it as a secret named GIST_TOKEN in this repo. Generate a new token (classic) and name it "gists for ontostart badges". Choose a long term expiration date. Check the box "gists" to give permission to create gists. click on generate token. Copy the personal access token. Go to the repo settings, Secrets and Variables, and create a new repository secret. Create a new Repository Secret named GIST_TOKEN and paste the PAT to the Secret. Click on Add Secret.
   b) Create a classic PAT with repo scope and store it as a secret named W3ID_TOKEN in this repo.
   
* Customize a pull request to w3id.org.
  * Edit the `apache/web/README.md` file to describe your ontology and put in your contact info.
  * Manually run the `Propose w3id.org redirects` GitHub Action. You can see the pull request at [https://github.com/perma-id/w3id.org/pulls](https://github.com/perma-id/w3id.org/pulls)
  * It will take which will yield an ontology IRI of the form `https://w3id.org/myawesomeontology/`



