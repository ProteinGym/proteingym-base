# Manifest

The manifest defines how a dataset is constructed.

## Capabilities

The following capabilities have been identified:

| Capability           | Kind           | Motivation                                                |
|----------------------|----------------|-----------------------------------------------------------|
| Primitive data types | Functional     | For data representation, like `int`, `bool` and `string`. |
| Lists                | Functional     | For organizing data entries.                              |
| Maps                 | Functional     | For organizing data entries.                              |
| Human readable       | Non-functional | To facilitate understanding and editing directly.         |
| Machine readable     | Non-functional | To facilitate programmatically reading and parsing.       |
| Version              | Non-functional | For schema evolution.                                     |
| Dataset metadata     | Domain         | A place to define metadata, like name and description.    |
| Path                 | Domain         | To reference data stored on file system.                  |
| Database references  | Domain         | To reference data stored in databases.                    |

Additionally, we defined:

| Kind           | Description                                                                                                     |
|----------------|-----------------------------------------------------------------------------------------------------------------|
| Functional     | The capability is directly related to the dataset's functionality and is essential for its operation            |
| Non-functional | The capability is not directly related to the dataset's functionality but enhances usability or maintainability |
| Domain         | The capability is specific to the domain of the dataset, such as biological data types.                         |

## TOML Medium

The manifest is defined in [TOML](https://toml.io/en/) format, which is a
human-readable data serialization language. Below tables motivate the choice of
TOML as the medium for the manifest.

| Criteria           | Minimum | Motivation                                          |
|--------------------|---------|-----------------------------------------------------|
| Covers requirement | Yes     | The medium should cover the criteria                |
| Text based         | No      | Works well with line-diffs in source control (git). |
| Industry standard  | No      | Easier for user to adopt.                           |

| Minimum criteria | Description                    |
|------------------|--------------------------------|
| Yes              | The criteria is **required**.  |
| No               | The criteria is **preferred**. |

| Medium | Covers criteria | Text based | Industry standard |
|--------|-----------------|------------|-------------------|
| TOML   | Yes             | Yes        | Yes               |

## Schema

The manifest schema is defined in this section. Let's start with an example
followed by the schema definition.

``` TOML
version = "1.0.0"
name = "Example Dataset"
description = "This is an example dataset for demonstration purposes."
reference_sequence_name = "abc"

[[ assay_variables ]]
name = "PH"
description = "pH level of the samples"
encoding = "numerical"
unit = "pH"

[[ assay_targets ]]
name = "DMS Score"
description = "DMS score of the samples"
unit = "log fold change"

[[ assay_targets ]]
name = "DMS Score Bin"
description = "DMS score bin of the samples"

[[ assays ]]
name = "assay"
path = "assay.csv"
sequence_alphabet = "AA"

[[ assays.targets ]]
name = "DMS Score"
alias = "DMS_score"

[[ assays.targets ]]
name = "DMS Score Bin"
alias = "DMS_score_bin"

[[ assays.non_targets ]]
name = "split"

[ assays.variables ]
PH = 7

[[ assays_raw ]]
name = "assay"
path = "assay_raw.csv"

[[ assays_raw.fields ]]
name = "OD"
unit = "log10(l0 / l)"
description = "Optical density at 600nm"

[[ sequences ]]
type = "wild_type"
alphabet = "DNA"
path = "sequences.fasta"

[[ structures ]]
path = "structures.pdb"

[[ msas ]]
path = "msas.a3m"
format = "fasta"
num_significant = 10
bit_score = 0.5
theta = 0.8
reference_sequence_name = "abc"
sequence_start = 1
sequence_end = 10

[[ msa_weights ]]
name = "msas"
path = "msas_weights.npy"
```

### Top-level

The top-level of the manifest contains the dataset metadata and references to
the protein data types.

| **Field**                 | **Type**              | **Required** | **Default** | **Description**                                                                                                                                                                                                                                                                                                          |
|---------------------------|-----------------------|--------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `version`                 | `string`              | Yes          | N/A         | The version of the manifest schema. The version follows the semantic versioning format: `<major>.<minor>.<patch>`. A major version change indicates breaking changes, while a minor version change indicates backward-compatible additions or changes. A patch version change indicates bug fixes or minor improvements. |
| `name`                    | `string`              | Yes          | N/A         | The name of the dataset.                                                                                                                                                                                                                                                                                                 |
| `description`             | `string \| None`      | No           | `None`      | A brief description of the dataset.                                                                                                                                                                                                                                                                                      |
| `reference_sequence_name` | `string \| None`      | No           | `None`      | The name of the sequence considered to be the main reference sequence.                                                                                                                                                                                                                                                   |
| `assay_variables`         | `dict[str, str]`      | No           | Empty dict  | The variables for the assays defined in the dataset. Can be an assay condition or other variables of interest.                                                                                                                                                                                                           |
| `assay_targets`           | `dict[str, str]`      | No           | Empty dict  | The targets for the assays defined in the dataset. Can be binding affinity, stability, or other targets of interest.                                                                                                                                                                                                     |
| `assays`                  | `list[map[str, str]]` | No           | Empty list  | A list of assays included in the dataset.                                                                                                                                                                                                                                                                                |
| `sequences`               | `list[map[str, str]]` | No           | Empty list  | The sequences included in the dataset.                                                                                                                                                                                                                                                                                   |
| `structures`              | `list[map[str, str]]` | No           | Empty list  | The structures included in the dataset.                                                                                                                                                                                                                                                                                  |
| `msas`                    | `list[map[str, str]]` | No           | Empty list  | The multiple sequence alignments included in the dataset.                                                                                                                                                                                                                                                                |
| `msa_weights`             | `list[map[str, str]]` | No           | Empty list  | The MSA weights included in the dataset.                                                                                                                                                                                                                                                                                 |

### Assay Variables

The assay variables section contains a list of assay variables defined in the dataset. E.g., the pH a certain assay was run at, or the round of engineering that an assay belonged to.

| **Field**     | **Type**                              | **Required** | **Default** | **Description**            |
|---------------|---------------------------------------|--------------|-------------|----------------------------|
| `name`        | `string`                              | Yes          | N/A         | The assay variable name    |
| `description` | `string \| None`                      | No           | `None`      | A brief description.       |
| `unit`        | `string \| None`                      | No           | `None`      | The unit of measurement.   |
| `value`       | `bool \| int \| float \| str \| None` | No           | `None`      | The value of the variable. |

### Assay Targets

The assay targets section contains a list of assay targets defined in the dataset. E.g., the target measured in a certain assay, like binding affinity or stability.

| **Field**     | **Type**                              | **Required** | **Default** | **Description**          |
|---------------|---------------------------------------|--------------|-------------|--------------------------|
| `name`        | `string`                              | Yes          | N/A         | The assay target name    |
| `description` | `string \| None`                      | No           | `None`      | A brief description.     |
| `unit`        | `string \| None`                      | No           | `None`      | The unit of measurement. |
| `value`       | `bool \| int \| float \| str \| None` | No           | `None`      | The value of the target. |

### Assays

The assays section contains a list of assays included in the dataset.

| **Field**           | **Type**         | **Required** | **Default**  | **Description**                                                          |
|---------------------|------------------|--------------|--------------|--------------------------------------------------------------------------|
| `name`              | `string`         | No           | `None`       | The name of the assay.                                                   |
| `path`              | `string`         | Yes          | N/A          | The path to the assay data file. Supported extensions: `.csv`.           |
| `targets`           | `dict[str, str]` | Yes          | N/A          | The map of target names given in manifest to feature names in the assay. |
| `non_targets`       | `list[Field]`    | No           | Empty list   | List of non-target fields that are included but not prediction targets. E.g., predefined CV split allocations                |
| `sequence_alias`    | `string`         | No           | `"sequence"` | The name of the column with sequences in the provided data.              |
| `sequence_alphabet` | `string`         | Yes          | `"AA"`       | The alphabet of the sequence ("DNA", "RNA", or "AA").                    |
| `variables`         | `dict[str, str]` | No           | Empty dict   | The variables of the assay.                                              |

Example of an assay file:

``` csv
mutated_sequence,DMS_score,engineering_round,split
ITLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSAVTEYYLNHGEWPGDNSSAGVATSADIKGKYVQSVTVANGVITAQMASSNVNNEIKSKKLSLWAKRQNGSVKWFCGQPVTRTTATATDVAAANGKTDDKINTKHLPSTCRDDSSAS,-3.5980000000000003,3,train
LTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSAVTEYYLNHGEWPGDNSSAGVATSADIKGKYVQSVTVANGVITAQMASSNVNNEIKSKKLSLWAKRQNGSVKWFCGQPVTRTTATATDVAAANGKTDDKINTKHLPSTCRDDSSAS,-0.6779999999999999,1,test
```

This would be represented in the manifest as:

``` toml
[[assays]]
path = "path/to/assay.csv"
sequence = "mutated_sequence"

[[ assays.targets ]]
name = "DMS Score"
alias = "DMS_score"

[[ assays.non_targets ]]
name = "split"
```

### Raw Assay Data

The raw assays section contains a list of raw assays with the data from which
the assays are created. Raw assays represent observed or calculated values for
specific targets. The raw assays are optional, though, if present, they need to
be linked to an assay.

| **Field**     | **Type**         | **Required** | **Default** | **Description**                                                |
|---------------|------------------|--------------|-------------|----------------------------------------------------------------|
| `name`        | `string`         | Yes          | `None`      | The name of the assay the raw data belongs to.                 |
| `path`        | `string`         | Yes          | N/A         | The path to the assay data file. Supported extensions: `.csv`. |
| `description` | `string \| None` | No           | `None`      | A brief description.                                           |

### Raw Assay Data fields

The fields section defines the fields in the raw assay data file.

| **Field**     | **Type**                              | **Required** | **Default** | **Description**            |
|---------------|---------------------------------------|--------------|-------------|----------------------------|
| `name`        | `string`                              | Yes          | N/A         | The field name             |
| `description` | `string \| None`                      | No           | `None`      | A brief description.       |
| `unit`        | `string \| None`                      | No           | `None`      | The unit of measurement.   |
| `value`       | `bool \| int \| float \| str \| None` | No           | `None`      | The value of the variable. |

### Sequences

The sequences section contains a list of sequences included in the dataset.

| **Field**  | **Type**         | **Required** | **Default** | **Description**                                                                                                                                                     |
|------------|------------------|--------------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `path`     | `string`         | Yes          | N/A         | The path to the sequence data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.fasta`, `.fastq`. |
| `alphabet` | `string`         | Yes          | N/A         | The alphabet of the sequence (e.g., "DNA", "RNA", "AA").                                                                                                            |
| `type`     | `string` \| None | No           | None        | The type of the sequence (e.g., "wild_type", "starting_sequence", "engineered_sequence").                                                                           |

### Structures

The structures section contains a list of structures included in the dataset.

| **Field** | **Type** | **Required** | **Default** | **Description**                                                                                                                                                           |
|-----------|----------|--------------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `path`    | `string` | Yes          | N/A         | The path to the structure data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.pdb`, `.cif`, `.bcif`. |

### MSAs

The MSAs section contains a list of multiple sequence alignments included in the dataset.

| **Field**                 | **Type**        | **Required** | **Default** | **Description**                                                                                                                                            |
|---------------------------|-----------------|--------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `path`                    | `string`        | Yes          | N/A         | The path to the MSA data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.a3m`, `.msa`. |
| `format`                  | `string`        | No           | `"fasta"`   | The format of the MSA data. Supported formats: `"fasta"`                                                                                                   |
| `num_significant`         | `int \| None`   | No           | `None`      | The number of significant sequences to include in the MSA.                                                                                                 |
| `bit_score`               | `float \| None` | No           | `None`      | The bit score threshold for including sequences in the MSA.                                                                                                |
| `theta`                   | `float \| None` | No           | `None`      | The sequence identity threshold for weighting sequences in the MSA.                                                                                        |
| `reference_sequence_name` | `string \| None`| No           | `None`      | The reference sequence name in the MSA.                                                                                                                    |
| `sequence_start`          | `int \| None`   | No           | `None`      | The start position of the sequence in the MSA.                                                                                                             |
| `sequence_end`            | `int \| None`   | No           | `None`      | The end position of the sequence in the MSA.                                                                                                               |
| `weights_path`            | `string \| None`| No           | `None`      | The path to the weights file for the MSA. Supported extensions: `.npy`. (Deprecated: use `msa_weights` section instead)                                    |

### MSA Weights

The MSA weights section contains a list of MSA weight files included in the dataset. Each weight file should correspond to an MSA by name.

| **Field** | **Type** | **Required** | **Default** | **Description**                                                         |
|-----------|----------|--------------|-------------|-------------------------------------------------------------------------|
| `name`    | `string` | Yes          | N/A         | The name of the weights (should match an MSA name).                     |
| `path`    | `string` | Yes          | N/A         | The path to the weights file. Supported extensions: `.npy`.             |

Example:

``` toml
[[ msas ]]
name = "msa1"
path = "msas/msa1.a3m"
format = "fasta"

[[ msa_weights ]]
name = "msa1"
path = "msas/msa1_weights.npy"
```
