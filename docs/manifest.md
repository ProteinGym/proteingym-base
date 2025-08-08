# Manifest

The manifest defines how a [dataset](data_model.md) is constructed.

## Capabilities

The following capabilities have been identified:

| Capability           | Kind           | Motivation                                                |
| -------------------- | -------------- | --------------------------------------------------------- |
| Primitive data types | Functional     | For data representation, like `int`, `bool` and `string`. |
| Lists                | Functional     | For organizing data entries.                              |
| Maps                 | Functional     | For organizing data entries.                              |
| Human readable       | Non-functional | To facilitate understanding and editing directly.         |
| Machine readable     | Non-functional | To facilitate programatical reading and parsing.          |
| Version              | Non-functional | For schema evolution.                                     |
| Dataset metadata     | Domain         | A place to define metadata, like name and description.    |
| Path                 | Domain         | To reference data stored on file system.                  |
| Database references  | Domain         | To reference data stored in databases.                    |

Additionally, we defined:

| Kind           | Description                                                                                                     |
| -------------- | --------------------------------------------------------------------------------------------------------------- |
| Functional     | The capability is directly related to the dataset's functionality and is essential for its operation            |
| Non-functional | The capability is not directly related to the dataset's functionality but enhances usability or maintainability |
| Domain         | The capability is specific to the domain of the dataset, such as biological data types.                         |

## TOML Medium

The manifest is defined in [TOML](https://toml.io/en/) format, which is a
human-readable data serialization language. Below tables motivate the coice of
TOML as the medium for the manifest.

| Criteria           | Minimum | Motivation                                          |
| ------------------ | ------- | --------------------------------------------------- |
| Covers requirement | Yes     | The medium should cover the criteria                |
| Text based         | No      | Works well with line-diffs in source control (git). |
| Industry standard  | No      | Easier for user to adopt.                           |

| Minimum criteria | Description                    |
| ---------------- | ------------------------------ |
| Yes              | The criteria is **required**.  |
| No               | The criteria is **preferred**. |

| Medium | Covers criteria | Text based | Industry standard |
| ------ | --------------- | ---------- | ----------------- |
| TOML   | Yes             | Yes        | Yes               |

## Schema

The manifest schema is defined in this section. Let's start with an example
followed by the schema definition.

``` TOML
version = "1.0.0"
name = "Example Dataset"
description = "This is an example dataset for demonstration purposes."

[[assay_conditions]]
name = "PH"
description = "pH level of the samples"
unit = "pH"

[[assays]]
name = "assay"
path = "assay.csv"
sequence = "sequence"
target = "target"

[ assays.conditions ]
PH = "7"

[[ sequences ]]
sequence_type = "wild_type"
sequence_alphabet = "DNA"
path = "sequences.fasta"

[[structures]]
path = "structures.pdb"

[[ msas ]]
path = "msas.a3m"
format = "fasta"

```

### Top-level

The top-level of the manifest contains the dataset metadata and references to
the protein data types.

| **Field**          | **Type**              | **Required** | **Default** | **Description**                                                                                                                                                                                                                                |
| ------------------ | --------------------- | ------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `version`          | `string`              | Yes          | `"1.0.0"`   | The version of the manifest schema. The version follows the semantic versioning format: `<major>.<minor>`. A major version change indicates breaking changes, while a minor version change indicates backward-compatible additions or changes. |
| `name`             | `string`              | Yes          | N/A         | The name of the dataset.                                                                                                                                                                                                                       |
| `description`      | `string \| None`      | No           | `None`      | A brief description of the dataset.                                                                                                                                                                                                            |
| `assay_conditions` | `dict[str, str]`      | No           | Empty dict  | The conditions for the assays defined in the dataset.                                                                                                                                                                                          |
| `assays`           | `list[map[str, str]]` | No           | Empty list  | A list of assays included in the dataset.                                                                                                                                                                                                      |
| `sequences`        | `list[map[str, str]]` | No           | Empty list  | The sequences included in the dataset.                                                                                                                                                                                                         |
| `structures`       | `list[map[str, str]]` | No           | Empty list  | The structures included in the dataset.                                                                                                                                                                                                        |
| `msas`             | `list[map[str, str]]` | No           | Empty list  | The multiple sequence alignments included in the dataset.                                                                                                                                                                                      |

### Assay Conditions

The assay conditions section contains a list of assay conditions defined in the dataset.

| **Field**     | **Type**                              | **Required** | **Default** | **Description**                                    |
| ------------- | ------------------------------------- | ------------ | ----------- | -------------------------------------------------- |
| `name`        | `string`                              | Yes          | N/A         | The assay condition name                           |
| `description` | `string \| None`                      | No           | `None`      | A brief description.                               |
| `unit`        | `string \| None`                      | No           | `None`      | The unit of measurement.                           |
| `value`       | `bool \| int \| float \| str \| None` | No           | `None`      | The value of the condition.                        |


### Assays

The assays section contains a list of assays included in the dataset.

| **Field**    | **Type**         | **Required** | **Default**  | **Description**                                                |
| ------------ | ---------------- | ------------ | ------------ | -------------------------------------------------------------- |
| `name`       | `string`         | No           | `None`       | The name of the assay.                                         |
| `path`       | `string`         | Yes          | N/A          | The path to the assay data file. Supported extensions: `.csv`. |
| `target`     | `string`         | No           | `"target"`   | The target feature name in the assay.                          |
| `sequence`   | `string`         | No           | `"sequence"` | The sequence feature name in the assay.                        |
| `conditions` | `dict[str, str]` | No           | Empty dict   | The conditions of the assay.                                   |

Example of an assay file:

``` csv
mutated_sequence,DMS_score,engineering_round
ITLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSAVTEYYLNHGEWPGDNSSAGVATSADIKGKYVQSVTVANGVITAQMASSNVNNEIKSKKLSLWAKRQNGSVKWFCGQPVTRTTATATDVAAANGKTDDKINTKHLPSTCRDDSSAS,-3.5980000000000003,3
LTLIELMIVIAIVGILAAVALPAYQDYTARAQVSEAILLAEGQKSAVTEYYLNHGEWPGDNSSAGVATSADIKGKYVQSVTVANGVITAQMASSNVNNEIKSKKLSLWAKRQNGSVKWFCGQPVTRTTATATDVAAANGKTDDKINTKHLPSTCRDDSSAS,-0.6779999999999999,1
```

This would be represented in the manifest as:

``` toml
[[assays]]
path = "path/to/assay.csv"
target = "DMS_score"
sequence = "mutated_sequence"
```

### Sequences

The sequences section contains a list of sequences included in the dataset.

| **Field**           | **Type** | **Required** | **Default** | **Description**                                                                                                                                                     |
| ------------------- | -------- | ------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `path`              | `string` | Yes          | N/A         | The path to the sequence data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.fasta`, `.fastq`. |
| `sequence_alphabet` | `string` | Yes          | N/A         | The alphabet of the sequence (e.g., "DNA", "RNA", "AA").                                                                                                        |
| `sequence_type`     | `string` | Yes          | N/A         | The type of the sequence (e.g., "wild_type", "starting_sequence", "engineered_sequence").                                                                                                        |

### Structures

The structures section contains a list of structures included in the dataset.

| **Field** | **Type** | **Required** | **Default** | **Description**                                                                                                                                                           |
| --------- | -------- | ------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `path`    | `string` | Yes          | N/A         | The path to the structure data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.pdb`, `.cif`, `.bcif`. |

### MSAs

The MSAs section contains a list of multiple sequence alignments included in the dataset.

| **Field** | **Type** | **Required** | **Default** | **Description**                                                                                                                                            |
| --------- | -------- | ------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `path`    | `string` | Yes          | N/A         | The path to the MSA data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.a3m`, `.msa`. |
| `format`  | `string` | No           | `"fasta"`   | The format of the MSA data. Supported formats: `"fasta"`                                                                                                   |