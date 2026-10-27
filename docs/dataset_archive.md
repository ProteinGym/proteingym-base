# Dataset Archive

The main deliverable of the ProteinGym dataset is a dataset archive. The key
attribute of the archive is that it **standardizes** protein data. This document
describes the dataset archive.

## Archive layout

A dataset archive (`<name>.pgdata`, written by `Dataset.dump` or
`proteingym-base build`) is a zip file with the following layout:

``` sh
|- manifest.lock
|- assays/
|- assays_raw/
|- msas/          # MSAs and their weights
|- sequences/
|- structures/
```

The [manifest](./manifest.md) contains the metadata that describes the protein
data assets. Read about the [manifest](./manifest.md) for more details.

## Splits archive

A splits archive (`<name>.splits.pgdata`, written by `Subsets.dump`) bundles a
dataset archive with its cross-validation splits:

``` sh
|- dataset.pgdata   # the dataset archive described above
|- slices.json      # the splits, each a list of folds (slices) of the dataset
```

Load it with `Subsets.from_path`. See the
[splitting tutorial](notebooks/05_Creating_Dataset_Splits.ipynb) for how splits are made.
