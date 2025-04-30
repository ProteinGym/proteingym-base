# pg2 dataset

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
    input_keys=["mutated_sequence"],
    label="DMS_score",
    random_state=42,
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
