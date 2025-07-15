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
maintainer = "John Doe"

[assay_conditions]
name = "PH"
description = "pH level of the samples"
unit = "pH"
data_type = "float"

[[sequences]]
file_path = "sequences.fasta"

[[structures]]
file_path = "structures.pdb"

[[msas]]
file_path = "msas.a3m"

[[assays]]
file_path = "assays.csv"
```

### Top-level

The top-level of the manifest contains the dataset metadata and references to
the protein data types.

| **Field**          | **Type**    | **Description**                                                 |
| ------------------ | ----------- | --------------------------------------------------------------- |
| `version`          | `string`    | The version of the manifest schema.                             |
| `name`             | `string`    | The name of the dataset.                                        |
| `description`      | `string`    | A brief description of the dataset.                             |
| `maintainer`       | `string`    | The name of the person or organization maintaining the dataset. |
| `assay_conditions` | `map`       | A list of assay conditions defined in the dataset.              |
| `sequences`        | `list[map]` | A list of sequences included in the dataset.                    |
| `structures`       | `list[map]` | A list of structures included in the dataset.                   |
| `msas`             | `list[map]` | A list of multiple sequence alignments included in the dataset. |
| `assays`           | `list[map]` | A list of assays included in the dataset.                       |

### Assay Conditions

The assay conditions section contains a list of assay conditions defined in the dataset.

| **Field**     | **Type** | **Description**                                    |
| ------------- | -------- | -------------------------------------------------- |
| `name`        | `string` | The (column) name                                  |
| `description` | `string` | A brief description.                               |
| `unit`        | `string` | The unit of measurement.                           |
| `data_type`   | `string` | The data type: `float`, `int`, `string` or `bool`. |

### Sequences

The sequences section contains a list of sequences included in the dataset.

| **Field**   | **Type** | **Description**                                                                                                                                                       |
| ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `file_path` | `string` | The file path to the sequence data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.fasta`, `.fa`. |

### Structures

The structures section contains a list of structures included in the dataset.

| **Field**   | **Type** | **Description**                                                                                                                                                                |
| ----------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `file_path` | `string` | The file path to the structure data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.pdb`, `.cif`, `.bcif`. |

### MSAs

The MSAs section contains a list of multiple sequence alignments included in the dataset.

| **Field**   | **Type** | **Description**                                                                                                                                                 |
| ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `file_path` | `string` | The file path to the MSA data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.a3m`, `.msa`. |

### Assays

The assays section contains a list of assays included in the dataset.

| **Field**   | **Type** | **Description**                                                                                                                                           |
| ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `file_path` | `string` | The file path to the assay data file or directory. In case of directories, all files within the directory will be included. Supported extensions: `.csv`. |