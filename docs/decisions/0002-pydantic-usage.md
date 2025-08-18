# 2. Pydantic usage

Date: 2025-08-18
Status: Accepted

## Context and Problem Statement

The project uses Pydantic for data validation and (de)serialization. However,
the project misuses/overuses Pydantic features, leading to unnecessary complexity
by not following a clear separation of concerns. This decision aims to clarify
the intended usage of Pydantic in the project.

## Decision

Use Pydantic: 
1. For `Manifest` validation and (de)serialization. 
2. For `Dataset` validation.

## Decision Drivers

- Aligns with Pydantic's intended use for data validation and serialization.
- Uses Pydantic's features for data validation.
- Fail as early as possible when user-provided data does not conform to the
  expected schema.
- Avoid overusing Pydantic.

## Considered Options

1. All data classes should be Pydantic models 
2. Only `Manifest` should be a Pydantic model as this the only data structure
  representing user-provided data when running from the cli.
3. Use Pydantic for `Manifest` and `Dataset` only, as these are the public API
  data structures representing user-provided data, both in the CLI and
  programmatically.

## Decision matrix

| Option                   | Aligns with Pydantic's use | Use Pydantic features | Fail early | Avoid overuse |
| ------------------------ | -------------------------- | --------------------- | ---------- | ------------- |
| All data classes         | Low                        | High                  | High       | Low           |
| `Manifest`               | High                       | Low                   | High       | High          |
| `Manifest` and `Dataset` | High                       | Medium                | High       | High          |

The `Manifest` and `Dataset` option aligns with Pydantic's intended use for data
while using Pydantic's features for validation and (de)serialization of
user-provided data, both from the CLI and programmically.

## Consequences

Only the `Manifest` and `Dataset` classes will be Pydantic models, which implies
that the other data classes will become "plain" Python data classes. The other
data objectes will integrate more natively with Python code.