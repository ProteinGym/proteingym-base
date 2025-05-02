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

```
from pg2_dataset.datasets.csv import CSVDataset

ds = CSVDataset(
    file_path="https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv",
    features=["mutated_sequence"],
    targets=["DMS_score"],
    train_size=10,
    test_size=2,
)

print(ds.train[0])
print(ds.train[0].pg2_split)
print(ds.train[0].pg2_uuid)

print(ds.test[0])
print(ds.test[0].pg2_split)
print(ds.test[0].pg2_uuid)
```

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
