# Publishing a sandbox ontology

This is how a student publishes a tutorial ontology with OntoStart. You need a text editor or Protégé, git and perl (preinstalled on macOS and Linux).

Pick `<name>` with lowercase letters, digits and hyphens only (`^[a-z0-9][a-z0-9-]*$`), starting with a letter so it also works as a Turtle prefix; it must not be `sandbox`, `versions`, `docs`, `catalog` or `main`.

## Make your folder

In a clone of the repository (see the two routes below for which clone and branch):

```
cp -r sandbox/testo sandbox/<name>
rm -rf sandbox/<name>/versions       # CI regenerates it
mv sandbox/<name>/testo.ttl sandbox/<name>/<name>.ttl
perl -pi -e 's/\btesto\b/<name>/g' sandbox/<name>/<name>.ttl
```

The `perl` command replaces every lowercase word `testo` in `<name>.ttl` with `<name>`: the IRIs (`https://w3id.org/ontostart/sandbox/testo/` becomes `https://w3id.org/ontostart/sandbox/<name>/`), the file name in URLs (`testo.ttl` becomes `<name>.ttl`), the `testo:` prefix, `vann:preferredNamespacePrefix "testo"` and the LOV link. It works the same on macOS and Linux. Then edit `<name>.ttl` by hand: replace the title, label, description, `dcterms:alternative "TESTO"`, creator and other metadata. The ontology IRI must be `https://w3id.org/ontostart/sandbox/<name>/`. Edit `sandbox/<name>/README.md` too, or delete it.

Your copy still has testo's `owl:versionInfo "0.0.1"`, and CI bumps the patch version when it publishes, so the first published version of your ontology is 0.0.2.

## Default: fork and pull request

1. Fork `micheldumontier/ontostart` on GitHub and clone your fork.
2. Make your folder on a new branch:

   ```
   git switch -c add-<name>
   # the commands under "Make your folder"
   git add sandbox/<name>
   git commit -m "Add sandbox ontology <name>"
   git push -u origin add-<name>
   ```

3. Open a pull request against `main` of `micheldumontier/ontostart`.

CI checks your ontology on the pull request but does not publish it; a red check means it would be blocked (see below). Push more commits to the same branch to fix it. It is published when the pull request is merged into `main`.

## A sandbox branch (for students you trust with write access)

> **Warning.** Write access lets a student run workflows: anyone who can push a branch can push a modified workflow and run it, and that run can read every repository secret. Give write access only to students you trust, and keep the repository's tokens (`W3ID_TOKEN`, `GIST_TOKEN`) as secrets of the `ontostart-secrets` environment whose deployment branches are limited to `main`, never as repository secrets (see "Secrets and variables" in the [README](../README.md)).

```
git fetch origin
git switch -c sandbox/<name> origin/main
# the commands under "Make your folder"
git add sandbox/<name>
git commit -m "Add sandbox ontology <name>"
git push -u origin sandbox/<name>
```

Each push to `sandbox/<name>` runs CI, which bumps the version, commits it back to your branch (pull before you push again), and publishes. Runs on sandbox branches push no badges.

## What you will see

* The page: `https://micheldumontier.github.io/ontostart/sandbox/<name>/`, with the sandbox banner, downloads in four syntaxes, documentation and the version list.
* The ontology IRI: `https://w3id.org/ontostart/sandbox/<name>/`. It only resolves after the w3id.org redirect update has been merged. Until then, use the GitHub Pages URL above.

## What blocks a publish

CI refuses to publish, and the run fails, when:

* the file cannot be parsed (a Turtle syntax error; the message gives the line),
* the ontology IRI is not `https://w3id.org/ontostart/sandbox/<name>/` (check that the `perl` command ran),
* the ontology is not in the OWL 2 DL profile,
* the ontology is inconsistent (HermiT) or reasoning errors.

Unsatisfiable classes alone do not block, but they are worth fixing. The reason is shown in the run's summary under the Actions tab, with ROBOT's explanation for an inconsistent ontology; the full ROBOT output is in the "Check" step of the build job (expand the "ROBOT … output" groups) and in the run's `ontology-sandbox-<name>` artifact.

## Lifetime

Sandbox ontologies are not persistent. They may be removed at the end of a term, so do not depend on a sandbox IRI from anything you want to keep.
