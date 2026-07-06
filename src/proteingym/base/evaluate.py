import json
import logging
from pathlib import Path
from typing import Any

from .dataset import Dataset, Subsets
from .metrics import (
    _discover_metric_functions,
    calculate_metrics_by_mode,
    calculate_selected_metrics,
)

logger = logging.getLogger("proteingym.base")


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
