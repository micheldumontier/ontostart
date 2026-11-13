# Publishing a sandbox ontology

This is how a student publishes a tutorial ontology with OntoStart. You need a text editor or Protégé, and git.

## With write access to the repository

```
git fetch origin
git switch -c sandbox/<name> origin/main
cp -r sandbox/testo sandbox/<name>
rm -rf sandbox/<name>/versions       # CI regenerates it
mv sandbox/<name>/testo.ttl sandbox/<name>/<name>.ttl
sed -i 's#sandbox/testo/#sandbox/<name>/#g' sandbox/<name>/<name>.ttl
git add sandbox/<name>
git commit -m "Add sandbox ontology <name>"
git push -u origin sandbox/<name>
```

Edit `sandbox/<name>/README.md` too, or delete it. Pick `<name>` with lowercase letters, digits and hyphens only (`^[a-z0-9][a-z0-9-]*$`); it must not be `sandbox`, `versions`, `docs`, `catalog` or `main`. On macOS use `sed -i ''` instead of `sed -i`. Then edit `<name>.ttl`: the ontology IRI must be `https://w3id.org/ontostart/sandbox/<name>/`, and you should replace the title, description, creator and other metadata. Replace the `testo:` prefix IRI as well; the `sed` command above does both.

Each push to `sandbox/<name>` runs CI, which bumps the version, commits it back to your branch (pull before you push again), and publishes.

## Without write access

Fork the repository, add the folder `sandbox/<name>/` with `<name>.ttl` as above, and open a pull request. CI checks your ontology on the pull request but does not publish it. It is published when the pull request is merged into `main`.

## What you will see

* The page: `https://micheldumontier.github.io/ontostart/sandbox/<name>/`, with the sandbox banner, downloads in four syntaxes, documentation and the version list.
* The ontology IRI: `https://w3id.org/ontostart/sandbox/<name>/`. It only resolves after the w3id.org redirect update has been merged. Until then, use the GitHub Pages URL above.

## What blocks a publish

CI refuses to publish, and the run fails, when:

* the ontology is not in the OWL 2 DL profile,
* the ontology is inconsistent (HermiT) or reasoning errors,
* the ontology IRI is not `https://w3id.org/ontostart/sandbox/<name>/` (check that you replaced `sandbox/testo/`).

Unsatisfiable classes alone do not block, but they are worth fixing. Read the failing step in the run log under the Actions tab for the reason.

## Lifetime

Sandbox ontologies are not persistent. They may be removed at the end of a term, so do not depend on a sandbox IRI from anything you want to keep.
