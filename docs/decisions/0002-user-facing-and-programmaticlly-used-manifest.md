# 2. User-facing and programmatically-used manifest

Date: 2025-08-18
Status: Accepted

## Context and Problem Statement

Separate the user-facing "external" from the programmatically-used "internal"
manifest. 

> [!NOTE]  
> Or, something similar but with different wording (see below). 

Herewith, the descriptions:
- External manifest : The manifest users utilize to create a dataset, like
  downloading assay, structure, msa and sequence data from certain locations
  combined with metadata like name, description and conditions. This user-facing
  manifest describes how a dataset is created and can be stored in a data catalog
  (catalog could be a git repo) 
- Internal manifest : The manifest that describes the
  persisted ProteinGym dataset. It describes the data resources inside the
  dataset, like the (relative) paths to the assay, structure, MSA and sequence
  data with metadata. This programmatically-used manifest ships with the dataset
  and tracks details of the dataset.

There is overlap between the external and internal dataset, like the name and
description. 
There are also differences, like download the assay from an S3 bucket to create
the dataset (in the external manifest) and load the assay from the csv that
ships with the dataset (in the internal manifest). 

Furthermore, this package can augment the metadata in the external manifest with
runtime metadata, like creation time, to create the metadata for the internal
manifest.

Currently we have an "external" user-facing manifest only. If we reuse that
within the dataset archive, then it is likely to become inaccurate when
archiving the dataset. 

For example, if the manifest might say to download an assay from
`"s3://bucket/assay.csv"`, this would be untrue within the dataset archive
because the assay exists within the dataset (after it was downloaded to persist
the dataset). Moreover, the purpose of the archive is to avoid another download!
Not just because of efficiency, but also because access to the bucket might be
unavailable at this time

Additionally, a user needs to open the dataset archive to quickly reference the
manifest (from a text editor) while we want users to only use the arhive 
through our package. Therefore, it is probably better to ship the (external)
manifest **next to** the persisted dataset instead **within** .

## Decision

We introduce a separation between the user-facing "external" manifest and the
programmatically-used "internal" manifest. Though, we name the "external" manifest
just "manifest" for user-friendliness, and we name the "internal" manifest
archive manifest that is stored in a `manifest.lock` file within the dataset
archive to indicate it should not be edited by users.

## Decision Drivers

1. Accuracy: The manifest should accurately reflect the dataset's contents and
   how to create it, both for users and programmatic use.
2. Reusability: The manifest should be reusable for both user-facing and programmatic
   purposes, avoiding duplication of logic.
3. Quick reference: The manifest should be easy to reference quickly.
4. Avoids access internals: The manifest should not require users to access
   internal details of the dataset.

## Considered Options

1. No separation between external and internal manifest.
2. External and internal manifest
3. Keep external manifest as the manifest and introduce another medium for tracking relative metadata in the persisted dataset

## Decision matrix

| Option                     | Accuracy          | Reusability | Quick reference                                                                          | Avoids access internals         |
| -------------------------- | ----------------- | ----------- | ---------------------------------------------------------------------------------------- | ------------------------------- |
| No separation              | Low (see example) | High        | Low: when part of the dataset archive <br> High when shipped next to the dataset archive | Correlates with quick reference |
| External and internal      | High              | High        | High: requires shipping next to the dataset archive                                      | high                            |
| Additional internal medium | High              | Low         | High                                                                                     | High                            |

The external and internal manifest option is chosen because it is accurate while
reusing manifest logic.

## Naming drivers

The following drivers motivate the choice in naming.
1. Accuracy: Accuracetly describes the manifest's purpose and how it is used.
2. User-friendliness: The manifest should be easy to understand and use for
   users, while also being suitable for programmatic access.
3. Verbosity: The manifest should not be overly verbose while still
   accurately describing its intent.

## Considered Naming Options

1. External / internal
2. \<nothing\> / archive
3. User-facing / Programmatically

## Naming Decision Matrix

| Approach                       | Accuracy | User-friendliness | Verbosity |
| ------------------------------ | -------- | ----------------- | --------- |
| External / internal            | Medium   | Medium            | Medium    |
| \<nothing\> / archive          | High     | High              | Medium    |
| User-facing / Programmatically | High     | Low               | High      |

The \<nothing\> / archive option is chosen because it is the most user-friendly.
We accept that it is less verbosity over user-friendliness.

## File Name drivers.

1. Clarity: The file name should clearly indicate its purpose and contents.
2. Consistency: The file name should be familiar to developers.
3. Simplicity: The file name should be simple and easy to remember.

## Considered File Name Options

1. `manifest.toml`
2. `_manifest.toml`
3. `manifest.lock`
4. `archive_manifest.toml`

## File Name Decision Matrix

| Option                  | Clarity | Consistency | Simplicity |
| ----------------------- | ------- | ----------- | ---------- |
| `manifest.toml`         | Medium  | High        | High       |
| `_manifest.toml`        | Medium  | Medium      | Medium     |
| `manifest.lock`         | High    | Medium      | High       |
| `archive_manifest.toml` | High    | Low         | Medium     |

The `manifest.lock` option is chosen because it clearly indicates that the file
should not be edited by users, while also being consistent with the naming.
Additionally, it is familiar to developers due to the  `uv.lock` file.

## Consequences

No public API changes are required, but we introduce the concept of an archive
manifest.
