# My ontology collection

A collection of ontologies published with [OntoStart](https://github.com/micheldumontier/ontostart): checks, versioned files, documentation and w3id.org IRIs, built by GitHub Actions.

## Set up

1. Click **Use this template** to create your repository.
2. In a clone of it (you need `git` and [uv](https://docs.astral.sh/uv/)), run init with the w3id.org name you want (lower case letters, digits and `-`), your GitHub account and the repository name:

   ```
   uvx --from git+https://github.com/micheldumontier/ontostart@v1.6 ontostart init --w3id NAME --owner OWNER --repo REPO
   ```

   This fills in `ontostart.yaml`, the example ontology's IRIs, `.github/workflows/w3id-pr.yml`, and writes `apache/web/NAME/.htaccess` and `README.md`.
3. Commit and push to `main`. The first run builds the example ontology and creates the `gh-pages` branch.
4. Enable Pages: Settings > Pages > Deploy from branch, `gh-pages`, `/ (root)`.
5. Create the environment `ontostart-secrets` (Settings > Environments), limited to the `main` branch, with these secrets:
   * `W3ID_TOKEN`: a classic personal access token with scopes `repo`, `read:org` and `workflow`.
   * `GIST_TOKEN` (optional, for badges): a fine-grained token with Gists read and write. Also put the gist's id in `gist_id` in `ontostart.yaml`.
6. Run the workflow **Propose w3id.org redirects** from the Actions tab. It opens a pull request on [perma-id/w3id.org](https://github.com/perma-id/w3id.org) for `https://w3id.org/NAME/`.

## Add an ontology

Create `ontologies/<name>/<name>.ttl` with the IRI `https://w3id.org/NAME/<name>/` and push. Settings per ontology (such as `status: experimental`) go under `ontologies:` in `ontostart.yaml`. Then run **Propose w3id.org redirects** again if you changed `ontostart.yaml`.

## Upgrade the engine

The workflows run a fixed release of OntoStart, so your published ontologies change only when this repository changes. To take a newer release (see [Engine releases](https://github.com/micheldumontier/ontostart#engine-releases)), replace the version, such as `v1.6`, in four lines: `uses:` and `engine-ref:` in both `.github/workflows/ontostart.yml` and `.github/workflows/w3id-pr.yml`. Commit and push; the next change to an ontology or to `ontostart.yaml` builds with it.
