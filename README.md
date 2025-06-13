# pg2 dataset
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

You can load the dataset as below, then go ahead to use it to train a model:

```python
from pg2_dataset.dataset import Manifest

ds = Manifest.from_path("example_data/A0A1I9GEU1_NEIME_Kennouche_2019.toml").ingest()

# load records
records = ds.assays.records

# load structure
structure = ds.structure
```

## develop locally

after the following commands, you are good to go:
```
uv sync
source .venv/bin/activate

pre-commit install
```

## test locally

```shell
uv run pytest
```

## play around

```shell
uv run jupyter lab
```
