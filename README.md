# pg2 dataset

#### Table of Contents

[1. Schema Overview](#schema)
[2. Getting Started](#getting-started)
[3. Example Datasets](#example-data)

## schema

``` mermaid
classDiagram
    class ModelManifest{
        train_entrypoint: Path|None
        predict_entrypoint: Path
        train_artifacts: list[Artifact]
        hyper_parameters: list[HyperParameter]
    }
    class MeasurementWithUncertainty{
        value: float
        uncertainty: PositiveFloat
    }
    class Dataset{
        +records: list[Record]
        +structure: Structure
        +msa: MSA
        +alphabet: SequenceAlphabet
        +assay_meta: list[AssayMeta]
        +reference_sequences: list[str]
        +meta: DatasetMeta
        +splits: dict[tuple[Round, Sequence, SplitStrategy], TrainValidTestEnum]
        +add_split(strategy: Callable) None
        +data_frame_by_target(target: str) pd.DataFrame
        +data_frame() pd.DataFrame
        +iter_by_rounds() Generator[Dataset]
        +split() tuple[Dataset, Dataset, Dataset]
    }
    Dataset <|-- Record
    class Record{
      +engineering_round: int
      +sequence: str
      +$key: float|str|MeasurementWithUncertainty
    }
    class AssayMeta{
        +target: str
        +features: dict[str, type]
        +description: str
        +$constant: any
    }
    Dataset <|-- AssayMeta
    Dataset <|-- DatasetMeta
    Record <|-- MeasurementWithUncertainty
    class DatasetMeta {
        +doi: Uri
        +source: Uri
        +xref: CrossReference
    }
```

Validators

- Every $target should have a corresponding AssayMeta
- No missing values in records for listed features assay metadata for target
- ...

## getting started

### develop locally

after the following commands, you are good to go:
```
uv sync
source .venv/bin/activate

pre-commit install
```

to test:
```shell
uv run pytest
```

to play around:
```
uv run jupyter lab
```

### load dataset

You can just load the dataset as below, then go ahead with using it for model training or prediction:

```python
from pg2_dataset.dataset import Manifest

ds = Manifest.from_path("example_data/A0A1I9GEU1_NEIME_Kennouche_2019.toml").ingest()

# load records
records = ds.assays.records

# load structure
structure = ds.structure
```

### loading from non-local

> [!CAUTION]
> This is probably out of date but good to include nonetheless. What is the current status on this?

You can load a data frame from either a DVC data registry, Google cloud storage starting with `gs://` or a relative path locally, we will add the support of S3 in the later release. 

As shown in the following example, the mandatory fields of records dataset are `features`, `targets` and `sequence_feature`. You can either use `records_file_path` or `toml_file` to configure the path to load the records:

```python
from pg2_dataset

#fill out example here.
```

## Example Data

We use the NEIME Kennouche 2019 (UniProt id: A0A1I9GEU1) dataset for testing purposes.
This dataset is stored in `example_data/NEIME_2019` and contains the following:

>[!CAUTION]
> AssayMeta and DatasetMeta are just examples of possible meta tags one might think of.
> Current information in there is not associated to the dataset at all and not obtained
> from official sources.


>[!CAUTION]
> In Assay.csv we also contain the split and engineer round column. 
> Engineering round is randomly allocated to 1, 2 or 3 for testing purposed.
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
│           │                       #file types and sources for testing:
│           ├── structure_experimental.cif
│           ├── structure_experimental.bcif
│           ├── structure.experimental.pdb
│           ├── structure_computational.cif
│           └── structure_computational.pdb
```


For a full overview of available data see the following table:

| Dataset name | Link to website | Relative path to manifest |
| :--- | :--- | :--- |
| NEIME2019 | www.proteingym.org | manifests/neime2019.toml |


