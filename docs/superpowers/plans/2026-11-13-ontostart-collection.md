# OntoStart Collection, Engine and Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace one-ontology-per-branch with folders built by a versioned, reusable engine, add a sandbox for tutorial ontologies, and publish a template repository.

**Architecture:** A Python package `ontostart` (in this repo, `src/ontostart/`) holds all logic: config, target planning, versioning, reasoning classification, site and catalogue generation, badges, `.htaccess` rendering. Two reusable workflows (`build.yml`, `w3id-pr.yml`) call it; this repo and the template call those workflows. Content moves from branches into `ontologies/` and `sandbox/` folders on `main`, publishing to the same GitHub Pages paths so live IRIs keep working.

**Tech Stack:** Python 3.11, rdflib ≥ 7, PyYAML, pytest (via `uv`), GitHub Actions, ROBOT 1.9.8 / HermiT, OntoSpy (fork `micheldumontier/Ontospy`), pyLODE 3.1.0, Apache httpd 2.4 in Docker for redirect tests.

**Spec:** `docs/superpowers/specs/2026-11-13-ontostart-collection-design.md`

## Global Constraints

- Work on branch `restructure` from `main`. **Do not push it before Task 7's commit, which deletes `branch.yml`, `main.yml`, `drift-guard.yml`, `test.yml`** (otherwise `branch.yml` publishes a site for `restructure`).
- Names: `^[a-z0-9][a-z0-9-]*$`; reserved `sandbox versions docs catalog main` plus `aliases` keys.
- Ontology IRI of a target = `https://w3id.org/<w3id>/<path>/`; version IRI = that + `x.y.z`.
- Pages layout, `meta.json` fields, badge file names and kinds: exactly as in the spec's "Published layout".
- `.htaccess`: only `[R=303,L]` redirects, literal `https://` targets, no 301, no `%{REQUEST_URI}`/`%{HTTP_HOST}` in targets, no redirect to w3id.org; keeps `Header always set Access-Control-Allow-Origin "*"`, `Header always merge Vary "Accept"`, `Options -MultiViews`.
- One commit to the ref and one push to `gh-pages` per run; caller workflows set `concurrency: { group: ontostart-${{ github.ref }}, cancel-in-progress: false }`.
- No `${{ inputs.* }}` or `${{ github.event.* }}` inside `run:`; pass through `env:`.
- `robot.jar` v1.9.8 verified with `sha256sum -c` before use; invoked as `java -jar robot.jar`.
- Runtime package dependencies: `rdflib>=7`, `pyyaml` only. pyLODE and OntoSpy are installed by the workflow, not the package.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Outward-facing steps (pushing `main`, the w3id.org PR, creating the template repo, deleting branches) need Michel's go-ahead at that step.

## Review Focus

1. A student copies `testo.ttl` into `sandbox/alice/` and keeps testo's IRI → expect a blocked target whose error names the expected IRI (`test_bump_rejects_wrong_ontology_iri`, Task 2; `test_wrong_iri_blocks`, Task 3).
2. One push changes several folders → one commit back and one `gh-pages` push, not one per folder (`test_plan_multiple_changed_folders`, Task 1; Task 7 publish job design).
3. Folder named `Alice`, `main`, `catalog` or `testo` (an alias) → planning fails with the offending name (`test_invalid_and_reserved_names`, Task 1).
4. Branch `sandbox/alice` pushed without a `sandbox/alice/` folder, or `sandbox/a/b` → clear error, nothing published (`test_sandbox_branch_without_folder`, `test_nested_sandbox_branch`, Task 1).
5. Ontology without `owl:versionInfo`, or with a non-semver one → first bump yields `0.0.1` (`test_bump_without_version_info`, Task 2).

---

### Task 1: Package skeleton, config and target planning

**Files:**
- Create: `pyproject.toml`, `src/ontostart/__init__.py`, `src/ontostart/config.py`, `src/ontostart/targets.py`, `src/ontostart/cli.py`, `ontostart.yaml` (values from the spec), `tests/test_config.py`, `tests/test_targets.py`, `tests/conftest.py`

**Interfaces:**
- Produces:
  - `class ConfigError(Exception)`
  - `@dataclass(frozen=True) class OntologySettings: status: str | None = None; compare_unsatisfiable_with: str | None = None`
  - `@dataclass(frozen=True) class LegacyRoot: path: str; name: str`
  - `@dataclass(frozen=True) class Config: w3id: str; pages: str; gist_id: str; sandbox: bool; foops: bool; term_docs: str; aliases: dict[str, str]; legacy_root: LegacyRoot | None; ontologies: dict[str, OntologySettings]` (`pages` stored without trailing slash)
  - `load_config(path: Path) -> Config`
  - `@dataclass(frozen=True) class Target: name: str; path: str; folder: Path; file: Path; status: str; safe: str; base_iri: str; catalog: Path | None; compare_with: Path | None` with `to_json() -> dict` (paths as repo-relative strings)
  - `@dataclass(frozen=True) class Plan: targets: list[Target]; publish: bool; bump: bool`
  - `find_targets(root: Path, config: Config) -> list[Target]` (sorted by path)
  - `make_plan(root: Path, config: Config, ref: str, event: str, changed: list[str] | None, only: str | None = None, bump: bool | None = None) -> Plan`
  - CLI: `ontostart plan --ref REF --event EVENT [--changed-file FILE] [--only PATH] [--bump true|false]` prints `{"targets": [...], "publish": bool, "bump": bool}` on one line
  - `pyproject.toml`: `[project.scripts] ontostart = "ontostart.cli:main"`; `[dependency-groups] dev = ["pytest"]`; `requires-python = ">=3.11"`

- [ ] **Step 1: Write failing tests.** `conftest.py` provides a `repo` fixture building a temp tree with `ontostart.yaml` and folders `ontologies/pizza/pizza.ttl`, `ontologies/suloized-pizza/{suloized-pizza.ttl,catalog-v001.xml}`, `sandbox/testo/testo.ttl`.

```python
def test_load_config_defaults(repo):         # sandbox True, foops True, term_docs "ontospy", aliases {} when omitted
def test_load_config_rejects_missing_w3id(tmp_path)   # ConfigError mentioning "w3id"
def test_find_targets(repo):
    t = {x.path: x for x in find_targets(repo, load_config(repo / "ontostart.yaml"))}
    assert t["pizza"].base_iri == "https://w3id.org/ontostart/pizza/" and t["pizza"].status == "stable"
    assert t["sandbox/testo"].safe == "sandbox-testo" and t["sandbox/testo"].status == "sandbox"
    assert t["suloized-pizza"].status == "experimental"
    assert t["suloized-pizza"].catalog.name == "catalog-v001.xml"
    assert t["suloized-pizza"].compare_with == repo / "ontologies/suloized-pizza/imports/pizza.owl"
def test_invalid_and_reserved_names(repo):    # folders Alice, main, catalog, testo(alias) each -> ConfigError naming the folder
def test_folder_without_matching_file(repo):  # ontologies/x/ with only y.ttl -> ConfigError
def test_plan_main_push_changed_only(repo):   # changed ["ontologies/pizza/pizza.ttl"] -> targets ["pizza"], publish/bump True
def test_plan_multiple_changed_folders(repo): # pizza + sandbox/testo changed -> both targets in one Plan
def test_plan_config_change_builds_all(repo): # changed ["ontostart.yaml"] -> all targets
def test_plan_sandbox_branch(repo):           # ref "sandbox/testo", push -> ["sandbox/testo"] only, publish/bump True
def test_sandbox_branch_without_folder(repo)  # ref "sandbox/alice" -> ConfigError mentioning "sandbox/alice/alice.ttl"
def test_nested_sandbox_branch(repo)          # ref "sandbox/a/b" -> ConfigError
def test_plan_other_branch_and_pr(repo):      # ref "feature" push, and event "pull_request" -> publish False, bump False
def test_plan_dispatch(repo):                 # event "workflow_dispatch", changed None, only "pizza", bump False -> ["pizza"], publish True, bump False
def test_sandbox_disabled(repo):              # sandbox: false -> sandbox folders ignored, sandbox/* branch -> ConfigError
```

- [ ] **Step 2:** Run `uv run pytest tests/test_config.py tests/test_targets.py -q` → FAIL (import errors).
- [ ] **Step 3:** Implement `config.py`, `targets.py`, `cli.py` (argparse, subcommand `plan`) per the interfaces and the spec's "What CI does" table. `publish` is True only for `main` and `sandbox/<name>` refs on `push` or `workflow_dispatch`.
- [ ] **Step 4:** Run the same command → PASS.
- [ ] **Step 5:** Commit `feat(engine): config and target planning`.

### Task 2: Versioning and syntax variants

**Files:**
- Create: `src/ontostart/versioning.py`, `tests/test_versioning.py`, `tests/fixtures/minimal.ttl` (an `owl:Ontology` `https://w3id.org/ontostart/sandbox/testo/` with `owl:versionInfo "0.0.1"`, one class)
- Delete: `scripts/bump_version.py` (logic moves here)

**Interfaces:**
- Consumes: `Target` (Task 1)
- Produces:
  - `class OntologyIRIError(Exception)`
  - `current_version(file: Path, base_iri: str) -> str | None`
  - `bump_version(file: Path, base_iri: str, versions_dir: Path, now: datetime) -> str` (rewrites `file`; same triples as today's `scripts/bump_version.py`: versionIRI, versionInfo, created-if-missing, modified, issued, priorVersion + backwardCompatibleWith when `versions_dir/<old>/<name>.ttl` exists, name = `file.stem`)
  - `write_variants(file: Path, out_dir: Path, name: str) -> list[Path]` (ttl, jsonld, nt, owl as RDF/XML)
  - CLI: `ontostart version --target-json JSON [--bump]` prints the resulting version

- [ ] **Step 1: Write failing tests**

```python
def test_bump_patch(tmp_path):            # 0.0.1 -> "0.0.2"; versionIRI == base + "0.0.2"; exactly one versionInfo
def test_bump_links_prior_version(tmp_path)   # with versions/0.0.1/testo.ttl present -> priorVersion base+"0.0.1"
def test_bump_keeps_created(tmp_path)     # existing dcterms:created unchanged; modified == now
def test_bump_without_version_info(tmp_path)  # none -> "0.0.1"; "v2" (non-semver) -> "0.0.1"
def test_bump_rejects_wrong_ontology_iri(tmp_path):
    with pytest.raises(OntologyIRIError, match="https://w3id.org/ontostart/sandbox/alice/"): ...
def test_current_version(tmp_path)        # "0.0.1"; None when absent
def test_write_variants(tmp_path)         # 4 files named testo.{ttl,jsonld,nt,owl}; each parses to the same triple count
```

- [ ] **Step 2:** `uv run pytest tests/test_versioning.py -q` → FAIL.
- [ ] **Step 3:** Implement. `OntologyIRIError` message: `expected owl:Ontology <{base_iri}> in {file}; found: {found or 'none'}`.
- [ ] **Step 4:** Re-run → PASS.
- [ ] **Step 5:** Commit `feat(engine): versioning and syntax variants`.

### Task 3: Checks — profile, reasoning, blocking

**Files:**
- Create: `src/ontostart/checks.py`, `tests/test_checks.py`, `tests/fixtures/robot/{consistent,unsat1,unsat2,inconsistent,error}.txt` (captured ROBOT stdout+stderr; the unsat/inconsistent texts contain `There is 1 unsatisfiable class`, `There are 2 unsatisfiable classes`, `ontology is inconsistent`)

**Interfaces:**
- Consumes: `Target`, `OntologyIRIError`
- Produces:
  - `@dataclass(frozen=True) class ReasonResult: kind: Literal["consistent","unsatisfiable","inconsistent","error"]; unsatisfiable: int = 0` with properties `message` (`"consistent"`, `"2 unsatisfiable"`, `"inconsistent"`, `"error"`) and `color` (`brightgreen`, `orange`, `red`, `red`)
  - `classify_reasoning(exit_code: int, output: str) -> ReasonResult`
  - `@dataclass class CheckReport: profile_ok: bool; reason: ReasonResult; expected_unsatisfiable: int | None; iri_error: str | None; explanation: Path | None` with `blocked_reason() -> str | None` and `to_json()/from_json()`
  - `run_checks(target: Target, robot_jar: Path, workdir: Path) -> CheckReport` — runs `java -jar robot.jar [--catalog C] validate-profile --profile DL --input F`, `reason --reasoner HermiT`, `explain` (mode by result, writes `workdir/reason.explanation.md`); sets `iri_error` (the `OntologyIRIError` message) when the file has no `owl:Ontology` `target.base_iri`; when `compare_with` is set, also reasons over it and stores its count in `expected_unsatisfiable`
  - CLI: `ontostart check --target-json JSON --robot robot.jar --out report.json` (exit 0 even when blocked; blocking is decided in publish)

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.parametrize("fixture,code,kind,n", [("consistent",0,"consistent",0),("unsat1",1,"unsatisfiable",1),("unsat2",1,"unsatisfiable",2),("inconsistent",1,"inconsistent",0),("error",1,"error",0)])
def test_classify_reasoning(fixture, code, kind, n)
def test_blocked_reasons():   # profile fail -> "OWL DL profile"; inconsistent -> "inconsistent"; error -> "reasoning error"
def test_unsatisfiable_alone_not_blocked()      # stable, 2 unsat, expected None -> None
def test_compare_mismatch_blocks()              # 3 unsat, expected 2 -> "3 unsatisfiable classes, source has 2"
def test_wrong_iri_blocks()                     # iri_error set -> blocked_reason contains it
def test_report_json_roundtrip()
```

- [ ] **Step 2:** `uv run pytest tests/test_checks.py -q` → FAIL.
- [ ] **Step 3:** Implement. `run_checks` is exercised for real in Task 7's CI run, not in unit tests.
- [ ] **Step 4:** Re-run → PASS.
- [ ] **Step 5:** Commit `feat(engine): profile and reasoning checks with blocking rules`.

### Task 4: Site pages, FOOPS! report and badges

**Files:**
- Create: `src/ontostart/site.py`, `src/ontostart/foops.py`, `src/ontostart/badges.py`, `tests/test_site.py`, `tests/test_foops.py`, `tests/test_badges.py`, `tests/fixtures/foops.json` (two checks: 3/3 and 1/2)

**Interfaces:**
- Consumes: `Target`, `CheckReport`, `ReasonResult`, `write_variants`
- Produces:
  - `@dataclass(frozen=True) class SiteContext: repo: str; ref: str; server_url: str; badge_base: str; foops_enabled: bool`
  - `build_site(target: Target, version: str, out: Path, ctx: SiteContext) -> None` — writes `out/index.html`, `out/meta.json`, `out/versions/<v>/` and `out/versions/latest/` (copied from `target.folder/"versions"`), `out/<v>/index.html` per version. Page content as today's `branch.yml` "Generate default branch page" step, plus a status banner, and the Source link pointing at `{server_url}/{repo}/tree/{ref}/{folder}` and `/blob/{ref}/{file}`
  - Banner copy, exact: experimental → `Experimental: this ontology is generated or still changing, and may change without notice.`; sandbox → `Sandbox: a tutorial ontology. It is not persistent and may be removed.`
  - `@dataclass(frozen=True) class FoopsSummary: label: str; checks: list[dict]`; `summarize_foops(data: dict) -> FoopsSummary` (label format as today: `"{pct:.1f}% ({sum:.2f} in {n} tests)"`); `write_foops_page(summary: FoopsSummary | None, out: Path, title: str, iri: str) -> None` (all values HTML-escaped)
  - `badge_files(target: Target, report: CheckReport, version: str, steps: dict[str, bool], deployed: bool | None, foops: FoopsSummary | None) -> dict[str, dict]` — keys `ontology-ci-<kind>-<safe>.json`, values Shields endpoint JSON `{"schemaVersion":1,"label":...,"message":...,"color":...}`; labels as today (`OWL DL Profile`, `Reasoning`, `Version`, `ontospy`, `pylode`, `deploy`, `FOOPS!`)
  - `push_badges(gist_id: str, token: str, files: dict[str, dict]) -> None` — one `PATCH https://api.github.com/gists/{gist_id}` with all files (urllib, no new dependency)
  - CLI: `ontostart site --target-json JSON --version V --out DIR` and `ontostart badges --reports DIR --gist ID` (token from env `GIST_TOKEN`)

- [ ] **Step 1: Write failing tests**

```python
def test_index_has_title_description_and_source(tmp_path)   # dcterms:description under <h1>; tree link ends "/tree/main/ontologies/pizza"
def test_index_escapes_html(tmp_path)        # label "<b>x</b>" appears escaped
def test_status_banners(tmp_path)            # exact banner copy for experimental and sandbox; none for stable
def test_meta_json(tmp_path)                 # keys == {"name","path","status","title","description","iri","version","versions","modified"}; versions newest first
def test_version_landing_pages(tmp_path)     # out/0.0.1/index.html exists and links testo.ttl
def test_summarize_foops()                   # label == "75.0% (1.50 in 2 tests)"
def test_badge_files_names_and_colors()      # 7 keys for safe "sandbox-testo"; reason "2 unsatisfiable"/orange; foops omitted when None
def test_push_badges_single_request(monkeypatch)   # exactly one PATCH carrying every file
```

- [ ] **Step 2:** `uv run pytest tests/test_site.py tests/test_foops.py tests/test_badges.py -q` → FAIL.
- [ ] **Step 3:** Implement (string templates in the modules; no template engine).
- [ ] **Step 4:** Re-run → PASS.
- [ ] **Step 5:** Commit `feat(engine): site pages, FOOPS report and badges`.

### Task 5: Root catalogue

**Files:**
- Create: `src/ontostart/catalogue.py`, `tests/test_catalogue.py`

**Interfaces:**
- Consumes: `meta.json` written by `build_site`, `Config`
- Produces: `build_catalogue(site_root: Path, config: Config) -> None` — reads `*/meta.json` and `sandbox/*/meta.json`, writes `site_root/index.html` (sections "Ontologies", "Experimental", "Sandbox"; each entry links `<path>/`, shows title, version, description) and `site_root/catalog.{ttl,jsonld,nt,owl}` (a `dcat:Catalog` `https://w3id.org/<w3id>/` with one `dcat:Dataset` per stable/experimental ontology: `dcterms:title`, `dcterms:description`, `owl:versionInfo`, `dcat:landingPage`, and four `dcat:Distribution`s with `dcat:downloadURL` `{pages}/{path}/versions/latest/{name}.{ext}` and `dcat:mediaType`). CLI: `ontostart catalogue --site DIR`.

- [ ] **Step 1: Write failing tests**

```python
def test_catalogue_lists_sections(tmp_path)        # pizza under "Ontologies", suloized-pizza under "Experimental", sandbox/testo under "Sandbox"
def test_catalogue_ignores_dirs_without_meta(tmp_path)   # main/ and testo/ archives not listed
def test_dcat_excludes_sandbox(tmp_path)           # 2 dcat:Dataset; 8 dcat:Distribution; no sandbox IRI
def test_catalog_files_parse(tmp_path)             # four files, same triple count
```

- [ ] **Step 2:** `uv run pytest tests/test_catalogue.py -q` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Re-run → PASS.
- [ ] **Step 5:** Commit `feat(engine): root catalogue page and DCAT`.

### Task 6: Generated `.htaccess` and redirect tests

**Files:**
- Create: `src/ontostart/htaccess.py`, `src/ontostart/templates/htaccess.tmpl`, `tests/test_htaccess.py`
- Modify: `apache/web/ontostart/.htaccess` (regenerated), `apache/tests/redirects.tsv` (rewritten for the new layout), `apache/test-redirects.sh` (only if needed for nested paths)

**Interfaces:**
- Consumes: `Config`
- Produces: `render_htaccess(config: Config) -> str`; CLI `ontostart htaccess [--out PATH]` (default `apache/web/<w3id>/.htaccess`)

Rule order in the template (behavior pinned by the table below): parameters → content negotiation (unchanged from today's file) → aliases (rewrite the path internally, never redirect to w3id.org) → `/` and `/catalog.<ext>` and `/sandbox[/]` → legacy root `/x.y.z` → split into `B` (`<name>` or `sandbox/<name>`) and `REST` → `BONTO` (= last segment of `B`, or `legacy_root.name` when `B == legacy_root.path`) → today's per-ontology sub-rules unchanged → pass-through.

`redirects.tsv` must contain at least these rows (plus today's pizza/pro/suloized-pizza rows, which stay unchanged):

```
text/html	/	{pages}/	-
text/turtle	/	{pages}/catalog.ttl	-
application/ld+json	/catalog.jsonld	{pages}/catalog.jsonld	-
text/html	/sandbox	{pages}/	-
text/turtle	/0.0.2	{pages}/main/versions/0.0.2/ontostart.ttl	y
text/html	/0.0.2	{pages}/main/0.0.2/	y
text/turtle	/main/	{pages}/main/versions/latest/ontostart.ttl	y
text/turtle	/testo/	{pages}/sandbox/testo/versions/latest/testo.ttl	-
text/html	/testo/Pizza	{pages}/sandbox/testo/docs/ontospy/class-testoPizza.html	-
text/turtle	/sandbox/alice/	{pages}/sandbox/alice/versions/latest/alice.ttl	-
text/turtle	/sandbox/alice	{pages}/sandbox/alice/versions/latest/alice.ttl	-
text/html	/sandbox/alice/1.0.0	{pages}/sandbox/alice/1.0.0/	-
text/html	/sandbox/alice/hasPart	{pages}/sandbox/alice/docs/ontospy/prop-alicehasPart.html	-
text/turtle	/sandbox/alice/alice.owl	{pages}/sandbox/alice/versions/latest/alice.owl	-
text/turtle	/newonto	{pages}/newonto/versions/latest/newonto.ttl	-
```

(`-` rows switch to `y` in Task 8 once the targets exist.)

- [ ] **Step 1: Write failing tests**

```python
def test_render_matches_committed_file()   # render_htaccess(load_config("ontostart.yaml")) == Path("apache/web/ontostart/.htaccess").read_text()
def test_render_has_no_forbidden_constructs()   # no "R=301", "REQUEST_URI", "HTTP_HOST", "https://w3id.org" in any RewriteRule target
def test_render_lists_no_ontology_names()   # "pizza", "pro" absent from the rendered file
def test_alias_and_legacy_root_rendered()   # "testo" and "sandbox/testo" present; no legacy rule when legacy_root is None
```

- [ ] **Step 2:** Save the current table to the scratchpad as `redirects-pre-migration.tsv` (Task 8 uses it). `uv run pytest tests/test_htaccess.py -q` → FAIL; `bash apache/test-redirects.sh` → FAIL on the new rows.
- [ ] **Step 3:** Implement the template and renderer; run `uv run ontostart htaccess`.
- [ ] **Step 4:** `uv run pytest -q` → PASS; `bash apache/test-redirects.sh` → `N passed, 0 failed`.
- [ ] **Step 5:** Commit `feat(engine): generated .htaccess with sandbox, aliases and catalogue root`.

### Task 7: Reusable workflows replace the per-branch ones

**Files:**
- Create: `.github/workflows/build.yml` (`on: workflow_call`), `.github/workflows/ontostart.yml` (caller), `.github/workflows/engine-tests.yml`
- Modify: `.github/workflows/w3id-pr.yml` (add `workflow_call` with the same inputs; inputs via `env:`; regenerate with `ontostart htaccess` and fail if it differs from the committed file)
- Delete: `.github/workflows/branch.yml`, `main.yml`, `drift-guard.yml`, `test.yml`

**Interfaces:**
- Consumes: CLI commands from Tasks 1–6.
- Produces:
  - `build.yml` inputs: `engine-ref` (string, default `v1`), `only` (string, default `""`), `bump` (string `""|true|false`, default `""`); secrets: `GIST_TOKEN` (optional). Jobs:
    1. `plan` — checkout (fetch-depth 2), `pip install "git+https://github.com/micheldumontier/ontostart@${ENGINE_REF}"`, changed files from `git diff --name-only ${{ github.event.before }} HEAD` (passed via env; empty → all), `ontostart plan` → output `plan` JSON.
    2. `build` — `strategy.matrix.target: fromJSON(plan).targets`, `fail-fast: false`; Java 17, Python 3.11; robot.jar download + `sha256sum -c`; `ontostart check`; if `plan.bump`, `ontostart version --bump`; variants; OntoSpy (fork) and pyLODE into `site/docs/`; FOOPS! if enabled; `ontostart site`; upload artifact `ontology-<safe>` containing `site/`, `source/` (the bumped `.ttl` and new `versions/<v>/` under the target's folder path), `report.json`.
    3. `publish` — `needs: [plan, build]`, `if: always() && fromJSON(needs.plan.outputs.plan).publish` so it still runs when some targets fail. Downloads all artifacts; skips blocked targets (`blocked_reason()`); if `bump`, copies `source/` into the checkout and makes **one** commit `chore(ontology): bump <path>@<v>, ... [skip ci]`, push; checks out `gh-pages` into `gh-pages/`, `rsync -a --delete site/ gh-pages/<path>/` per target, `ontostart catalogue --site gh-pages`, **one** commit, push with one `git pull --rebase` retry; `ontostart badges`; finally `exit 1` listing blocked targets if any.
  - `ontostart.yml` (this repo): triggers `push` and `pull_request` on paths `ontologies/**`, `sandbox/**`, `ontostart.yaml`; `workflow_dispatch` inputs `only`, `bump` (boolean, default false); `concurrency` per ref; `uses: ./.github/workflows/build.yml` with `engine-ref: ${{ github.sha }}`; `permissions: contents: write`.
  - `engine-tests.yml`: on push/PR touching `src/**`, `tests/**`, `apache/**`, `pyproject.toml`: `uv run pytest -q` and `bash apache/test-redirects.sh`.
  - Third-party actions pinned by commit SHA (look up each tag's SHA with `gh api repos/<owner>/<action>/git/ref/tags/<tag>`).

- [ ] **Step 1:** Compute the pinned checksum: download `https://github.com/ontodev/robot/releases/download/v1.9.8/robot.jar` into a new empty scratch directory, `shasum -a 256` it, and put the value in `build.yml`. Do not run it.
- [ ] **Step 2:** Write the workflows; delete the four old ones in the same commit.
- [ ] **Step 3:** Lint: `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.7 -color` → no errors. Grep check: `grep -nE '\$\{\{ *(inputs|github\.event)\.' .github/workflows/*.yml` shows no matches inside `run:` blocks.
- [ ] **Step 4:** Commit `ci: reusable build workflow replaces per-branch workflows`. Push `restructure` and open a draft PR to `main` that touches `ontologies/pizza/` (Task 8 content may be cherry-picked early for this): `ontostart.yml` runs in check-only mode → `plan` shows `publish: false`, `build` passes for pizza, `publish` skipped. Engine tests green.

### Task 8: Migrate content to folders on `main` (go-ahead required before merging)

**Files:**
- Create: `ontologies/pizza/` (from `origin/pizza`: `pizza.ttl`, `versions/`, `README.md`), `ontologies/pro/`, `ontologies/suloized-pizza/` (+ `catalog-v001.xml`, `imports/pizza.owl`), `sandbox/testo/` (from `origin/testo`, IRIs rewritten from `https://w3id.org/ontostart/testo/` to `https://w3id.org/ontostart/sandbox/testo/` in `testo.ttl` only, not in `versions/`), `docs/classroom.md`
- Modify: `README.md` (collection + engine + template link + "Publishing a sandbox ontology"; W3ID_TOKEN scopes `repo`, `read:org`, `workflow`), per-ontology READMEs (branch links → folder links; testo README gets the sandbox notice)
- Delete: `ontostart.ttl`, `versions/` (root; already archived at `gh-pages/main/`), `scripts/`

`docs/classroom.md` steps for a student: `git switch -c sandbox/<name> origin/main` → copy `sandbox/testo/` to `sandbox/<name>/`, rename the file to `<name>.ttl`, replace `sandbox/testo/` with `sandbox/<name>/` in it → push → page at `https://w3id.org/ontostart/sandbox/<name>/`. Alternative for students without write access: fork, add the folder, open a PR.

- [ ] **Step 1:** Copy the content, then `uv run ontostart plan --ref main --event workflow_dispatch` → 4 targets with paths `pizza`, `pro`, `suloized-pizza`, `sandbox/testo`.
- [ ] **Step 2:** Push to the PR; CI check-only run → pizza, pro, testo `consistent`; suloized-pizza `2 unsatisfiable`, expected 2, not blocked.
- [ ] **Step 3:** **Ask Michel to approve the merge.** Squash-merge with `[skip ci]` in the message (so the merge doesn't bump every ontology), then `gh workflow run ontostart.yml --ref main -f bump=false`. Expect: 4 targets green, no commit to `main`, one `gh-pages` commit.
- [ ] **Step 4:** Verify live: `bash apache/test-redirects.sh --url https://w3id.org/ontostart --targets --table <scratchpad>/redirects-pre-migration.tsv` → 0 failed (old `.htaccess` still serves `/pizza/`, `/pro/`, `/suloized-pizza/`, `/testo/` (archive), `/`). Check `https://micheldumontier.github.io/ontostart/` shows the catalogue and `.../sandbox/testo/` shows the sandbox banner.
- [ ] **Step 5:** Smoke-test the sandbox branch flow: push `sandbox/ci-smoke` per `docs/classroom.md` → page at `{pages}/sandbox/ci-smoke/`; then delete the branch and `gh-pages/sandbox/ci-smoke/`.
- [ ] **Step 6:** `git tag v1 && git push origin v1`.

### Task 9: Propose the new `.htaccess` to w3id.org (go-ahead required)

**Files:** none in this repo (uses `w3id-pr.yml`).

- [ ] **Step 1:** Flip the `-` rows from Task 6 to `y` where the target now exists (catalogue, `sandbox/testo`); `bash apache/test-redirects.sh --targets` against local Apache → 0 failed. Commit.
- [ ] **Step 2:** Sync the fork: `gh repo sync micheldumontier/w3id.org --source perma-id/w3id.org --branch master`.
- [ ] **Step 3:** **Ask Michel**, then `gh workflow run w3id-pr.yml --ref main` with title `ontostart: catalogue root, sandbox namespace, folder layout` and a body listing: catalogue at `/`, `/sandbox/<name>/`, `/testo/` alias, legacy `/x.y.z`, no ontology list in the file, tested in httpd 2.4, checker run. Expect the run green and a PR URL.
- [ ] **Step 4:** After merge: `bash apache/test-redirects.sh --url https://w3id.org/ontostart --targets` → 0 failed (one WARN for `Vary`).

### Task 10: Template repository (go-ahead required before creating the repo)

**Files (engine, this repo):**
- Create: `src/ontostart/init.py`, `tests/test_init.py`, `template/` (the template's full content: `ontostart.yaml` with `w3id: CHANGEME`, `pages: https://OWNER.github.io/REPO`, `gist_id: ""`, `sandbox: false`, no aliases, no legacy_root; `ontologies/testo/` with IRIs `https://w3id.org/CHANGEME/testo/`; `.github/workflows/ontostart.yml`, identical to this repo's caller except `uses: micheldumontier/ontostart/.github/workflows/build.yml@v1` with `engine-ref: v1`; `.github/workflows/w3id-pr.yml` calling the reusable one; `README.md` with setup steps incl. PAT scopes `repo`, `read:org`, `workflow`)

**Interfaces:**
- Produces: `init_repo(root: Path, w3id: str, owner: str, repo: str, gist_id: str = "") -> list[Path]` — writes `ontostart.yaml`, replaces `https://w3id.org/CHANGEME/` with `https://w3id.org/<w3id>/` in `ontologies/**/*.ttl`, writes `apache/web/<w3id>/.htaccess` and its README; returns changed paths. Idempotent. CLI: `ontostart init --w3id NAME --owner OWNER --repo REPO [--gist ID]`.

- [ ] **Step 1: Write failing tests**

```python
def test_init_rewrites_iris(tmp_path)       # copy template/ ; after init no "CHANGEME" anywhere; testo IRI "https://w3id.org/myonto/testo/"
def test_init_is_idempotent(tmp_path)       # second run returns []
def test_init_rejects_bad_name(tmp_path)    # w3id "My Onto" -> ConfigError
def test_template_plan(tmp_path)            # after init, make_plan(...main, push, None) -> ["testo"]
```

- [ ] **Step 2:** `uv run pytest tests/test_init.py -q` → FAIL. **Step 3:** Implement. **Step 4:** PASS. Commit `feat(engine): ontostart init and template content`; tag `v1.1`.
- [ ] **Step 5:** **Ask Michel**, then create `micheldumontier/ontostart-template` from `template/` (`gh repo create --public`, push, `gh api -X PATCH repos/micheldumontier/ontostart-template -f is_template=true`).
- [ ] **Step 6:** End-to-end check: "Use this template" into a scratch repo, `ontostart init --w3id ontostart-demo ...`, push → build green, page on that repo's Pages. Delete the scratch repo afterwards (with Michel's go-ahead).

### Task 11: Retire the ontology branches (go-ahead required)

- [ ] **Step 1:** For each of `pizza pro testo suloized-pizza`: `git tag archive/<b> origin/<b>`; `git push origin archive/<b>`.
- [ ] **Step 2:** **Ask Michel**, then `git push origin --delete pizza pro testo suloized-pizza`.
- [ ] **Step 3:** Confirm nothing published from those branches is lost: `gh-pages/{pizza,pro,suloized-pizza}/` are rebuilt from folders; `gh-pages/testo/` and `gh-pages/main/` remain as archives. `bash apache/test-redirects.sh --url https://w3id.org/ontostart --targets` → 0 failed.
