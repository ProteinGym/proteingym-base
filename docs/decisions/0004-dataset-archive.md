# 4. Dataset archive

Date: 2025-09-10
Status: Accepted

## Context and Problem Statement

The archiving protein data is a central goal of this library to standardize and
simplify the sharing and re-use of protein datasets. This functionality deserves
its own [documentation](../dataset_archive.md) next to this architecture
decision record (ADR) that captures how we came to the decision. 

Because of its central role, users will interact with the archive format often.
This means we need to ensure it is well-documented and easy to use.

## Decision

The chosen archive file extension is `.pgdata` that signals it is a Protein Gym
data(set) archive. It also hides which archive format is used internally, allowing us to change that if needed.

Currently, the archive format used internally is ZIP as it is widely
supported.

## Decision Drivers

- User-friendly: The archive format should be easy to use. Even though, we
  expect users to interact with the archive format **through** this library, it
  still helps if it can be easily used outside of it.
- Preserve Linux information: The archive format should preserve Linux
  file information for consistency.
- Support in Windows: The archive format should be supported in Windows as well.
- Free license: So that everyone can use it.

## Considered Options

- ZIP: The ZIP file format.
- TAR.GZ: The tarball file format with gzip compression.

## Decision matrix

| Option | User-friendly | Preserve info | Windows | Free license |
|--------|---------------|---------------|---------|--------------|
| ZIP    | High          | High          | High    | High         |
| TAR.GZ | Medium        | High          | Medium  | High         |

The ZIP format is widely supported across platforms, including Windows, and has
a free license.

## Consequences

The archives get extension `.pgdata` after implementing this decision.

## Archive file extension

The archive file extension is user-facing, therefore it gets its own (sub)decision.

### Decision for archive file extension

The chosen archive file extension is `.pgdata`.

### Decision drivers for archive file extension

- Branding: The archive file extension should reflect the Protein Gym branding.
- Avoid users accessing internals: The archive file extension should not reveal
  the internal archive format to avoid users accessing internals.
- Covers the project's context: The archive file extension should reflect the
  context of the project, i.e. protein datasets.
- User-friendly: The archive file extension should be easy to use.

### Considered archive file extensions

- `.zip`
- `.proteingym`
- `.pgdata`
- `.protein`
- `.mango`

### Decision matrix for archive file extension

| Option      | Branding | Avoid internals | Context                                                    | User-friendly |
|-------------|----------|-----------------|------------------------------------------------------------|---------------|
| .zip        | Low      | High            | Low                                                        | High          |
| .proteingym | High     | High            | Medium* The bigger context not just `proteingym-base` repo | Medium        |
| .pgdata     | High     | High            | High* The context is clearly defined as protein datasets   | High          |
| .protein    | Medium   | High            | Medium* Too big, we focus on protein gym                   | Medium        |
| .mango      | Low      | High            | Low                                                        | High          |

The `.pgdata` extension is short, reflects the Protein Gym branding, and covers the right amount of context.