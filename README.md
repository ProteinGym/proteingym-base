# pg2 dataset
## schema
``` mermaid
classDiagram
    class ModelMeta{
        hyper_parameters: list[HyperParameter]
        train_entrypoint: Path | None
        predict_entrypoint: Path
        input_modalities: list[enum[MSA, Structure, Assay]]
        higher_is_better: bool
        support_multi_target: bool
        license: str
    }
    class ValueWithUncertainty{
        value: ValueWithUnit
        uncertainty: PositiveFloat
    }
    class Dataset{
        +name: str
        +taxon: NCBITaxon
        +description: str
        +doi: Uri
        +source: Uri
        +uniprot: str
        +xrefs: list[CrossReference]
        +assays: list[Assays]
        +structures: StructuresDataset
        +alphabet: SequenceAlphabet
        +reference_sequences: list[str]
        +licence: str
        +msa: MSA
        +save()
        +load()
    }
    class Record{
      +sequence: str
      +$key: float|str
      +value: ValueWithUncertainty
    }
    class Assay{
        +name: str
        +target_name: str
        +file_path: Path
        +description: str
        +data: pl.DataFrame[Record]
        +conditions: dict[str, NumericalOrCategorical]
        +selection_assay: str
        +selection_type: str
        +higher_is_better: bool
        +value_unit: str
        +engineering_round: int
        +assay_type: enum[OrgnismalFitness, Activity, Stability, Expression, Binding]
    }
    class MSA{
        +file_path: Path
        +msa: Biotite|Biopython|..
        +weights: np.array
        +range: tuple[int, int]
        +bitscore: float
        +theta: float
        +coverage: percent
        +n_eff: float
        +neff_l: float
        +neff_l_category: enum[Medium, Low, High]
        +num_significant: int
        +num_significant_l: float
    }
    class StructuresDataset{
        +structures: list[Structure]
        +splits: dict[tuple[Round, Sequence, SplitStrategy], enum[Train, Valid, Test]]
        +add_split(strategy: Callable) None
        +train() tuple[X, Y]
        +valid() tuple[X, Y]
        +test() tuple[X, Y]
    }
    class Structure{
        +structure: Biotite|Biopython
        +file_path: Path
        +range: tuple[int, int]
    }
    Dataset <|-- Assay
    Dataset <|-- StructuresDataset
    Dataset <|-- MSA
    StructuresDataset <|-- Structure
    Assay <|-- Record
    Record <|-- ValueWithUncertainty
```

[Meta data on assays in PG1](https://raw.githubusercontent.com/OATML-Markslab/ProteinGym/refs/heads/main/reference_files/DMS_substitutions.csv)


[Meta data on models in PG1](https://github.com/OATML-Markslab/ProteinGym/blob/main/config.json)

Track only non-redundant information E.g.,

- Can use [taxoniq](https://pypi.org/project/taxoniq/) to grab details about organism
- Can use [doi2bib](https://github.com/bibcure/doi2bib) to grab details about articles
- Can use [uniprot mapper](https://github.com/David-Araripe/UniProtMapper) to grab details about reference sequence
- Sequence-length, MSA length etc, are computed fields

## Getting Started

You can load the dataset as below, then go ahead to use it to train a model:

```python
from pg2_dataset.dataset import Dataset

ds = Dataset.from_toml("example_data/dataset.toml")

# load records
records = ds.assays.records

# load structure
structure = ds.structure
```

## Develop Locally

after the following commands, you are good to go:
```
uv sync
source .venv/bin/activate

pre-commit install
```

## Test Locally

```shell
uv run pytest
```

## Play Around

```shell
uv run jupyter lab
```
