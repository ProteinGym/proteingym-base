# Metrics

Metrics quantify how well a model's predictions match the ground truth of a
dataset. ProteinGym Base ships a small, extensible metrics framework that is
used by the benchmark to score model predictions. This document describes how
metrics work and how to design and add new ones.

## Overview

Metrics operate on a scoring context that bundles a ground truth `Dataset` or
`Subsets` object, a `predicted` `Dataset` and the target. The framework uses **dynamic discovery**: any function in
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

## Usage

You do not need the DVC benchmark pipeline to compute metrics. The metrics API
can be used directly on any dataset archive and set of predictions, which is
handy for quick local checks and exploration.

The typical local workflow is:

1. Load the ground truth dataset archive.
2. Build a predictions `Dataset` from your model's scores using
   [`Dataset.predictions_delta`][proteingym.base.dataset.Dataset.predictions_delta],
   which aligns predictions to the dataset's assay structure by sequence.
3. Wrap ground truth, predictions and target in a scoring context
   ([`DatasetScoringContext`][proteingym.base.metrics.DatasetScoringContext] or
   [`SubsetScoringContext`][proteingym.base.metrics.SubsetScoringContext]).
4. Call [`calculate_selected_metrics`][proteingym.base.metrics.calculate_selected_metrics].

### Scoring a plain dataset

``` python
import polars as pl

from proteingym.base import Dataset, DatasetScoringContext, calculate_selected_metrics

# 1. Load the ground truth dataset archive.
dataset = Dataset.from_path("my_dataset.pgdata")

# 2. Wrap your model's predictions in a Dataset. The DataFrame needs a
#    'sequence' column and a column named after the target being predicted.
scores = pl.DataFrame(
    {
        "sequence": ["MKT...", "MKV...", "MRT..."],
        "DMS_score": [0.12, -0.85, 1.03],
    }
)
predictions = dataset.predictions_delta(scores, target="DMS_score")

# 3. Build the scoring context.
context = DatasetScoringContext(
    ground_truth=dataset,
    predicted=predictions,
    target="DMS_score",
)

# 4. Calculate the metrics you care about.
results = calculate_selected_metrics(selected_metrics=["spearman"], context=context)
print(results)  # {"spearman": 0.87}
```

### Scoring a single fold of a split

If your dataset ships with cross-validation splits (a `.splits.pgdata`
archive), load it as `Subsets` and use a `SubsetScoringContext` with `split`
and `fold` to score a single fold (or a list of folds in aggregate):

``` python
from proteingym.base import Subsets, SubsetScoringContext, calculate_selected_metrics

subsets = Subsets.from_path("my_dataset.splits.pgdata")
predictions = subsets.dataset.predictions_delta(scores, target="DMS_score")

context = SubsetScoringContext(
    ground_truth=subsets,
    predicted=predictions,
    target="DMS_score",
    split="random",
    fold=0,
)
results = calculate_selected_metrics(
    selected_metrics=["spearman", "recovery"],
    context=context,
)
```

### Scoring across all folds at once

To reproduce the benchmark's per-mode breakdown (test fold, aggregated training
folds, and each fold individually) without the pipeline, use
[`calculate_metrics_by_mode`][proteingym.base.metrics.calculate_metrics_by_mode].
It returns a [`MetricsResult`][proteingym.base.metrics.MetricsResult]:

``` python
from proteingym.base import ScoreMode, calculate_metrics_by_mode

result = calculate_metrics_by_mode(
    selected_metrics=["spearman", "recovery"],
    context=context,
    test_fold=0,
    score_modes=[ScoreMode.TEST, ScoreMode.TRAIN_AVAILABLE, ScoreMode.PER_FOLD],
)
result.test             # {"spearman": ..., "recovery": ...}
result.train_available  # {"spearman": ..., "recovery": None}
result.per_fold         # {"fold_0": {...}, "fold_1": {...}, ...}
```

The available score modes are `test`, `train_available`, `per_fold` and
`full_dataset` (score against the whole underlying dataset, ignoring splits).

## Calculating metrics

The public API exposes these entry points:

| Function                     | Purpose                                                                                                       |
|------------------------------|---------------------------------------------------------------------------------------------------------------|
| `calculate_selected_metrics` | Calculate a chosen set of metrics for a `DatasetScoringContext` or `SubsetScoringContext`.                     |
| `calculate_metrics_by_mode`  | Calculate metrics across scoring modes for a `SubsetScoringContext`, returning a `MetricsResult`.             |
| `evaluate_subset`            | Load a `.splits.pgdata` ground truth and a prediction archive, score by mode, and write the results to JSON.  |
| `evaluate_dataset`           | Load a plain `.pgdata` ground truth and a prediction archive, score, and write the results to JSON.           |
| `evaluate_zero_shot`         | Score predictions against the full dataset (zero-shot models), and write the results to JSON.                 |

The `evaluate_*` functions are also available on the command line as
`proteingym-base evaluate-subset`, `evaluate-dataset` and `evaluate-zero-shot`;
these are what the benchmark pipelines call. Run them with `--help` for their options.

## Handling `None` results

A metric may return `None` when it cannot be computed for a given dataset slice.
For example, `recovery` returns `None` when the dataset slice has no `top_k`
metadata (typically the case for training folds) or when scoring a plain
`Dataset`. `None` values are preserved in the output and serialize to `null` in
JSON. Metric functions should return `None` rather than raise when a metric is
simply not applicable to the input.

## Designing a new metric

To add a new metric, define a function in `proteingym.base.metrics` that follows
the metric signature below. The function is automatically discovered by its
`metric_` prefix; no registration is required.

### Signature

Every metric function takes a single scoring context and returns a `float`, or
`None` when the metric is not applicable:

``` python
def metric_<name>(context: DatasetScoringContext) -> float | None: ...
```

The context exposes:

| Attribute      | Type                 | Description                                                                                              |
|----------------|----------------------|----------------------------------------------------------------------------------------------------------|
| `scoring_df`   | `pl.DataFrame`       | Ground truth and predictions aligned row by row, with the prediction in a `<target>_pred` column. For a `SubsetScoringContext` it is restricted to the selected fold(s). |
| `target`       | `str`                | Name of the target variable to score (e.g. `"DMS_score"`).                                               |
| `top_k`        | `int \| None`        | The number of top variants for the slice, if the split recorded one.                                     |
| `ground_truth` | `Dataset \| Subsets` | The ground truth data.                                                                                   |
| `predicted`    | `Dataset`            | The model predictions.                                                                                   |

A `SubsetScoringContext` additionally carries `split` and `fold`.

### Example

The following metric computes the mean absolute error between the ground truth
and predicted values:

``` python
import numpy as np


def metric_mae(context: DatasetScoringContext) -> float:
    """Compute the mean absolute error between ground truth and predictions."""
    scoring_df = context.scoring_df
    gt_values = scoring_df[context.target].to_numpy()
    pred_values = scoring_df[f"{context.target}_pred"].to_numpy()
    return float(np.mean(np.abs(gt_values - pred_values)))
```

Once defined, the metric is available under the name `"mae"`:

``` python
results = calculate_selected_metrics(selected_metrics=["mae"], context=context)
# {"mae": 0.12}
```

### Guidelines

The following guidelines help keep metrics consistent and predictable:

| Guideline                          | Motivation                                                                        |
|------------------------------------|-----------------------------------------------------------------------------------|
| Read from `context.scoring_df`     | The context aligns ground truth and predictions and validates complete prediction coverage; don't re-join the datasets yourself. |
| Read both `target` and `target_pred` columns | The scoring dataframe stores predicted values under the `_pred` suffix.   |
| Return `None` when not applicable  | Signals "not measured" without raising; serializes to `null` in JSON.             |
| Prefix the function name with `metric_` | Required for automatic discovery.                                            |
| Keep the standard signature        | Enables the metric to be called uniformly by the orchestration functions.         |
