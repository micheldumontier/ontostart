# My ontology collection

A collection of ontologies published with [OntoStart](https://github.com/micheldumontier/ontostart): checks, versioned files, documentation and w3id.org IRIs, built by GitHub Actions.

## Set up

1. Click **Use this template** to create your repository.
2. In a clone of it (you need `git` and [uv](https://docs.astral.sh/uv/)), run init with the w3id.org name you want (lower case letters, digits and `-`), your GitHub account and the repository name:

   ```
   uvx --from git+https://github.com/micheldumontier/ontostart@v1.10 ontostart init --w3id NAME --owner OWNER --repo REPO
   ```

   This fills in `ontostart.yaml`, the example ontology's IRIs, `.github/workflows/w3id-pr.yml`, and writes `apache/web/NAME/.htaccess` and `README.md`.
3. Commit and push to `main`. The first run builds the example ontology and creates the `gh-pages` branch.
4. Enable Pages: Settings > Pages > Deploy from branch, `gh-pages`, `/ (root)`.
5. Create the environment `ontostart-secrets` (Settings > Environments), limited to the `main` branch, with these secrets:
   * `W3ID_TOKEN`: a classic personal access token with scopes `repo`, `read:org` and `workflow`.
   * `GIST_TOKEN` (optional, for badges): a fine-grained token with Gists read and write. Also put the gist's id in `gist_id` in `ontostart.yaml`.
   * `ONTOEXPLORER_TOKEN` (optional, for OntoExplorer): an OntoExplorer API key with `write` scope. When set, each push to `main` registers or refreshes this collection's published ontologies in OntoExplorer. See [Publish to OntoExplorer](#publish-to-ontoexplorer).
6. Run the workflow **Propose w3id.org redirects** from the Actions tab. It opens a pull request on [perma-id/w3id.org](https://github.com/perma-id/w3id.org) for `https://w3id.org/NAME/`.

## Add an ontology

Create `ontologies/<name>/<name>.ttl` with the IRI `https://w3id.org/NAME/<name>/` and push. Settings per ontology (such as `status: experimental`) go under `ontologies:` in `ontostart.yaml`. Then run **Propose w3id.org redirects** again if you changed `ontostart.yaml`.

## Publish to OntoExplorer

[OntoExplorer](https://github.com/MaastrichtU-IDS/ontoexplorer) is a catalogue and quality observatory for ontologies. You can have each publish register this collection's ontologies there automatically, so OntoExplorer always holds your latest released versions.

It is **opt-in** and runs only on the `main` branch:

1. In OntoExplorer, sign in and (if you don't already have upload rights) request them. Then create an **API key with `write` scope** under **Dashboard → API keys**. Copy the key — it is shown only once.
2. Add it as a secret named **`ONTOEXPLORER_TOKEN`** to the `ontostart-secrets` environment (the same environment as `W3ID_TOKEN`, limited to `main`).

On each push to `main`, the build posts every published ontology's latest Turtle URL (`<pages>/<name>/versions/latest/<name>.ttl`) to OntoExplorer. OntoExplorer identifies an ontology by the IRI inside the document, so a known ontology is **refreshed** and a new one is **registered**, each owned by your account; every version still passes OntoExplorer's quality gate before it goes live. Registration is best-effort — a hiccup warns in the job log but never fails your build. Leaving `ONTOEXPLORER_TOKEN` unset disables it entirely.

By default the build targets the OntoExplorer **dev** deployment. To use a different host, pass `ontoexplorer-host:` under `with:` in `.github/workflows/ontostart.yml`.

## Upgrade the engine

The workflows run a fixed release of OntoStart, the `@vX.Y` in their `uses:` lines, so your published ontologies change only when this repository changes. When there is a new release (see [Engine releases](https://github.com/micheldumontier/ontostart#engine-releases)), Dependabot opens a pull request that changes those lines once the release is three days old, and CI checks every ontology with the new release on it. Merge it to republish your ontologies with the new release; their versions stay the same. Without Dependabot, change the `@vX.Y` in `.github/workflows/ontostart.yml` and `.github/workflows/w3id-pr.yml` yourself.
