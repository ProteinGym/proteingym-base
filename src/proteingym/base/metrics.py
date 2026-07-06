import inspect
import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from scipy.stats import spearmanr

from .assay import SEQUENCE
from .dataset import Dataset, DatasetSlice, Subsets

logger = logging.getLogger("proteingym.base")

MetricFunction = Callable[..., float | None]

_metric_functions_cache: dict[str, MetricFunction] | None = None


def _split_slices(subsets: Subsets, split: str) -> list[DatasetSlice]:
    """Return the list of slices for a named split strategy.

    Args:
        subsets: The Subsets object containing split information.
        split: The name of the split strategy (e.g., 'random', 'kfold_random').

    Returns:
        The list of dataset slices associated with the split.

    Raises:
        TypeError: If the subsets slices are not stored as a dictionary.
    """
    if not isinstance(subsets.slices, dict):
        raise TypeError(
            "Subsets slices must be stored as a dictionary keyed by split strategy."
        )
    return subsets.slices[split]


def get_fold_indices(subsets: Subsets, split: str) -> list[int]:
    """Get all fold indices for a given split strategy.

    Args:
        subsets: The Subsets object containing split information.
        split: The name of the split strategy (e.g., 'random', 'kfold_random').

    Returns:
        List of fold indices available for the split.
    """
    return list(range(len(_split_slices(subsets, split))))


def prepare_and_validate_scoring_df(
    ground_truth: Subsets | Dataset,
    predicted: Dataset,
    target: str,
    split: str | None = None,
    fold: int | list[int] | None = None,
) -> pl.DataFrame:
    """Prepare and validate a scoring dataframe from ground truth and predictions.

    Joins ground truth and predicted datasets on sequence and assay variables,
    ensuring complete prediction coverage. The returned DataFrame contains both
    ground truth and predicted values for the specified target, aligned by
    sequence and variables.

    Args:
        ground_truth: The ground truth data, either as a complete Dataset or
            a Subsets object containing dataset slices.
        predicted: The predicted Dataset containing model predictions for the
            target. Must have the same structure (assays and variables) as the
            ground truth.
        target: The name of the target variable to score (e.g., 'fitness',
            'binding_affinity'). Must be present in both datasets' assay_targets.
        split: Required when ground_truth is a Subsets object. The name of the
            splitting strategy to evaluate (e.g., 'random', 'kfold_random').
        fold: Required when ground_truth is a Subsets object. Can be:
            - A single fold index (int) to score one fold
            - A list of fold indices to score multiple folds in aggregate

    Returns:
        A Polars DataFrame with columns:
            - 'sequence': The protein sequence
            - assay variable columns (e.g., 'temperature', 'pH')
            - target column: ground truth values
            - target_pred column: predicted values (with '_pred' suffix)

    Raises:
        TypeError: If ground_truth is neither a Dataset nor a Subsets object.
        ValueError: If split or fold is None when ground_truth is a Subsets object.
        ValueError: If any ground truth records lack corresponding predictions
            (incomplete coverage).
    """
    if isinstance(ground_truth, Dataset):
        gt_df = ground_truth.to_df(target_names=target)
        pred_df = predicted.to_df(target_names=target)
    elif isinstance(ground_truth, Subsets):
        if split is None or fold is None:
            raise ValueError(
                "Both 'split' and 'fold' must be provided when scoring Subsets."
            )

        fold_indices = [fold] if isinstance(fold, int) else fold

        split_slices = _split_slices(ground_truth, split)
        gt_dfs = []
        pred_dfs = []
        for fold_idx in fold_indices:
            dataset_slice = split_slices[fold_idx]
            gt_dfs.append(
                ground_truth.dataset[dataset_slice].to_df(target_names=target)
            )
            pred_dfs.append(predicted[dataset_slice].to_df(target_names=target))

        gt_df = pl.concat(gt_dfs, how="vertical_relaxed")
        pred_df = pl.concat(pred_dfs, how="vertical_relaxed")
    else:
        raise TypeError("'ground_truth' must be a Dataset or a Subsets object.")

    if isinstance(ground_truth, Subsets):
        gt_variables = ground_truth.dataset.assay_variables
        pred_variables = predicted.assay_variables
    else:
        gt_variables = ground_truth.assay_variables
        pred_variables = predicted.assay_variables

    if gt_variables != pred_variables:
        gt_var_names = [v.name for v in gt_variables]
        pred_var_names = [v.name for v in pred_variables]
        raise ValueError(
            "Ground truth and predicted datasets must have identical assay_variables. "
            f"Ground truth has: {gt_var_names}, predicted has: {pred_var_names}"
        )

    # Join on (sequence, variables) to align predictions with ground truth.
    # Only use variables that are present and not all-null in both dataframes
    # (Polars doesn't match null values in joins: NULL != NULL).
    declared_variable_names = [v.name for v in gt_variables]
    variable_names = [
        var
        for var in declared_variable_names
        if var in gt_df.columns
        and var in pred_df.columns
        and not gt_df[var].is_null().all()
        and not pred_df[var].is_null().all()
    ]
    join_keys = [SEQUENCE] + variable_names

    joined = gt_df.join(pred_df, on=join_keys, how="inner", suffix="_pred")

    missing_predictions = len(gt_df) - len(joined)
    if missing_predictions > 0:
        raise ValueError(f"Missing {missing_predictions} prediction(s).")

    return joined


def _get_top_k_from_slice(
    ground_truth: Subsets | Dataset,
    split: str | None,
    fold: int | list[int] | None,
) -> int | None:
    """Extract top_k from slice metadata if available.

    Args:
        ground_truth: The ground truth data (Dataset or Subsets).
        split: The split name (required for Subsets).
        fold: The fold index (required for Subsets, must be int not list).

    Returns:
        The top_k value from metadata, or None if:
            - ground_truth is not a Subsets object
            - split or fold is not provided
            - fold is a list (not supported for recovery)
            - metadata doesn't exist or doesn't contain top_k
    """
    if not isinstance(ground_truth, Subsets):
        return None
    if split is None or not isinstance(fold, int):
        return None
    try:
        dataset_slice = _split_slices(ground_truth, split)[fold]
    except (KeyError, IndexError, TypeError):
        return None
    if dataset_slice.metadata is None:
        return None
    top_k = dataset_slice.metadata.get("top_k", None)
    return int(top_k) if top_k is not None else None


def _discover_metric_functions() -> dict[str, MetricFunction]:
    """Discover all metric functions in the current module (cached).

    Returns:
        A mapping from metric name (the suffix after ``metric_``) to the metric
        function.
    """
    global _metric_functions_cache
    if _metric_functions_cache is None:
        _metric_functions_cache = {}
        current_module = sys.modules[__name__]
        for name, obj in inspect.getmembers(current_module, inspect.isfunction):
            if name.startswith("metric_"):
                metric_name = name.replace("metric_", "", 1)
                _metric_functions_cache[metric_name] = obj
    return _metric_functions_cache


def metric_recovery(
    ground_truth: Subsets | Dataset,
    predicted: Dataset,
    target: str,
    split: str | None = None,
    fold: int | list[int] | None = None,
) -> float | None:
    """Compute the recovery metric: fraction of top-k variants correctly identified.

    The recovery metric measures what fraction of the true top-k highest-value
    variants (from ground truth) are also ranked in the top-k of predictions. This
    metric is useful for evaluating whether a model successfully identifies the best
    candidates, which is often more important than precise value prediction.

    The top-k threshold is retrieved from the dataset slice metadata. If the metadata
    does not contain a "top_k" value, or if ground_truth is a plain Dataset (not
    Subsets), the metric returns None.

    Note on None/NaN values: It is expected and correct for this metric to return
    None in certain scenarios, particularly when evaluating training data. In the
    standard workflow, top-k variants are typically only present in test folds (where
    metadata includes "top_k"), while training folds do not have this metadata. This
    is the intended behavior and None values should be preserved in metric outputs
    (serialized as ``null`` in JSON).

    Args:
        ground_truth: The ground truth data, either as a complete Dataset or
            a Subsets object containing dataset slices.
        predicted: The predicted Dataset containing model predictions for the target.
        target: The name of the target variable to score (e.g., 'fitness').
        split: Required when ground_truth is a Subsets object. The name of the
            splitting strategy to evaluate (e.g., 'random').
        fold: Required when ground_truth is a Subsets object. The fold index
            (0-based integer) within the specified split. Must be a single integer,
            not a list.

    Returns:
        The recovery fraction (0.0 to 1.0) representing the fraction of true top-k
        variants that appear in the predicted top-k, or None if top_k is not available
        or if top_k is invalid (e.g., <= 0).

    Raises:
        TypeError: If ground_truth is neither a Dataset nor a Subsets object.
        ValueError: If split or fold is None when ground_truth is a Subsets object.
        ValueError: If any ground truth records lack corresponding predictions.
        ValueError: If top_k is larger than the number of samples.
    """
    top_k = _get_top_k_from_slice(ground_truth, split, fold)
    if top_k is None:
        return None

    scoring_df = prepare_and_validate_scoring_df(
        ground_truth, predicted, target, split, fold
    )

    gt_values = scoring_df[target].to_numpy()
    pred_values = scoring_df[f"{target}_pred"].to_numpy()

    n_samples = len(gt_values)
    if top_k > n_samples:
        raise ValueError(
            f"top_k ({top_k}) is larger than the number of samples ({n_samples})."
        )
    effective_k = min(top_k, n_samples)

    if effective_k <= 0:
        return None

    top_k_gt_indices = set(np.argsort(gt_values)[-effective_k:])
    top_k_pred_indices = set(np.argsort(pred_values)[-effective_k:])

    overlap = len(top_k_gt_indices & top_k_pred_indices)
    return overlap / effective_k


def metric_spearman(
    ground_truth: Subsets | Dataset,
    predicted: Dataset,
    target: str,
    split: str | None = None,
    fold: int | list[int] | None = None,
) -> float:
    """Compute the Spearman rank correlation between ground truth and predictions.

    The Spearman correlation assesses how well the relationship between ground truth
    and predicted values can be described using a monotonic function. It measures the
    strength and direction of association between the ranked versions of the values.

    This metric is rank-based and robust to outliers, making it suitable for
    evaluating model predictions when the absolute scale matters less than the
    relative ordering of samples.

    Args:
        ground_truth: The ground truth data, either as a complete Dataset or
            a Subsets object containing dataset slices.
        predicted: The predicted Dataset containing model predictions for the target.
        target: The name of the target variable to score (e.g., 'fitness').
        split: Required when ground_truth is a Subsets object. The name of the
            splitting strategy to evaluate (e.g., 'random').
        fold: Required when ground_truth is a Subsets object. The fold index
            (0-based integer) within the specified split.

    Returns:
        The Spearman rank correlation coefficient, ranging from -1 to 1:
            - 1.0 indicates a perfect positive monotonic relationship
            - -1.0 indicates a perfect negative monotonic relationship
            - 0.0 indicates no monotonic relationship

    Raises:
        TypeError: If ground_truth is neither a Dataset nor a Subsets object.
        ValueError: If split or fold is None when ground_truth is a Subsets object.
        ValueError: If any ground truth records lack corresponding predictions.
    """
    scoring_df = prepare_and_validate_scoring_df(
        ground_truth, predicted, target, split, fold
    )
    gt_values = scoring_df[target].to_numpy()
    pred_values = scoring_df[f"{target}_pred"].to_numpy()
    spearman_corr, _ = spearmanr(gt_values, pred_values)
    return spearman_corr


def calculate_selected_metrics(
    selected_metrics: list[str],
    ground_truth: Subsets | Dataset,
    predicted: Dataset,
    target: str,
    split: str | None = None,
    fold: int | list[int] | None = None,
) -> dict[str, float | None]:
    """Calculate selected metrics by comparing ground truth and predictions.

    This function dynamically discovers all functions with the ``metric_`` prefix in
    this module and executes the requested ones. Each metric function receives the
    ground truth, predictions, and scoring parameters.

    Args:
        selected_metrics: List of metric names to calculate (e.g., ["spearman"]).
            Names should match the function suffix after ``metric_``.
        ground_truth: The ground truth data, either as a complete Dataset or
            a Subsets object containing dataset slices.
        predicted: The predicted Dataset containing model predictions for the target.
        target: The name of the target variable to score (e.g., 'fitness').
        split: Required when ground_truth is a Subsets object. The name of the
            splitting strategy to evaluate (e.g., 'random').
        fold: Required when ground_truth is a Subsets object. The fold index
            (0-based integer) within the specified split.

    Returns:
        Dictionary mapping metric names to their computed values. Some metrics (like
        recovery) may return None when they cannot be calculated for a given dataset
        slice (e.g., missing metadata). None values are preserved in the output and
        will serialize as null in JSON.
    """
    metric_functions = _discover_metric_functions()
    results: dict[str, float | None] = {}

    for metric_name in selected_metrics:
        if metric_name in metric_functions:
            metric_value = metric_functions[metric_name](
                ground_truth, predicted, target, split, fold
            )
            results[metric_name] = metric_value
        else:
            logger.warning(f"Metric '{metric_name}' not found in available metrics")

    return results


def calculate_metrics_by_mode(
    selected_metrics: list[str],
    ground_truth: Subsets,
    predicted: Dataset,
    target: str,
    split: str,
    test_fold: int,
    score_modes: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate metrics in different scoring modes.

    Args:
        selected_metrics: List of metric names to calculate (e.g., ["spearman"]).
        ground_truth: The Subsets object containing cross-validation splits.
        predicted: The predicted Dataset containing model predictions.
        target: The name of the target variable to score.
        split: The name of the splitting strategy (e.g., 'random', 'kfold_random').
        test_fold: The fold index designated as the test fold.
        score_modes: List of scoring modes. Options:
            - "test": Score only the test fold
            - "train_available": Score all non-test folds in aggregate
            - "per_fold": Score each fold individually
            - "full_dataset": Score against the full underlying dataset (ignoring
              splits)
            If None, defaults to ["test", "train_available", "per_fold"].

    Returns:
        Dictionary with structure::

            {
                "test": {"spearman": 0.85, ...},
                "train_available": {"spearman": 0.92, ...},
                "per_fold": {
                    "fold_0": {"spearman": 0.91, ...},
                    ...
                },
                "full_dataset": {"spearman": 0.83, ...},
                "metadata": {
                    "test_folds": [4],
                    "train_available_folds": [0, 1, 2, 3],
                    "total_folds": 5
                }
            }

        When full_dataset mode is used, it scores against the complete dataset
        ignoring all splits. The metric value is identical across all folds since it
        evaluates the same data regardless of the fold.
    """
    if score_modes is None:
        score_modes = ["test", "train_available", "per_fold"]

    all_fold_indices = get_fold_indices(ground_truth, split)
    train_folds = [f for f in all_fold_indices if f != test_fold]

    results: dict[str, Any] = {}

    if "test" in score_modes:
        results["test"] = calculate_selected_metrics(
            selected_metrics, ground_truth, predicted, target, split, test_fold
        )

    if "train_available" in score_modes:
        results["train_available"] = calculate_selected_metrics(
            selected_metrics, ground_truth, predicted, target, split, train_folds
        )

    if "per_fold" in score_modes:
        per_fold: dict[str, dict[str, float | None]] = {}
        for fold_idx in all_fold_indices:
            per_fold[f"fold_{fold_idx}"] = calculate_selected_metrics(
                selected_metrics, ground_truth, predicted, target, split, fold_idx
            )
        results["per_fold"] = per_fold

    if "full_dataset" in score_modes:
        results["full_dataset"] = calculate_selected_metrics(
            selected_metrics, ground_truth.dataset, predicted, target, None, None
        )

    results["metadata"] = {
        "test_folds": [test_fold],
        "train_available_folds": train_folds,
        "total_folds": len(all_fold_indices),
    }

    return results


def evaluate(
    prediction_path: Path,
    metric_path: Path,
    dataset_path: Path | None = None,
    selected_metrics: list[str] | None = None,
    model_name: str | None = None,
    split: str | None = None,
    target: str | None = None,
    fold: str | None = None,
    score_modes: list[str] | None = None,
) -> Path:
    """Calculate performance metrics from predictions and save results to JSON.

    Loads ground truth data from a dataset archive (.pgdata or .splits.pgdata),
    loads predictions from a prediction archive, calculates the selected metrics,
    and saves the results to a JSON file with metadata.

    The function automatically detects whether the dataset is a plain Dataset
    (.pgdata) or Subsets (.splits.pgdata) based on the file extension.

    If the prediction file is not found, an error JSON with null metric values
    is written instead.

    Args:
        prediction_path: Path to the prediction dataset archive (.pgdata file)
            containing model predictions.
        metric_path: Path where the calculated metrics JSON will be saved.
        dataset_path: Path to the ground truth dataset archive. Can be either:
            - .pgdata file: Plain Dataset for single-fold scoring
            - .splits.pgdata file: Subsets with cross-validation splits
        selected_metrics: Optional list of metric names to calculate (e.g.,
            ["spearman"]). If None, all discovered metrics are included.
        model_name: Name of the model that generated predictions (stored in metadata).
        split: Name of the splitting strategy to evaluate (e.g., 'random'). Required
            when dataset_path is a .splits.pgdata file.
        target: Name of the target variable to score (e.g., 'DMS_score', 'fitness').
            Required for all metric calculations.
        fold: Fold index (as string) designated as the test fold. Required when
            dataset_path is a .splits.pgdata file.
        score_modes: List of scoring modes. Options: "test", "train_available",
            "per_fold", "full_dataset". If None, defaults to
            ["test", "train_available", "per_fold"]. Only used when dataset_path is a
            .splits.pgdata file.

    Returns:
        The path to the saved metrics JSON file (same as metric_path input).

    Raises:
        ValueError: If required parameters (--split, --fold, --target) are missing for
            a Subsets file, or if --target is missing for a plain Dataset.
    """
    logger.info("Start to calculate metrics.")

    if not prediction_path.exists():
        logger.error(f"Prediction file not found: {prediction_path}")
        error_result: dict[str, Any] = {
            "error": f"Prediction file not found: {prediction_path}",
            "status": "failed",
        }

        if selected_metrics:
            for metric_name in selected_metrics:
                error_result[metric_name] = None

        metric_path.write_text(json.dumps(error_result, indent=2))
        return metric_path

    if dataset_path is None:
        raise ValueError(
            "The 'dataset_path' parameter is required for metric calculation."
        )

    metrics_to_calculate = selected_metrics or list(_discover_metric_functions())

    try:
        if dataset_path.name.endswith(".splits.pgdata"):
            ground_truth: Dataset | Subsets = Subsets.from_path(dataset_path)
        else:
            ground_truth = Dataset.from_path(dataset_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load dataset from {dataset_path}: {e}")
        raise

    try:
        predicted = Dataset.from_path(prediction_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load predictions from {prediction_path}: {e}")
        raise

    test_fold: int | None = None
    metrics_result: dict[str, Any]
    if isinstance(ground_truth, Subsets):
        if split is None or fold is None or target is None:
            raise ValueError(
                "Parameters --split, --fold, and --target are required when "
                "dataset_path is a Subsets file (.splits.pgdata)."
            )

        test_fold = int(fold)

        metrics_result = calculate_metrics_by_mode(
            metrics_to_calculate,
            ground_truth,
            predicted,
            target,
            split,
            test_fold,
            score_modes,
        )
    else:
        if target is None:
            raise ValueError(
                "The 'target' parameter is required for metric calculation. "
                "Please provide --target."
            )

        metrics_result = {
            "full_dataset": calculate_selected_metrics(
                metrics_to_calculate, ground_truth, predicted, target, None, None
            )
        }

    dataset_name = dataset_path.stem
    if any([dataset_name, model_name, split, target, fold]):
        if "metadata" not in metrics_result:
            metrics_result["metadata"] = {}
        if dataset_name:
            metrics_result["metadata"]["dataset"] = dataset_name
        if model_name:
            metrics_result["metadata"]["model"] = model_name
        if split:
            metrics_result["metadata"]["split"] = split
        if target:
            metrics_result["metadata"]["target"] = target
        if fold:
            metrics_result["metadata"]["test_fold"] = test_fold

    metric_path.parent.mkdir(parents=True, exist_ok=True)
    metric_path.write_text(json.dumps(metrics_result, indent=2))
    return metric_path
