# Metrics

Metrics quantify how well a model's predictions match the ground truth of a
dataset. ProteinGym Base ships a small, extensible metrics framework that is
used by the benchmark to score model predictions. This document describes how
metrics work and how to design and add new ones.

## Overview

Metrics operate on a ground truth `Dataset` or `Subsets` object and a
`predicted` `Dataset`. The framework uses **dynamic discovery**: any function in
`proteingym.base.metrics` whose name starts with the `metric_` prefix is
automatically discovered and made available for calculation. The part of the
name after `metric_` becomes the metric's name.

For example, a function named `metric_spearman` is exposed as the metric
`"spearman"`, and can be requested via the `selected_metrics` argument.

The following metrics are provided out of the box:

| Metric     | Function          | Range        | Description                                                                 |
|------------|-------------------|--------------|-----------------------------------------------------------------------------|
| `spearman` | `metric_spearman` | `-1.0`–`1.0` | Spearman rank correlation between ground truth and predicted values.        |
| `recovery` | `metric_recovery` | `0.0`–`1.0`  | Fraction of the true top-k variants that appear in the predicted top-k.     |

## Calculating metrics

The public API exposes three entry points:

| Function                     | Purpose                                                                                             |
|------------------------------|-----------------------------------------------------------------------------------------------------|
| `calculate_selected_metrics` | Calculate a chosen set of metrics for a single `Dataset` or a single fold of a `Subsets` object.    |
| `calculate_metrics_by_mode`  | Calculate metrics across scoring modes (`test`, `train_available`, `per_fold`) of a `Subsets`.      |
| `evaluate`                   | Load ground truth and prediction archives, calculate metrics, and write the results to a JSON file. |

A minimal example using `calculate_selected_metrics`:

``` python
from proteingym.base import calculate_selected_metrics

results = calculate_selected_metrics(
    selected_metrics=["spearman"],
    ground_truth=dataset,
    predicted=predictions,
    target="DMS_score",
)
# {"spearman": 0.87}
```

When scoring a `Subsets` object, `split` and `fold` must be provided to select
the relevant cross-validation fold:

``` python
results = calculate_selected_metrics(
    selected_metrics=["spearman", "recovery"],
    ground_truth=subsets,
    predicted=predictions,
    target="DMS_score",
    split="random",
    fold=0,
)
```

## Handling `None` results

A metric may return `None` when it cannot be computed for a given dataset slice.
For example, `recovery` returns `None` when the dataset slice has no `top_k`
metadata (typically the case for training folds). `None` values are preserved in
the output and serialize to `null` in JSON. Metric functions should return
`None` rather than raise when a metric is simply not applicable to the input.

## Designing a new metric

To add a new metric, define a function in `proteingym.base.metrics` that follows
the metric signature below. The function is automatically discovered by its
`metric_` prefix; no registration is required.

### Signature

Every metric function must accept the following parameters:

| Parameter      | Type                        | Description                                                                          |
|----------------|-----------------------------|--------------------------------------------------------------------------------------|
| `ground_truth` | `Subsets \| Dataset`        | The ground truth data.                                                               |
| `predicted`    | `Dataset`                   | The model predictions for the target.                                                |
| `target`       | `str`                       | Name of the target variable to score (e.g. `"DMS_score"`).                           |
| `split`        | `str \| None`               | Required for `Subsets`: the split strategy name (e.g. `"random"`).                   |
| `fold`         | `int \| list[int] \| None`  | Required for `Subsets`: the fold index (or indices) within the split.                |

It must return a `float`, or `None` when the metric is not applicable.

### Example

The following metric computes the mean absolute error between the ground truth
and predicted values:

``` python
import numpy as np

from proteingym.base.dataset import Dataset, Subsets
from proteingym.base.metrics import prepare_and_validate_scoring_df


def metric_mae(
    ground_truth: Subsets | Dataset,
    predicted: Dataset,
    target: str,
    split: str | None = None,
    fold: int | list[int] | None = None,
) -> float:
    """Compute the mean absolute error between ground truth and predictions."""
    scoring_df = prepare_and_validate_scoring_df(
        ground_truth, predicted, target, split, fold
    )
    gt_values = scoring_df[target].to_numpy()
    pred_values = scoring_df[f"{target}_pred"].to_numpy()
    return float(np.mean(np.abs(gt_values - pred_values)))
```

Once defined, the metric is available under the name `"mae"`:

``` python
results = calculate_selected_metrics(
    selected_metrics=["mae"],
    ground_truth=dataset,
    predicted=predictions,
    target="DMS_score",
)
# {"mae": 0.12}
```

### Guidelines

The following guidelines help keep metrics consistent and predictable:

| Guideline                          | Motivation                                                                        |
|------------------------------------|-----------------------------------------------------------------------------------|
| Use `prepare_and_validate_scoring_df` | Aligns ground truth and predictions on sequence and assay variables, and validates complete prediction coverage. |
| Read both `target` and `target_pred` columns | The scoring dataframe stores predicted values under the `_pred` suffix.   |
| Return `None` when not applicable  | Signals "not measured" without raising; serializes to `null` in JSON.             |
| Prefix the function name with `metric_` | Required for automatic discovery.                                            |
| Keep the standard signature        | Enables the metric to be called uniformly by the orchestration functions.         |
