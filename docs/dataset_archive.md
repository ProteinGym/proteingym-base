# Dataset Archive

The main delivarable of the Protein Gym 2 dataset is a dataset archive. The key
attribute of the archive is that it **standardizes** protein data. This document 
describes the dataset archive.

## Archive layout

The bundles multiple files with the following layout:

``` sh
|- manifest.lock
|- assays/
|- msas/
|- sequences/
|- structures/
```

The [manifest](./manifest.md) contains the metadata that describes the protein
data assets: `assays/`, `msas/`, `sequences/` and `structures/`. Read about the [manifest](./manifest.md) for more details.