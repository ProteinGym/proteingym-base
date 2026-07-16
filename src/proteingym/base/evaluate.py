import logging
from pathlib import Path

from .dataset import Dataset, Subsets
from .metrics import (
    DatasetScoringContext,
    MetricsProvenance,
    MetricsResult,
    ScoreMode,
    SubsetScoringContext,
    _discover_metric_functions,
    calculate_metrics_by_mode,
    calculate_selected_metrics,
)

logger = logging.getLogger("proteingym.base")


def _write_result(
    result: MetricsResult,
    metric_path: Path,
    *,
    dataset_stem: str,
    target: str,
    model_name: str | None = None,
    split: str | None = None,
    test_fold: int | None = None,
) -> Path:
    """Merge provenance metadata into a result and write it to JSON.

    Args:
        result: The metrics result to persist.
        metric_path: Path where the metrics JSON will be saved.
        dataset_stem: The stem of the ground truth dataset archive.
        target: The scored target variable.
        model_name: Name of the model that generated predictions, if known.
        split: The evaluated split strategy, if applicable.
        test_fold: The test fold index, if applicable.

    Returns:
        The path the metrics JSON was written to (same as ``metric_path``).
    """
    provenance = (result.metadata or MetricsProvenance()).model_copy(
        update={
            "dataset": dataset_stem,
            "target": target,
            "model": model_name,
            "split": split,
            "test_fold": test_fold,
        }
    )
    result = result.model_copy(update={"metadata": provenance})

    metric_path.parent.mkdir(parents=True, exist_ok=True)
    metric_path.write_text(result.model_dump_json(indent=2, exclude_none=True))
    return metric_path


def evaluate_splits(
    prediction_path: Path,
    metric_path: Path,
    dataset_path: Path,
    split: str,
    target: str,
    fold: str,
    selected_metrics: list[str] | None = None,
    model_name: str | None = None,
    score_modes: list[ScoreMode] | None = None,
) -> Path:
    """Calculate metrics for cross-validation splits and save them to JSON.

    Loads ground truth from a Subsets archive (.splits.pgdata) and predictions from a
    prediction archive, scores the requested metrics across the requested scoring
    modes, and writes the results to a JSON file with provenance metadata.

    Args:
        prediction_path: Path to the prediction dataset archive (.pgdata file)
            containing model predictions.
        metric_path: Path where the calculated metrics JSON will be saved.
        dataset_path: Path to the ground truth Subsets archive (.splits.pgdata).
        split: Name of the splitting strategy to evaluate (e.g., 'random').
        target: Name of the target variable to score (e.g., 'DMS_score').
        fold: Fold index (as string) designated as the test fold.
        selected_metrics: Optional list of metric names to calculate (e.g.,
            ["spearman"]). If None, all discovered metrics are included.
        model_name: Name of the model that generated predictions (stored in metadata).
        score_modes: Optional list of scoring modes to compute. If None, defaults to
            test, train_available, and per_fold.

    Returns:
        The path to the saved metrics JSON file (same as metric_path input).
    """
    logger.info("Start to calculate metrics for splits.")

    metrics_to_calculate = selected_metrics or list(_discover_metric_functions())
    ground_truth = Subsets.from_path(dataset_path)
    predicted = Dataset.from_path(prediction_path)
    test_fold = int(fold)

    context = SubsetScoringContext(
        ground_truth=ground_truth,
        predicted=predicted,
        target=target,
        split=split,
        fold=test_fold,
    )
    result = calculate_metrics_by_mode(
        metrics_to_calculate, context, test_fold, score_modes
    )

    return _write_result(
        result,
        metric_path,
        dataset_stem=dataset_path.stem,
        target=target,
        model_name=model_name,
        split=split,
        test_fold=test_fold,
    )


def evaluate_data(
    prediction_path: Path,
    metric_path: Path,
    dataset_path: Path,
    target: str,
    selected_metrics: list[str] | None = None,
    model_name: str | None = None,
) -> Path:
    """Calculate metrics for a plain dataset and save them to JSON.

    Loads ground truth from a Dataset archive (.pgdata) and predictions from a
    prediction archive, scores the requested metrics against the full dataset, and
    writes the results to a JSON file with provenance metadata.

    Args:
        prediction_path: Path to the prediction dataset archive (.pgdata file)
            containing model predictions.
        metric_path: Path where the calculated metrics JSON will be saved.
        dataset_path: Path to the ground truth Dataset archive (.pgdata).
        target: Name of the target variable to score (e.g., 'DMS_score').
        selected_metrics: Optional list of metric names to calculate (e.g.,
            ["spearman"]). If None, all discovered metrics are included.
        model_name: Name of the model that generated predictions (stored in metadata).

    Returns:
        The path to the saved metrics JSON file (same as metric_path input).
    """
    logger.info("Start to calculate metrics for dataset.")

    metrics_to_calculate = selected_metrics or list(_discover_metric_functions())
    ground_truth = Dataset.from_path(dataset_path)
    predicted = Dataset.from_path(prediction_path)

    context = DatasetScoringContext(
        ground_truth=ground_truth, predicted=predicted, target=target
    )
    result = MetricsResult(
        full_dataset=calculate_selected_metrics(metrics_to_calculate, context)
    )

    return _write_result(
        result,
        metric_path,
        dataset_stem=dataset_path.stem,
        target=target,
        model_name=model_name,
    )
