# AGENTS.md

ProteinGym Base: the Python package (`proteingym.base`) that defines the ProteinGym2
dataset format (manifests, `.pgdata` archives, splits), model cards, metrics, and the
`proteingym-base` CLI. Read these before changing things:

- [README.md](README.md) – overview, quickstart, CLI, example data.
- [CONTRIBUTING.md](CONTRIBUTING.md) – setup, tests, CI checks, docs site, releases.
- [docs/manifest.md](docs/manifest.md) – manifest (TOML) schema.
- [docs/dataset_archive.md](docs/dataset_archive.md) – archive and splits archive layout.
- [docs/metrics.md](docs/metrics.md) – metrics API and how to add a metric.
- [docs/decisions/](docs/decisions/) – architecture decision records (historical context).
- [docs/notebooks/](docs/notebooks/) – tutorials, executed in CI.

## Key facts

- Source lives in `src/proteingym/base/`; public API is re-exported from `__init__.py`.
- Downstream users: [proteingym-benchmark](https://github.com/ProteinGym/proteingym-benchmark)
  (installs this package from `main` and calls the `evaluate-*` CLI commands) and
  [evedesign](https://github.com/evedesignbio/evedesign) (`evedesign.proteingym` converts
  `Subsets` into evedesign datatypes). Changes to the dataset format, `ModelCard`, metrics
  or CLI options can break them.
- Metrics are discovered automatically: any `metric_<name>(context)` function in
  `metrics.py` becomes metric `<name>`.
- Manifest sections are Pydantic models with `extra="forbid"`; when adding or renaming a
  field, update `docs/manifest.md`.

## Commands

```shell
uv sync --all-extras --dev       # install
uv run pytest                    # tests + README/docstring doctests (80% coverage gate)
uv run ruff check src tests && uv run ruff format --check src tests
uv run pyrefly check             # type check
uv run mkdocs serve              # docs site
```

Code examples in `docs/*.md` are not doctested; keep them in sync with the API by hand.
