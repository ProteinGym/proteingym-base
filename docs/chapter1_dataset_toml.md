# Chapter 1: Creating and Using the dataset.toml File

## Introduction

The `dataset.toml` file is the central configuration file for the PG2 dataset system. It defines the metadata, resources, and structure of your dataset, allowing the system to properly load and process your data. This chapter explains how to create and use a `dataset.toml` file for your projects.

## Structure of dataset.toml

A typical `dataset.toml` file consists of several sections:

1. **Resources**: Defines the locations of data files
2. **Records**: Specifies column information for tabular data
3. **Metadata**: Contains descriptive information about the dataset
4. **Assays**: Defines measurement types and their properties

Let's examine each section in detail.

### Resources Section

The `resources` section specifies the locations of your data files. These can be local file paths or URLs.

```toml
[resources]
records = "https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv"
structure = "example_data/v1/A0A1I9GEU1_NEIME_Kennouche_2019/structure.cif"
# msa = "data/msa.npy"  # Uncomment to include MSA data
```

Available resource types:
- `records`: Path to CSV file containing sequence and assay data (required)
- `structure`: Path to structure file in CIF format (optional)
- `msa`: Path to multiple sequence alignment file (optional)

### Records Section

The `records` section defines how the tabular data in your CSV file is structured.

```toml
[records]
columns = ["mutated_sequence", "mutant", "DMS_score", "DMS_score_bin"]
sequence_feature = "mutated_sequence"
```

Key parameters:
- `columns`: List of column names to load from the CSV file
- `sequence_feature`: The column name that contains the sequence data

### Metadata Section

The `metadata` section provides descriptive information about your dataset.

```toml
[metadata]
name = "project name"
description = "project description"
doi = "DOI: 10.1000/xyz123"
source = "DOI: 10.1000/xyz123"
xref = ""
```

Fields:
- `name`: Short name for the dataset
- `description`: Longer description of the dataset
- `doi`: Digital Object Identifier for citation
- `source`: Source of the data
- `xref`: Cross-references to other resources

### Assays Section

The `assays` section defines the measurements in your dataset and their properties.

```toml
[assays.DMS_score]
description = "Deep mutational scanning score"

[assays.DMS_score.constants]
key_one = "1"
key_two = 2

[assays.DMS_score_bin]
description = "Binarized deep mutational scanning score"
```

For each assay:
- Define a subsection with the assay name (must match a column in your CSV)
- `description`: Description of what the assay measures
- `constants`: Optional constants associated with the assay

## Loading a Dataset from TOML

To load a dataset from a TOML file in your Python code:

```python
from pg2_dataset.dataset import Dataset

# Load dataset from TOML file
dataset = Dataset.from_toml("path/to/dataset.toml")

# Access metadata
print(dataset.meta.name)
print(dataset.meta.description)

# Access assays data
if dataset.assays:
    # Get all records
    records = dataset.assays.records
    
    # Get data as pandas DataFrame
    df = dataset.assays.data_frame
```

## Example dataset.toml

Here's a complete example of a `dataset.toml` file:

```toml
[resources]
records = "https://github.com/ProteinGym2/dvc-dataset-registry/protein_gym/A0A1I9GEU1_NEIME_Kennouche_2019.csv"
structure = "example_data/v1/A0A1I9GEU1_NEIME_Kennouche_2019/structure.cif"

[records]
columns = ["mutated_sequence", "mutant", "DMS_score", "DMS_score_bin"]
sequence_feature = "mutated_sequence"

[metadata]
name = "A0A1I9GEU1_NEIME_Kennouche_2019"
description = "Deep mutational scanning of Neisseria meningitidis FrpC protein"
doi = "DOI: 10.1038/s41467-019-10080-9"
source = "Kennouche et al. 2019"
xref = ""

[assays.DMS_score]
description = "Deep mutational scanning score measuring protein function"

[assays.DMS_score_bin]
description = "Binarized deep mutational scanning score (0 = non-functional, 1 = functional)"
```

## Best Practices

1. **File Organization**: Keep your data files in a consistent directory structure
2. **Naming Conventions**: Use descriptive names for your datasets and assays
3. **Documentation**: Include detailed descriptions for all assays
4. **Version Control**: Track changes to your dataset.toml files
5. **Validation**: Ensure all referenced files exist before distributing your dataset

## Troubleshooting

Common issues when working with dataset.toml files:

1. **File Not Found**: Ensure all paths in the `resources` section are correct
2. **Column Mismatch**: Verify that columns listed in the TOML file match those in your CSV
3. **Missing Sequence Feature**: The `sequence_feature` must point to a valid column in your CSV
4. **Invalid TOML Syntax**: Check for syntax errors in your TOML file

## Summary

The `dataset.toml` file is the foundation of your PG2 dataset. It defines where your data is located, how it's structured, and provides essential metadata. By properly configuring this file, you enable the PG2 dataset system to efficiently load and process your data for analysis and machine learning tasks.