---
name: proteingym-base-working-with-pgdata
description: Load, interact with, and extract data from .pgdata archives in proteingym-base
---

# Working with ProteinGym .pgdata Archives

The proteingym-base package provides a standardized format for storing and sharing protein datasets using `.pgdata` archives (ZIP-based archives). This skill guides you through loading and working with these archives.

## Loading .pgdata Archives

### Quick Start: Load from Archive

To load a `.pgdata` archive file:

```python
from proteingym.base import Dataset

# Load directly from archive
dataset = Dataset.from_path("path/to/dataset.pgdata")
print(dataset.name)
```

### Load from Manifest

To load a dataset from a manifest file (`.toml` format):

```python
from proteingym.base import Manifest, Dataset

manifest = Manifest.from_path("example_data/neime_2019.toml")
dataset = Dataset.from_manifest(manifest)
```

## Accessing Dataset Components

The `Dataset` object provides access to four main components:

```python
# Assays - mutation effect data
assays = dataset.assays
for assay in assays:
    print(f"Assay: {assay.name}")

# Sequences - protein sequences
sequences = dataset.sequences
for sequence in sequences:
    print(f"Sequence: {sequence.identifier}")

# Structures - 3D protein structures (PDB, CIF, mmCIF formats)
structures = dataset.structures
for structure in structures:
    print(f"Structure: {structure.identifier}")

# MSAs - Multiple Sequence Alignments (BioPython MultipleSeqAlignment format)
msas = dataset.msas
for msa in msas:
    print(f"MSA alignment length: {len(msa.value)}")
```

## Archive Structure

The internal layout of a `.pgdata` archive:

```
dataset.pgdata
├── manifest.lock          # Metadata and asset manifest
├── assays/               # Tabular mutation effect data
├── assays_raw/          # Raw assay files
├── sequences/           # Protein sequences (FASTA)
├── structures/          # 3D structures (PDB/CIF)
└── msas/               # Multiple sequence alignments (FASTA, A2M, A3M, PSI)
```

## Creating and Persisting Archives

### Create Archive from Manifest

```python
from proteingym.base import Manifest, Dataset

# Load from manifest
manifest = Manifest.from_path("example_data/neime_2019.toml")
dataset = Dataset.from_manifest(manifest)

# Save as .pgdata archive
archive_path = dataset.dump(path="output_directory/")
print(f"Archive created at: {archive_path}")
```

### Reload Persisted Archive

```python
# Quickly reload the archived data
persisted_dataset = Dataset.from_path("output_directory/NEIME_2019.pgdata")
print(persisted_dataset.name)  # 'NEIME_2019'
```

## Working with Assays

Assay data is tabular mutation effect data:

```python
assay = dataset.assays[0]

# Access assay as DataFrame
df = assay.value  # Polars DataFrame

# Common columns: sequence, prediction, ground_truth, split, etc.
print(df.columns)
print(df.head())
```

## Working with MSAs

Multiple Sequence Alignments are stored in multiple formats:

```python
msa = dataset.msas[0]

# Access as BioPython MultipleSeqAlignment
alignment = msa.value

# Iterate over aligned sequences
for record in alignment:
    print(f"Sequence ID: {record.id}, Length: {len(record.seq)}")
```

## Manifest Format

The manifest is a TOML file defining dataset metadata:

```toml
[manifest]
name = "NEIME_2019"
description = "Dataset description"

[[assays]]
path = "path/to/Assays/Assay.csv"

[[sequences]]
path = "path/to/A0A1I9GEU1.fasta"
format = "fasta"

[[structures]]
path = "path/to/Structures/experimental.pdb"
type = "experimental"
format = "pdb"

[[msas]]
path = "path/to/MSA/msa.fasta"
format = "fasta"
```

## Key Classes and Methods

- **`Dataset`** - Main class for managing datasets
  - `from_path(path)` - Load from .pgdata archive
  - `from_manifest(manifest)` - Load from manifest TOML
  - `dump(path)` - Persist to .pgdata archive
  - Properties: `assays`, `sequences`, `structures`, `msas`, `name`

- **`Manifest`** - Metadata and resource descriptor
  - `from_path(path)` - Load from TOML file
  - Validates dataset structure and references

- **`Assay`**, **`Sequence`**, **`Structure`**, **`MSA`** - Dataset components
  - Each has a `.value` property containing the actual data

## Example Data

The repository includes example NEIME 2019 dataset at `example_data/neime_2019.toml` with corresponding data files.

## Evaluation and Metrics

For evaluating predictions against ground truth:

```python
from proteingym.base import evaluate_dataset, evaluate_subset, evaluate_zero_shot

# Evaluate a plain dataset
metrics = evaluate_dataset(
    dataset=dataset,
    predictions=predictions_df,  # Polars DataFrame with predictions
    target="target_column"
)

# Evaluate cross-validation splits
metrics = evaluate_subset(
    dataset=dataset_with_splits,
    predictions=predictions_df,
    target="target_column"
)

# Zero-shot evaluation
metrics = evaluate_zero_shot(
    dataset=dataset_with_splits,
    predictions=predictions_df,
    target="target_column"
)
```
