# 7. Dataset splits

Date: 2025-10-30
Status: Accepted

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

### Dataset slice

The term "dataset slice" refers to the accessors that create a  subset of a
dataset. Slice is common term in programming to create a subset of a data
structure, for example 
[array slicing](https://en.wikipedia.org/wiki/Array_slicing) or search for
"slice" and your programming language of choice. 

Note that "slice" is used both as a verb 
([function](https://docs.python.org/3/library/functions.html#slice))
and a noun ([object](https://docs.python.org/3/glossary.html#term-slice)). Also
see 
[slicings in Python](https://docs.python.org/3/reference/expressions.html#slicings).

For the protein gym [data model](../data_model.md), a dataset slice is a
collection of accessors for a dataset to select specific (subsets of) assays,
sequences, structures, or MSAs. 

### Dataset operators

The introduction of splits introduces the notion for dataset operators for
communicating about the relationships between datasets, dataset splits, and
dataset slices. 

For example, when splitting a dataset, for each split the following is true:

```
dataset contains split
split is contained in dataset
```

> See Wikipedia on this [subsets](https://en.wikipedia.org/wiki/Set_(mathematics)#Subsets)

When splitting a dataset the following operations hold true:

```
split_1 union split_2 equals dataset
split_1 intersection split_2 equals empty set
dataset difference split_1 equals split_2
```

> Assuming a dataset is split here into two splits: split_1 and split_2.

The difference between a dataset split and slice is that splits are always
[disjoint](https://en.wikipedia.org/wiki/Disjoint_sets) while slices can overlap.

```
split_1 intersection split_2 equals empty set      # Always disjoint
slice_1 intersection slice_2 not equals empty set  # Can overlap
```

For the protein gym [data model](../data_model.md), this implies that a dataset
split needs to account for the interdependencies between the protein data types.
For example, the sequences split from an assay need to be split from the
list of sequences list.

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
- Flexibility : A flexible implementation is preferred. For example, for
  boosting algorithms, one might want to have training sets from different
  datasets and a separate test set. While this is not a common use case, a
  programmatic user might want to create such a dataset combination.

### User-interfaces

The command line interface (CLI) should be as follows:

```shell
$ pg2-dataset splits ./path/to/dataset_with_validation.splits.pgdata
train1.pgdata test1.pgdata val1.pgdata
train2.pgdata test2.pgdata val2.pgdata
train3.pgdata test3.pgdata val3.pgdata
$ pg2-dataset splits ./path/to/dataset_without_validation.splits.pgdata
train1.pgdata test1.pgdata
train2.pgdata test2.pgdata
```

> Note: the `.splits` suffix is just an example, the actual suffix can be different.

The Python API should be as follows:

```python
from pg2_dataset import Dataset 

for train_set, test_set, val_set in Dataset.load_splits("./path/to/dataset_with_validation.splits.pgdata"):
    ...  # Do something with the splits

for train_set, test_set in Dataset.load_splits("./path/to/dataset_without_validation.splits.pgdata"):
    ...  # Do something with the splits
```

> Note: the `Dataset` class is just an example, the actual class can be different.

### Splits marker

Our library should be able to know if a dataset consists of splits, or not.
Furthermore, a user should also be able to check if a dataset is a split.

#### Splits marker decision

A archive with dataset splits has the suffix `.splits.pgdata`.

#### Decision Drivers for splits marker

- differentiate: The splits marker should be able to differentiate between a
  dataset with splits and a dataset without splits.
- user-friendly: The splits marker should be user-friendly and easy to use.

#### Considered splits marker

- Suffix: use a specific suffix for datasets with splits, e.g. `.splits`
- Flag in archive manifest: add a flag in the archive manifest file to indicate
  if a dataset has splits. Note: this has to be done in the **archive** manifest
  file as the splits do not exist yet before archiving.

### Decision matrix for splits marker

| Option                   | Differentiate | User-friendly |
| ------------------------ | ------------- | ------------- |
| Suffix                   | High          | High          |
| Flag in archive manifest | High          | Medium        |

The flag in the archive manifest requires a user to run a command to check if a
dataset has splits, while the suffix can be checked by just looking at the file
name. Therefore, the suffix is more user-friendly.

##### Suffix decision

The chosen suffix is `.splits.pgdata` .

##### Decision drivers for suffix

- Non-breaking : The suffix should not break existing workflows.
- Consistent : The suffix should be consistent with existing conventions.
- Explicit : The suffix should clearly indicate the purpose of the dataset.

##### Considered suffixes

The following additional suffixes were considered:
- `.splits`
- `.superset`

These suffixes can go before or after the `.pgdata` suffix, e.g.: `.splits.pgdata` or
`.pgdata.splits`. Or, without the `.pgdata` suffix, e.g.: `.splits` or
`.superset`.

##### Decision matrix for suffix

| Option              | Non-breaking | Consistent | Explicit |
| ------------------- | ------------ | ---------- | -------- |
| `.splits.pgdata`    | High         | High       | High     |
| `.pgdata.splits`    | High         | Medium     | High     |
| `.splits`           | Low          | Low        | High     |
| `.superset.pgdata`  | High         | High       | Medium   |
| `.pgdata.superset`  | High         | Medium     | Medium   |
| `.superset`         | Low          | Low        | Medium   |

The `.splits.pgdata` suffix is the most straigh-forward option as the archives
remain to end with `.pgdata` and the `.splits` suffix clearly indicates the
purpose of this "special" archive. (That the archive has splits.)

## Considered Options

- Add a split index to the [archive](../dataset_archive.md)
- `Superset`: a dataset of datasets. See Wikipedia on
  [subset](https://en.wikipedia.org/wiki/Subset).

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

| Option                            | Split strategy agnostic | Adjustable dimensions | Consistent for archived datasets | Flexibility |
| --------------------------------- | ----------------------- | --------------------- | -------------------------------- | ----------- |
| Add a split index to the archive  | High                    | High                  | High                             | Medium      |
| `Superset`: a dataset of datasets | High                    | High                  | High                             | High        |

Both options score equally well on the most important decision drivers. However,
the `Superset` option introduces a clearer separation of concerns that is more
flexible.

## Consequences

The supersets have to be created from archives or directly from manifests.
