# Protein Gym Dataset

[![codecov](https://codecov.io/gh/ProteinGym2/pg2-dataset/graph/badge.svg?token=RQ9KX7UPL0)](https://codecov.io/gh/ProteinGym2/pg2-dataset)

A standardisation for using protein data within protein gym.

- [Protein Gym Dataset](#protein-gym-dataset)
  - [Dataset Manifest](#dataset-manifest)
  - [1.3. Getting Started](#13-getting-started)
    - [1.3.1. develop locally](#131-develop-locally)
    - [1.3.2. Load data](#132-load-data)
    - [1.3.3. loading from non-local](#133-loading-from-non-local)
    - [1.3.3. Persist data](#133-persist-data)
    - [1.3.3. Load persisted data](#133-load-persisted-data)
    - [1.3.4 Loading MSA data](#134-loading-msa-data)
  - [1.4. Engineering rounds](#14-engineering-rounds)
  - [1.5. Example Data](#15-example-data)
  - [1.6. Example Manifest](#16-example-manifest)
  - [1.7. Tutorials](#17-tutorials)

## Dataset Manifest

The dataset manifest is a configuration file that describes the dataset metadata
and assets:
- Assays
- Structures
- Sequences
- MSAs (Multiple Sequence Alignments)

The full schema of the manifest is described in the
[schema](./docs/manifest.md). Below example code uses the [NEIME 2019
dataset](./manifests/neime_2019.toml).


## 1.3. Getting Started
### 1.3.1. develop locally

after the following commands, you are good to go:
```
uv sync
source .venv/bin/activate

pre-commit install
```

to install all optional dependencies for Structures and MSA:
```
uv sync --all-extras
```

to test:
```shell
uv run pytest
```

to play around:
```
uv run jupyter lab
```

### 1.3.2. Load data

You can load the data using the manifest:

``` python
>>> from pg2_dataset import Dataset, Manifest
>>> manifest = Manifest.from_path("manifests/neime_2019.toml")
>>> manifest.name
'NEIME_2019'
>>> dataset = Dataset.from_manifest(manifest)
>>> dataset.assays is not None and dataset.structures is not None 
True

```

After loading the manifest, go ahead with using its data for model training or prediction.

### 1.3.3. loading from non-local

> [!CAUTION]
> This is probably out of date but good to include nonetheless. What is the current status on this?

You can load a data frame from either a DVC data registry, Google cloud storage starting with `gs://` or a relative path locally, we will add the support of S3 in the later release. 

As shown in the following example, the mandatory fields of records dataset are `features`, `targets` and `sequence_feature`. You can either use `records_file_path` or `toml_file` to configure the path to load the records:

```python
from pg2_dataset

#fill out example here.
```

### 1.3.3. Persist data

You can persist data in ProteinGym2's standardized archive format as follows

``` python
>>> archive_path = dataset.dump(path="example_data/")
>>> archive_path.is_file() and archive_path.stat().st_size > 0  # The archive contains the dataset
True

```

### 1.3.3. Load persisted data

You can quickly load the persisted data instead of re-ingesting it:

``` python
>>> persisted_dataset = Dataset.from_path(archive_path)  
>>> persisted_dataset.name
'NEIME_2019'
>>> archive_path.unlink()  # (FOR TESTING PURPOSES ONLY: remove the archive file for cleanup)

```

### 1.3.4 Loading MSA data

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
---

## 1.4. Engineering rounds

PG2 will support the concept of engineering rounds. When IFF develops new enzymes, we do iterative design where the target might change every round. E.g. if the goal is engineering a better enzyme X for cleaning stain Y, we usually reach the wanted Y performance in a few rounds with different targets in different rounds. In the first round we could try to achieve maximum stability, second round might be after expression in the biological host or a third round for getting the best cleaning performance on a specific stain Y. 

By supporting engineering rounds we allow for the easy modeling of methods where we can train on round 1, predict round 2 data, train round 1+2, predict round 3 data, etc. Or for benchmarking on older data and see if a tool would have been helpful along the round design.

## 1.5. Example Data

We use the NEIME Kennouche 2019 (UniProt id: A0A1I9GEU1) dataset as example.
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
│       ├── A0A1I9GEU1.fasta        #Parent sequence
│       ├── AssayMeta.json          #Example of possible AssayMeta
│       ├── Assays                  
│       │   └── Assay.csv           #Tabular format of assay
│       ├── DataSetMeta.json        #Example of possible DatasetMeta
│       ├── MSA
│       │   ├── msa_weights.npy     #weights file for MSA as obtained from PG1.
│       │   ├── msa.a2m             #MSA file in .a2m format
│       │   ├── msa.a3m             #MSA file in .a3m format
│       │   └── msa.psi             #MSA file in .psi format
│       └── Structures              #5 types of example structures with different
│           │                       #file types and sources for examples:
│           ├── experimental.cif
│           ├── experimental.bcif
│           ├── experimental.pdb
│           ├── computational.cif
│           └── computational.pdb
```

For a full overview of available data see the following table:

| | Dataset name | Link to website | Relative path to manifest |
| :--- | :--- | :--- | :--- |
| 1. | NEIME2019 | www.proteingym.org | [manifests/neime_2019.toml](manifests/neime_2019.toml) |

## 1.6. Example Manifest

We use the NEIME Kennouche 2019 (UniProt id: A0A1I9GEU1) dataset as example.
This manifest for this dataset is stored in `manifests/neime_2019.manifest` and contains the following:

```toml
name = "NEIME_2019"                                     # Name of the dataset

[assays_meta]                                           # Meta data of the assay
file_path = "example_data/NEIME_2019/Assays/Assay1.csv" # File path to Assay file
columns = ["mutated_sequence", "mutant", "DMS_score", "DMS_score_bin", "split", "engineering_round"] # Relevant columns to load
sequence_feature = "mutated_sequence"                   # Column of the sequence
split_feature="split"                                   # Column of the stored split information
engineering_round_feature="engineering_round"           # Column of the engineering round

[structures_meta]                                       # Meta data of the structures
file_path = "example_data/NEIME_2019/experimental.cif"  # Path to structure file or directory containing multiple files.

[assays_meta.assays.DMS_score]                          # Meta data of the DMS Score assay
```

## 1.7. Tutorials

>[!CAUTION]
> Should add section with tutorials here. E.g. pointing to the CI/CD notebooks.
