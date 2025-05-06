# pg2 dataset
## schema

``` mermaid
classDiagram
    class ModelManifest{
        train_entrypoint: str|None
        predict_entrypoint: str
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
        +split(strategy: Callable)
        +data_frame_by_target(target: str)
        +data_frame()
    }
    Dataset <|-- Record
    class Record{
      +engineering_round: int
      +sequence: str
      +target_name: str
      +$key: float|str|MeasurementWithUncertainty
    }
    class AssayMeta{
        +target_name: str
        +features: dict[str, type]
        +description: str
        +$constant: any
    }
    Dataset <|-- AssayMeta
    Dataset <|-- DatasetMeta
    Record <|-- MeasurementWithUncertainty
    class DatasetMeta {
        +xref: CrossReference
    }
   
```

Validators

- Every $target_name should have a corresponding AssayMeta
- No missing values in records for listed features assay metadata for target
- ...

## develop locally

after the following commands, you are good to go:
```
uv sync
source .venv/bin/activate

pre-commit install
```

## a small example

We use [polars](https://github.com/pola-rs/polars) to load typed data frames. You can read [this reference](https://docs.pola.rs/user-guide/migration/pandas/) as to why Polars is chosen over Pandas.

You can load a data frame from either a DVC data registry, Google cloud storage starting with `gs://` or a relative path locally, we will add the support of S3 in the later release. As shown in the following example, the mandatory fields needed to load a CSV data frame are `file_path`, `features` (feature names of the data frame required for a model to train or predict) and `targets` (predictions from a model):

```python
from pg2_dataset.datasets.csv import CSVDataset

ds = CSVDataset(
    file_path="https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv",
    features=["mutated_sequence"],
    targets=["DMS_score"],
)

print(len(ds.data_frame))
print(ds.data_frame[0])
```

It is also recommended to load a data frames with its schema, as shown in the following example:

```python
import polars as pl
from pg2_dataset.backend.records import RecordsDataset

ds = RecordsDataset(
    file_path="https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv",
    features=["mutated_sequence"],
    targets=["DMS_score"],
    columns=["mutated_sequence", "mutant", "DMS_score", "DMS_score_bin"],
    schemas=[pl.String, pl.String, pl.Float32, pl.Int64]
)

print(len(ds.data_frame))
print(ds.data_frame[0])
```

Or if some columns are used for classification, you can do this:

```python
ds = RecordsDataset(
    file_path="https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv",
    features=["mutated_sequence"],
    targets=["DMS_score"],
    columns=["mutated_sequence", "mutant", "DMS_score", "DMS_score_bin"],
    schemas=[pl.String, pl.String, pl.Float32, pl.Categorical]
)
```

> [!TIP]
> You can find the polars data types to use in this guide: https://docs.pola.rs/api/python/stable/reference/datatypes.html

## play around

```shell
uv run jupyter lab
```

## test

```shell
uv run pytest
```

## todo

- [ ] add different split strategies from https://github.com/ProteinGym2/pg2-data/tree/main/src/pg2_data/split_strategy.
- [ ] refactor [Example.py](https://github.com/ProteinGym2/pg2-dataset/blob/main/src/pg2_dataset/primitives/example.py) with Pydantic model to do schema validation.
- [ ] use it in pg2-project as a common dependency to replace its "dataset.py" module, first in pg2-model-pls.
- [ ] use it in pg2 benchmarking, e.g., it can be in DVC.
