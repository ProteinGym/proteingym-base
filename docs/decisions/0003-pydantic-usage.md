# 3. Pydantic usage

Date: 2025-08-18
Status: Accepted

## Context and Problem Statement

The project uses Pydantic for data validation and (de)serialization. However,
Pydantic introduces a risk for misusing/overusing its features, leading to
unnecessary complexity when not following a clear separation of concerns. This
decision aims to clarify the intended usage of Pydantic in the project.

We use [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
that introduce (usefull) features for data validation and serialization.
The validation and serialization functionality is inherited through Pydantic's 
[`BaseModel`](https://docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel),
extending what would have been vanilla Python dataclasses with (implicit) validation,
coercing and parsing data.

When introducing data validation (with Pydantic), a decision has to be taken
where to validate. Following the "fail early" paradigm, we prefer to validate
as early as possible, while keeping the validation logic close to the relevant
context.

## Decision

Use Pydantic: 
1. For `Manifest` validation and (de)serialization. 
2. For `Dataset` validation.

## Decision Drivers

- Aligns with Pydantic's intended use for data validation and serialization.
- Uses Pydantic's features for data validation.
- Fail as early as possible when user-provided data does not conform to the
  expected schema.
- Avoid overusing Pydantic by validating data that can be trusted. (Pydantic is
  intended for validating [untrusted data](https://docs.pydantic.dev/latest/concepts/models/))

## Considered Options

1. All data classes should be Pydantic models 
2. Only `Manifest` should be a Pydantic model as this the only data structure
  representing user-provided data when running from the cli.
3. Use Pydantic for `Manifest` and `Dataset` only, as these are the public API
  data structures representing user-provided data, both in the CLI and
  programmatically.

## Decision matrix

| Option                   | Aligns with Pydantic's use | Use Pydantic features | Fail early | Avoid overuse |
|--------------------------|----------------------------|-----------------------|------------|---------------|
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