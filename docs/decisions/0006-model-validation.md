# 1. Model validation

Date: 2025-09-15
Status: Accepted

## Context and Problem Statement

There are two roles in a model benchmarking system:
* Model provider: They either provide a model with a GitHub repo, a distribution package or a Docker image, or only share its API for a remote call. To validate a model to see if it can be integrated in the `proteingym` universe, they want to have an easy-to-use tool to sanity check their models quickly for a feeling of confidence.
* Model benchmarker: They need a uniform API to call each model to get the same format of result in return, so they can compare them on a equal basis. Since they need to validate all models, they want a tool to call these models, while models are running in a self-contained execution environent.

In order for the benchmark to work for a variety of models, we need to validate if these models conform to a standard. Examples of validation checks include:
- [x] If they have the model card defined as expected, so we can load the model's hyperparamters.
- [x] If they have the mandatory entrypoint, with expected input and output.

Given the above considerations, we will first set out to build a tool for model providers to let them do a self-check quickly.

## Decision

Currently, we use the [Option 2: Install `proteingym-base` as a dev dependency and run sanity check by CLI](#option-2-install-proteingym-base-as-a-dev-dependency-and-run-sanity-check-by-cli), as it gives model providers a tool at their hand to sanity check the code during development.

## Decision Drivers

The decision drivers are based on the following constraints, since they cover the majority of models.

| Contraint | Type |
| --------- | ---- |
| The model is implemented in Python | Required |
| The model provides its source code | Required |
| The model project has a [src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) | Required |
| The model exposes its entrypoints by CLI |  Nice to have |
| The model is containerised which comes with its Dockerfile | Nice to have |

Thus, we come to the following drivers:

- Least dependencies, e.g., it is ideal to be independent from `uv`.
- Work across platforms, e.g., UNIX platforms or Windows.
- No hardcoded paths and entrypoint names and parameters, such as `train`.
- Least assumptions, e.g., model providers are expected to write tests, create CLI entrypoints or make Dockerfile.
- Robustness, meaning it is easy to perform this option with robust support, such as Docker or `uv` is actively maintained.
- Insightfulness, meaning it can capture the failures as early as possible and provide debug messages as detailed as possible, so it can help model builders to build their models for the benchmarking system.

## Considered Options

### Option 1: Only verify its exposed Docker entrypoints

The benefit is that we verify it from end to end using the prepared sample data and check if the returned data conforms to our data contract. Besides, it works across all platforms. The downside is that it has more dependencies, such as Docker and the sample data.

#### Example

```shell
docker run --rm ... model-image entrypoint --params ...
```

### Option 2: Install `proteingym-base` as a dev dependency and run sanity check by CLI

The benefit is that for model builders, it is quick to sanity check their code during development. Besides, they can install `proteingym-base` anyway they want, which might be independent from `uv`. It is with the least assumptions and dependencies and insightful, as it can provide debug messages along their development process.

#### Example

```shell
$ proteingym-base validate .
```


## Decision matrix

| Option | Least dependencies | Work across platforms | No hardcoded paths and names | Least assumptions | Robustness | Insightfulness |
|:-------|:------------------:|:---------------------:|:----------------------------:|:-----------------:|:----------:|:----------:|
| Docker |                    | :white_check_mark:    | :white_check_mark:           |                   | :white_check_mark: | :white_check_mark: |
| proteingym-base CLI | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |

## Consequences

`proteingym-base validate` provides the basic sanity check for model builders, based on which we can continuously improve it and extend the tool for model benchmarkers.