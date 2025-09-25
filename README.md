# Protein Gym Dataset

[![codecov](https://codecov.io/gh/ProteinGym/proteingym-base/graph/badge.svg?token=RQ9KX7UPL0)](https://codecov.io/gh/ProteinGym/proteingym-base)

A standardisation for using protein data within protein gym.

- [Protein Gym Dataset](#protein-gym-dataset)
  - [Project Structure](#project-structure)
  - [Dataset Manifest](#dataset-manifest)
  - [Installation](#installation)
  - [Quickstart example](#quickstart-example)
    - [Load data](#load-data)
    - [Archive data](#archive-data)
      - [Load archived data](#load-archived-data)
    - [Access protein data](#access-protein-data)
      - [Multiple Sequence Alignment (MSA)](#multiple-sequence-alignment-msa)
    - [Example Data](#example-data)

## Project Structure

``` tree
├── docs                       <-- Folder with documentation
│   ├── decisions/             <-- Architecture decision records
│   └── *.md                   <-- Other documentation files
├── example_data/              <-- Example data folder
│   ├── NEIME_2019/            <-- NEIME 2019 dataset
│   └── neime_2019.toml        <-- NEIME 2019 manifest file
├── notebooks/                 <-- Jupyter notebooks
│   └── *.ipynb                <-- Demonstration notebooks
├── src/                       <-- Source code folder
│   └── pg2_dataset/           <-- Main package
├── tests/                     <-- Test folder
│   └── test_*.py              <-- Test files
├── .adr-dir                   <-- Architecture decision records folder
├── .gitignore                 <-- Git ignore file
├── .pre-commit-config.yaml    <-- Pre-commit configuration file
├── .python-version            <-- Python version file
├── CONTRIBUTING.md            <-- Contribution guide
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
>>> from pg2_dataset import Dataset, Manifest
>>> manifest = Manifest.from_path("example_data/neime_2019.toml")
>>> manifest.name
'NEIME_2019'
>>> dataset = Dataset.from_manifest(manifest)
>>> len(dataset.assays) > 0 and len(dataset.structures) > 0
True

```

This wil gather data from the locations specified in the manifest into a single
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

### Access protein data

The `Dataset` object provides access to the protein data:
- Assays
- Sequences
- Structures
- MSAs (Multiple Sequence Alignments)

#### Multiple Sequence Alignment (MSA)

When loading MSA, [biotite](https://www.biotite-python.org/latest/index.html) is
required to be installed: `uv sync --extra biotite`.

> [!CAUTION]
> Biotite only supports loading from fasta. So any aligment outside the fasta format (ending with .fa or .fasta) will throw an error.

When loading MSA data, configure the following section in the toml:

```toml
[[ msas ]]
path = "example_data/v2/A0A1I9GEU1_NEIME_Kennouche_2019/msa.fasta"
format = "fasta"
```

[biotite get the alignment](https://www.biotite-python.org/latest/apidoc/biotite.sequence.io.fasta.get_alignment.html)
as an [`Alignment` object](https://biopython.org/docs/latest/api/Bio.AlignIO.html):

```python
>>> from Bio.Align import Alignment, MultipleSeqAlignment
>>> isinstance(dataset.msas[0].value, MultipleSeqAlignment)  # The first MSA in the dataset
True

```

### Example Data

The NEIME Kennouche 2019 (UniProt id: A0A1I9GEU1) dataset is used as an example.
This dataset is stored in `example_data/NEIME_2019` and contains the following:

>[!CAUTION]
> AssayMeta and DatasetMeta are just examples of possible meta tags one might think of.
> Current information in there is not associated to the dataset at all and not obtained
> from official sources.

>[!CAUTION]
> In Assay.csv we also contain the split and engineer round column. 
> Engineering round is randomly allocated to 1, 2 or 3 for illustrative purposes.
> Orginal assay belongs to a single engineering round.
> Split column converted the fold_random_5 from a k-split to train/val/test split with kfolds 0, 1, 2 in train, 3 in val, 4 in test.

```shell
.
├── example_data
│   └── NEIME_2019
│       ├── A0A1I9GEU1.fasta        # Parent sequence
│       ├── AssayMeta.json          # Example of possible AssayMeta
│       ├── Assays                  
│       │   └── Assay.csv           # Tabular format of assay
│       ├── DataSetMeta.json        # Example of possible DatasetMeta
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

|      | Dataset name | Link to website    | Relative path to manifest                              |
| :--- | :----------- | :----------------- | :----------------------------------------------------- |
| 1.   | NEIME2019    | www.proteingym.org | [example_data/neime_2019.toml](example_data/neime_2019.toml) |
