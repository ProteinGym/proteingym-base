# 4. Dataset splits

Date: 2025-09-04
Status: REVIEW

## Context and Problem Statement

For AI/ML applications, datasets are typically split into training, validation,
and test sets. These splits are used to evaluate the generalization performance of
models and to prevent overfitting. However, the way these splits are created can
vary between datasets or when done on the fly, making it challenging to replicate
the behaviour across model training and evaluation runs.

For more consistent and reproducible results, the dataset should be split
deterministicly while accommodating for different split strategies.  

A counterintuitive example: the random split. Even for the random split, one could
create such a split randomly, then share *their* split with other so that
everyone has the same *random* split.

## Decision

The superset: a dataset of datasets.

## Decision Drivers

- Split strategy agnostic: The split implementation should be agnostic to the
  split strategy. Ideally, users can apply their own split strategy to any
  dataset and then consistently share their split with others.
- Adjustable dimensions: the split implementation should result in split rounds
  where each round can have a variable number of splits and the number of rounds
  can also be variable.
- Consistent for archived datasets: The split implementation should be
  consistent for archived datasets only and be applied while archiving data.
  Datasets created from manifests files do not have to result in consistent
  splits.

### User-interfaces

The command line interface (CLI) should be as follows:

```shell
$ pg2-dataset splits ./path/to/dataset_with_validation.splits
train1.pgdata test1.pgdata val1.pgdata
train2.pgdata test2.pgdata val2.pgdata
train3.pgdata test3.pgdata val3.pgdata
$ pg2-dataset splits ./path/to/dataset_without_validation.splits
train1.pgdata test1.pgdata
train2.pgdata test2.pgdata
```

> Note: the `.splits` suffix is just an example, the actual suffix can be different.

The Python API should be as follows:

```python
from pg2_dataset import Dataset 

for train_set, test_set, val_set in Dataset.load_splits("./path/to/dataset_with_validation.splits"):
    ...  # Do something with the splits

for train_set, test_set in Dataset.load_splits("./path/to/dataset_without_validation.splits"):
    ...  # Do something with the splits
```

> Note: the `Dataset` class is just an example, the actual class can be different.

## Considered Options

- Add a split index to the [archive](../dataset_archive.md)
- `Superset`: a dataset of datasets

### 1. Add a split index to the archive

One option is to add a split index to the archive that tracks how the dataset
is split:

``` tree
|   # inside archive.pgdata
├── split_index.lock
├── manifest.lock
├── assays/
├── msas/
├── sequences/
├── structures/
```

The index file tracks how the dimensions of the splits:

``` json
{
    "splits": [
        [
            ["seq_id1", "seq_id2", ...],
            ["seq_id3", "seq_id4", ...],
            ["seq_id5", "seq_id6", ...]
        ],
        [
            ["seq_id7", "seq_id8", ...],
            ["seq_id9", "seq_id10", ...],
            ["seq_id11", "seq_id12", ...]
        ],
        ...
    ]
}
```

> Note: the index file format is just an example, the actual format can be
> different. 

### 2. Superset: a dataset of datasets

A superset is a dataset that contains multiple datasets, it could be an archive of archives:

``` tree
|   # inside dataset_with_splits.pgdata
├── split_index.lock
├── train1.pgdata
├── test1.pgdata
├── val1.pgdata
├── train2.pgdata
├── test2.pgdata
├── val2.pgdata
├── ...
```

Additionally, an index file tracks how the dimensions of the splits:

``` json
{
    "splits": [
        ["train1.pgdata", "test1.pgdata", "val1.pgdata"],
        ["train2.pgdata", "test2.pgdata", "val2.pgdata"],
        ...
    ]
}
```

> Note: the index file format is just an example, the actual format can be
> different. 

## Decision matrix

| Option                            | Split strategy agnostic | Adjustable dimensions | Consistent for archived datasets |
| --------------------------------- | ----------------------- | --------------------- | -------------------------------- |
| Add a split index to the archive  | High                    | High                  | High                             |
| `Superset`: a dataset of datasets | High                    | High                  | High                             |

Both options score equally well on the decision drivers. However, the `Superset`
option is a better separation of concerns and possibly a cleaner implementation.

## Consequences

The supersets have to be created from archives or directly from manifests.
