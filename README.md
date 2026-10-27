# ProteinGym Base

[![codecov](https://codecov.io/gh/ProteinGym/proteingym-base/graph/badge.svg?token=RQ9KX7UPL0)](https://codecov.io/gh/ProteinGym/proteingym-base)
[![CI pipeline](https://github.com/ProteinGym/proteingym-base/actions/workflows/ci.yaml/badge.svg)](https://github.com/ProteinGym/proteingym-base/actions/workflows/ci.yaml)

[ProteinGym](https://proteingym.org/) has become a widely used resource for comparing the ability of models to predict the effects of protein mutations. ProteinGym Base is an effort to bring more structure to the datasets so that they become easier to work with and to distribute; and to the models in the benchmark so that they become easier to install and run. Less undocumented csv's and more formal schemas. Fewer scripts with hardcoded paths and more Dockerfiles and precise requirements.

- [Project Structure](#project-structure)
- [Dataset Manifest](#dataset-manifest)
- [Installation](#installation)
- [Quickstart example](#quickstart-example)
  - [Load data](#load-data)
  - [Archive data](#archive-data)
  - [Access proteingym data](#access-proteingym-data)
  - [Splits](#splits)
  - [Metrics](#metrics)
- [Command line](#command-line)
- [Model cards](#model-cards)
- [Example Data](#example-data)
- [Related projects](#related-projects)

## Project Structure

``` tree
├── docs                       <-- Documentation, published with mkdocs
│   ├── decisions/             <-- Architecture decision records
│   ├── notebooks/             <-- Tutorial notebooks (executed in CI)
│   └── *.md                   <-- Other documentation files
├── example_data/              <-- Example data folder
│   ├── NEIME_2019/            <-- NEIME 2019 dataset
│   └── neime_2019.toml        <-- NEIME 2019 manifest file
├── src/                       <-- Source code folder
│   └── proteingym/            <-- Namespace package
│       └── base/              <-- Package
├── tests/                     <-- Test folder
│   └── test_*.py              <-- Test files
├── .adr-dir                   <-- Architecture decision records folder
├── .gitignore                 <-- Git ignore file
├── .pre-commit-config.yaml    <-- Pre-commit configuration file
├── .python-version            <-- Python version file
├── AGENTS.md                  <-- Guide for coding agents
├── CONTRIBUTING.md            <-- Contribution guide
├── mkdocs.yml                 <-- Documentation site configuration
├── pyproject.toml             <-- Project configuration file
├── README.md                  <-- This README file
└── uv.lock                    <-- Dependency lock file
```

## Dataset Manifest

The dataset manifest is a configuration file that describes the dataset metadata
and assets:
- Assays
- Structures
- Sequences
- MSAs (Multiple Sequence Alignments)

The full schema of the manifest is described in the
[schema](./docs/manifest.md). Below example code uses the [NEIME 2019
dataset](#example-data).

## Installation

To install the package, you can use pip:

```shell
$ pip install git+https://github.com/ProteinGym/proteingym-base.git
```

## Quickstart example

Below is a quickstart example of how to use this package.

### Load data

You can load the data using a [manifest](./docs/manifest.md) file. In the
example code below we load the [NEIME 2019](#example-data) dataset
[manifest](./example_data/neime_2019.toml):

``` python
>>> from proteingym.base import Dataset, Manifest
>>> manifest = Manifest.from_path("example_data/neime_2019.toml")
>>> manifest.name
'NEIME_2019'
>>> dataset = Dataset.from_manifest(manifest)
>>> len(dataset.assays) > 0 and len(dataset.structures) > 0
True

```

This will gather data from the locations specified in the manifest into a single
`Dataset` object. Go ahead with using its data for model training or prediction.

### Archive data

You can persist data in a Protein Gym archive for easy sharing and reloading.

``` python
>>> archive_path = dataset.dump(path="example_data/")
>>> archive_path.is_file() and archive_path.stat().st_size > 0  # The archive contains the dataset
True

```

#### Load archived data

You can quickly load the archived data:

``` python
>>> persisted_dataset = Dataset.from_path(archive_path)
>>> persisted_dataset.name
'NEIME_2019'
>>> archive_path.unlink()  # (FOR TESTING PURPOSES ONLY: remove the archive file for cleanup)

```

### Access proteingym data

The `Dataset` object provides access to the proteingym data:
- Assays
- Sequences
- Structures
- MSAs (Multiple Sequence Alignments)

#### Multiple Sequence Alignment (MSA)


When loading MSA data, add the following section in the toml:

```toml
[[ msas ]]
path = "./NEIME_2019/MSA/msa.a3m"
format = "a3m"
```

Paths are relative to the manifest file.

To get the MSA as [`MultipleSeqAlignment` object](https://biopython.org/docs/latest/api/Bio.AlignIO.html):

```python
>>> from proteingym.base import Manifest, Dataset
>>> mf = Manifest.from_path("example_data/neime_2019.toml")
>>> dataset = Dataset.from_manifest(mf)
>>> isinstance(dataset.msas[0].value, list)  # The first MSA in the dataset
True

```

### Splits

Data splits are stored as `Subsets`: a dataset plus named splits,
each made of folds. Splitters in `proteingym.base.splits` create them:

```python
>>> from proteingym.base import Subsets
>>> from proteingym.base.splits import RandomSplitter
>>> subsets = Subsets(dataset=dataset)
>>> subsets.update(random=RandomSplitter(fractions=[0.8, 0.1, 0.1]).split(dataset=dataset))
>>> list(subsets.slices)
['random']

```

`Subsets.dump` writes a `.splits.pgdata` archive and `Subsets.from_path` loads it.
See the [splitting tutorial](docs/notebooks/05_Creating_Dataset_Splits.ipynb) and
the [dataset archive](docs/dataset_archive.md) docs.

### Metrics

`proteingym.base.metrics` scores model predictions against a dataset or splits
(Spearman, top-k recovery, ...). See [metrics](docs/metrics.md).

## Command line

The package installs a `proteingym-base` CLI (run any command with `--help`):

| Command              | Purpose                                                                     |
|----------------------|-----------------------------------------------------------------------------|
| `build`              | Build a dataset archive from a manifest.                                    |
| `list-datasets`      | List the `.pgdata` archives in a folder as JSON.                            |
| `list-models`        | List the model cards in a folder as JSON.                                   |
| `validate`           | Validate a model project (its `pyproject.toml` entry points and model card) |
| `generate-data`      | Generate dummy data for testing.                                            |
| `evaluate-subset`    | Score predictions on cross-validation splits and write JSON.                |
| `evaluate-dataset`   | Score predictions on a plain dataset and write JSON.                        |
| `evaluate-zero-shot` | Score zero-shot predictions against the full dataset and write JSON.        |

> [!NOTE]
> `validate` finds the model's entry points among installed packages, so run it
> from the model's own environment, e.g. `cd my-model && uv run proteingym-base validate .`.

## Model cards

`proteingym.base.model.ModelCard` reads a model card: a `README.md` whose YAML
front matter holds the model `name`, `hyper_parameters` and any extra fields.
Model cards are used by the
[ProteinGym benchmark](https://github.com/ProteinGym/proteingym-benchmark).

## Example Data

The NEIME Kennouche 2019 (UniProt id: A0A1I9GEU1) dataset is used as an example.
This dataset is stored in `example_data/NEIME_2019` and contains the following:

>[!NOTE]
> AssayMeta and DatasetMeta are just examples of possible meta tags one might think of.
> Current information in there is not associated to the dataset at all and not obtained
> from official sources.

>[!NOTE]
> In Assay1.csv we also contain the split and engineering round column.
> Engineering round is randomly allocated to 1, 2 or 3 for illustrative purposes.
> Original assay belongs to a single engineering round.
> Split column converted the fold_random_5 from a k-split to train/val/test split with kfolds 0, 1, 2 in train, 3 in val, 4 in test.

```shell
.
├── example_data
│   └── NEIME_2019
│       ├── A0A1I9GEU1.fasta        # Parent sequence
│       ├── AssayMeta.json          # Example of possible AssayMeta
│       ├── Assays
│       │   └── Assay1.csv          # Tabular format of assay
│       ├── DataSetMeta.json        # Example of possible DatasetMeta
│       ├── sequences
│       │   └── A0A1I9GEU1.fasta    # Sequence referenced by the manifest
│       ├── MSA
│       │   ├── msa_weights.npy     # weights file for MSA as obtained from PG1.
│       │   ├── msa.a2m             # MSA file in .a2m format
│       │   ├── msa.a3m             # MSA file in .a3m format
│       │   └── msa.psi             # MSA file in .psi format
│       └── Structures              # 5 types of example structures with different
│           │                       # file types and sources for examples:
│           ├── experimental.cif
│           ├── experimental.bcif
│           ├── experimental.pdb
│           ├── computational.cif
│           └── computational.pdb
```

For a full overview of available data see the following table:

|    | Dataset name | Link to website    | Relative path to manifest                                    |
|:---|:-------------|:-------------------|:-------------------------------------------------------------|
| 1. | NEIME2019    | www.proteingym.org | [example_data/neime_2019.toml](example_data/neime_2019.toml) |

## Related projects

- [proteingym-benchmark](https://github.com/ProteinGym/proteingym-benchmark): the benchmark that consumes these datasets, model cards and metrics.
- [evedesign](https://github.com/evedesignbio/evedesign): the framework the benchmark models run on; `evedesign.proteingym` converts `Subsets` into evedesign datatypes.
