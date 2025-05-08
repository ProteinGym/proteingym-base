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
      +targets: list[str]
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

## develop locally

after the following commands, you are good to go:
```
uv sync
source .venv/bin/activate

pre-commit install
```

## structure example
```
from pg2_dataset.datatypes.structure import MMcifFile

mmcif = MMcifFile()
mmcif_data = mmcif.from_mmcif('example_data/A0A1I9GEU1_NEIME_Kennouche_2019/structure.cif')

x = mmcif_data.atom_site.cartn_x
y = mmcif_data.atom_site.cartn_y
z = mmcif_data.atom_site.cartn_z
atom_type = mmcif_data.atom_site.id

#do cool stuff with your structural data...
```

Every entry in an mmcif file should be accessible. 
Typically there are two types of entry: key-value pairs and tabular datas. 
To access key-value pairs (e.g. for `_citation.pdbx_database_id_DOI`) you can access it by writing out the full key, where each '.' and '-' is replace by '_':

```
mmcif_data.citation_pdbx_database_id_DOI
```

To get the full tabular data one can access this with the common table name, or further take only the column by the column name:
```
mmcif_data.atom_site # returns the complete table for atom_site
mmcif_data.atom_site.cartn_x # returns only the values for the cartn_x coordinates.
```

## sequence example

We use [polars](https://github.com/pola-rs/polars) to load typed data frames. You can read [this reference](https://docs.pola.rs/user-guide/migration/pandas/) as to why Polars is chosen over Pandas.

You can load a data frame from either a DVC data registry, Google cloud storage starting with `gs://` or a relative path locally, we will add the support of S3 in the later release. 

As shown in the following example, the mandatory fields of records dataset are `features`, `targets` and `sequence_feature`. You can either use `records_file_path` or `toml_file` to configure the path to load the records:

```python
from pg2_dataset.backends.records import RecordsDataset

ds = RecordsDataset(
    records_file_path="https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv",
    features=["mutated_sequence"],
    targets=["DMS_score"],
    sequence_feature="mutated_sequence",
)

print(ds.data_frame())
```

To initialize a dataset with a TOML file, you can try the test TOML file - [dataset.toml](example_data/dataset.toml):

```python
from pg2_dataset.backends.records import RecordsDataset

ds = RecordsDataset(
    toml_file="example_data/dataset.toml",
    features=["mutated_sequence"],
    targets=["DMS_score"],
    sequence_feature="mutated_sequence",
)

print(ds.data_frame())
```

We also recommend to load a data frame with its schema, as shown in the following example, so you will be aware of the schema further down the road:

```python
import polars as pl
from pg2_dataset.backends.records import RecordsDataset

ds = RecordsDataset(
    records_file_path="https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv",
    features=["mutated_sequence"],
    targets=["DMS_score"],
    sequence_feature="mutated_sequence",
    columns=["mutated_sequence", "mutant", "DMS_score", "DMS_score_bin"],
    schemas=[pl.String, pl.String, pl.Float32, pl.Float32],
)

print(ds.data_frame())
```

Above three examples all give the following result:
```
    mutant                                           sequence  DMS_score  DMS_score_bin                                                                  
0      F1I  ITLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...     -3.598            0.0
1      F1L  LTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...     -0.678            0.0
2      F1Y  YTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...     -2.373            0.0
3      F1V  VTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...      1.299            1.0
4      F1S  STLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...     -0.127            0.0
..     ...                                                ...        ...            ...
917  S161R  FTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...     -0.344            0.0
918  S161I  FTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...      1.472            1.0
919  S161G  FTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...      0.345            1.0
920  S161T  FTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...     -1.969            0.0
921  S161C  FTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSA...     -1.697            0.0

[922 rows x 4 columns]
```

Additionally, for a records dataset `ds`, you also have the following properties or functions to use:
* `raw_data_frame`: a Polars data frame, which hasn't been filtered, selected, purely loaded from a CSV file.
* `records`: a list of `Record` from the `raw_data_frame`, with not null `sequence`.
* `data_frame_by_target()`: a function to retrieve a specific target from `raw_data_frame`, with not null features and target.
* `data_frame()`: a function to retrieve all targets from `raw_data_frame`, with not null features and targets.

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
