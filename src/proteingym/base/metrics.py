import inspect
import logging
import sys
from collections.abc import Callable, Sequence
from enum import StrEnum

import numpy as np
import polars as pl
from pydantic import BaseModel, ConfigDict, model_validator
from scipy.stats import spearmanr

from .assay import SEQUENCE
from .dataset import Dataset, DatasetSlice, Subsets

logger = logging.getLogger("proteingym.base")


class ScoreMode(StrEnum):
    """A scoring mode for evaluating cross-validation splits."""

    TEST = "test"
    """Score only the test fold."""

    TRAIN_AVAILABLE = "train_available"
    """Score all non-test folds in aggregate."""

    PER_FOLD = "per_fold"
    """Score each fold individually."""

    FULL_DATASET = "full_dataset"
    """Score against the full underlying dataset, ignoring splits."""


MetricFunction = Callable[["DatasetScoringContext"], float | None]

_metric_functions_cache: dict[str, MetricFunction] | None = None


def _split_slices(subsets: Subsets, split: str) -> list[DatasetSlice]:
    """Return the list of slices for a named split strategy."""
    # should be changed with #477
    if not isinstance(subsets.slices, dict):
        raise TypeError(
            "Subsets slices must be stored as a dictionary keyed by split strategy."
        )
    return subsets.slices[split]


def get_fold_indices(subsets: Subsets, split: str) -> list[int]:
    """Get all fold indices for a given split strategy."""
    return list(range(len(_split_slices(subsets, split))))


def _align(
    gt_df: pl.DataFrame, pred_df: pl.DataFrame, gt_variables: list
) -> pl.DataFrame:
    """Align ground truth and predicted dataframes on (sequence, variables).

    Only use variables that are present and not all-null in both dataframes
    (Polars doesn't match null values in joins: NULL != NULL).
    """
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


class DatasetScoringContext(BaseModel):
    """A validated request to score predictions against a plain Dataset.

    This bundles everything a metric needs to run: the ground truth Dataset, the
    predicted Dataset, and the target being scored.

    The predicted dataset is created by `Dataset.predictions_delta` which takes as
    input the target predictions in a form of a dataframe and returns an protein-
    gym dataset with predicted properties.

    Metric functions accept a single DatasetScoringContext and read the aligned data
    from :attr:`scoring_df` rather than re-joining the datasets themselves.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
    )
    """Configuration for the Pydantic model."""

    ground_truth: Dataset
    """The ground truth Dataset."""

    predicted: Dataset
    """The predicted Dataset containing model predictions for the target."""

    target: str
    """The name of the target variable to score (e.g., 'fitness')."""

    @model_validator(mode="after")
    def _validate(self) -> "DatasetScoringContext":
        """Validate matching assay variables."""
        gt_variables = self.ground_truth.assay_variables
        if gt_variables != self.predicted.assay_variables:
            gt_var_names = [v.name for v in gt_variables]
            pred_var_names = [v.name for v in self.predicted.assay_variables]
            raise ValueError(
                "Ground truth and predicted datasets must have identical "
                f"assay_variables. Ground truth has: {gt_var_names}, predicted has: "
                f"{pred_var_names}"
            )
        return self

    @property
    def scoring_df(self) -> pl.DataFrame:
        """Aligned ground truth and predicted values for the target."""
        gt_df = self.ground_truth.to_df(target_names=self.target)
        pred_df = self.predicted.to_df(target_names=self.target)
        return _align(gt_df, pred_df, self.ground_truth.assay_variables)

    @property
    def top_k(self) -> int | None:
        """Top-k threshold. Always None for a plain Dataset (no splitter metadata).

        Kept on the base so `metric_recovery` can read `context.top_k` uniformly;
        recovery returns None for plain datasets.
        """
        return None


class SubsetScoringContext(DatasetScoringContext):
    """A validated request to score predictions against cross-validation Subsets.

    In addition to the base fields, this carries the split strategy and fold(s) to
    evaluate.
    """

    ground_truth: Subsets  # pyrefly: ignore[bad-override]
    """The ground truth Subsets object with cross-validation slices."""

    split: str
    """The split strategy to evaluate."""

    fold: int | list[int]
    """The fold index (or indices) to evaluate.

    A single int scores one fold; a list scores multiple folds in aggregate.
    """

    @model_validator(mode="after")
    def _validate(self) -> "SubsetScoringContext":
        """Validate split/fold presence and matching assay variables."""
        if self.split is None or self.fold is None:
            raise ValueError(
                "Both 'split' and 'fold' must be provided when scoring Subsets."
            )
        gt_variables = self.ground_truth.dataset.assay_variables
        if gt_variables != self.predicted.assay_variables:
            gt_var_names = [v.name for v in gt_variables]
            pred_var_names = [v.name for v in self.predicted.assay_variables]
            raise ValueError(
                "Ground truth and predicted datasets must have identical "
                f"assay_variables. Ground truth has: {gt_var_names}, predicted has: "
                f"{pred_var_names}"
            )
        return self

    def for_fold(self, fold: int | list[int]) -> "SubsetScoringContext":
        """Return a copy of this context targeting different fold(s)."""
        return self.model_copy(update={"fold": fold})

    def for_full_dataset(self) -> "DatasetScoringContext":
        """Return a context scoring the full underlying dataset, ignoring splits."""
        return DatasetScoringContext(
            ground_truth=self.ground_truth.dataset,
            predicted=self.predicted,
            target=self.target,
        )

    @property
    def scoring_df(self) -> pl.DataFrame:
        """Aligned ground truth and predicted values for the target fold(s)."""
        fold_indices = [self.fold] if isinstance(self.fold, int) else self.fold
        split_slices = _split_slices(self.ground_truth, self.split)
        gt_dfs = []
        pred_dfs = []
        for fold_idx in fold_indices:
            dataset_slice = split_slices[fold_idx]
            gt_dfs.append(
                self.ground_truth.dataset[dataset_slice].to_df(
                    target_names=self.target
                )
            )
            pred_dfs.append(
                self.predicted[dataset_slice].to_df(target_names=self.target)
            )
        gt_df = pl.concat(gt_dfs, how="vertical_relaxed")
        pred_df = pl.concat(pred_dfs, how="vertical_relaxed")
        return _align(gt_df, pred_df, self.ground_truth.dataset.assay_variables)

    @property
    def top_k(self) -> int | None:
        """The top-k threshold from QuantileSplitter metadata, if available.

        QuantileSplitter tags test slices with the number of high-property variants
        they contain. This value is used by metric_recovery to compute the recovery
        metric (fraction of true top-k variants that appear in predicted top-k).

        Returns None when:

        - Context targets multiple folds or no specific fold
        - Split name doesn't exist in the Subsets
        - Fold index is out of range
        - The slice has no metadata or no "top_k" key (e.g., training folds,
          non-QuantileSplitter splits)

        This is expected behavior. Most slices won't have top_k metadata, and that's
        fine—metric_recovery simply returns None for those cases.

        Returns:
            The top-k threshold as an integer, or None if unavailable.
        """
        if not isinstance(self.fold, int):
            return None

        # Validate split exists
        if not isinstance(self.ground_truth.slices, dict):
            return None
        if self.split not in self.ground_truth.slices:
            return None

        # Validate fold index is in range
        slices = self.ground_truth.slices[self.split]
        if not (0 <= self.fold < len(slices)):
            return None

        dataset_slice = slices[self.fold]
        if dataset_slice.metadata is None:
            return None

        top_k = dataset_slice.metadata.get("top_k", None)
        return int(top_k) if top_k is not None else None


class MetricsProvenance(BaseModel):
    """Provenance for a metrics result, used to reproduce the scoring run in DVC.

    Combines the fold layout produced during scoring (test/train folds, total fold
    count) with the write-time provenance describing the inputs (dataset, target,
    model, split).
    """

    model_config = ConfigDict(extra="forbid")
    """Configuration for the Pydantic model."""

    dataset: str | None = None
    """Stem of the ground truth dataset archive."""

    target: str | None = None
    """The scored target variable."""

    model: str | None = None
    """Name of the model that generated predictions, if known."""

    split: str | None = None
    """The evaluated split strategy, if applicable."""

    test_fold: int | None = None
    """The test fold index, if applicable."""

    test_folds: list[int] | None = None
    """The fold indices scored as the test set, if applicable."""

    train_available_folds: list[int] | None = None
    """The fold indices available for training, if applicable."""

    total_folds: int | None = None
    """The total number of folds in the split, if applicable."""


class MetricsResult(BaseModel):
    """Metrics computed across one or more scoring modes.

    Each scoring mode maps metric names to their computed value (None when a metric
    cannot be calculated for that slice). ``per_fold`` maps a fold label (e.g.
    'fold_0') to its own metric mapping. ``metadata`` carries provenance such as the
    dataset, target, model, and fold layout.
    """

    model_config = ConfigDict(extra="forbid")
    """Configuration for the Pydantic model."""

    test: dict[str, float | None] | None = None
    """Metrics scored on the test fold, if computed."""

    train_available: dict[str, float | None] | None = None
    """Metrics scored on the aggregate of non-test folds, if computed."""

    per_fold: dict[str, dict[str, float | None]] | None = None
    """Metrics scored on each fold individually, keyed by fold label."""

    full_dataset: dict[str, float | None] | None = None
    """Metrics scored against the full dataset ignoring splits, if computed."""

    metadata: MetricsProvenance | None = None
    """Provenance for the result (dataset, target, model, fold layout, etc.)."""


def _discover_metric_functions() -> dict[str, MetricFunction]:
    """Discover all metric functions in the current module (cached)."""
    global _metric_functions_cache
    if _metric_functions_cache is None:
        _metric_functions_cache = {}
        current_module = sys.modules[__name__]
        for name, obj in inspect.getmembers(current_module, inspect.isfunction):
            if name.startswith("metric_"):
                metric_name = name.replace("metric_", "", 1)
                _metric_functions_cache[metric_name] = obj
    return _metric_functions_cache


def metric_recovery(context: DatasetScoringContext) -> float | None:
    """Compute the recovery metric: fraction of top-k variants correctly identified.

    The recovery metric measures what fraction of the true top-k highest-value
    variants (from ground truth) are also ranked in the top-k of predictions. This
    metric is useful for evaluating whether a model successfully identifies the best
    candidates, which is often more important than precise value prediction.

    The top-k threshold is retrieved from the dataset slice metadata. If the metadata
    does not contain a "top_k" value, or if the context scores a plain Dataset (not
    Subsets), the metric returns None.

    Note on None/NaN values: It is expected and correct for this metric to return
    None in certain scenarios, particularly when evaluating training data. In the
    standard workflow, top-k variants are typically only present in test folds (where
    metadata includes "top_k"), while training folds do not have this metadata. This
    is the intended behavior and None values should be preserved in metric outputs
    (serialized as ``null`` in JSON).
    """
    top_k = context.top_k
    if top_k is None:
        return None

    scoring_df = context.scoring_df
    gt_values = scoring_df[context.target].to_numpy()
    pred_values = scoring_df[f"{context.target}_pred"].to_numpy()

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


def metric_spearman(context: DatasetScoringContext) -> float:
    """Compute the Spearman rank correlation between ground truth and predictions.

    The Spearman correlation assesses how well the relationship between ground truth
    and predicted values can be described using a monotonic function. It measures the
    strength and direction of association between the ranked versions of the values.

    This metric is rank-based and robust to outliers, making it suitable for
    evaluating model predictions when the absolute scale matters less than the
    relative ordering of samples.
    """
    scoring_df = context.scoring_df
    gt_values = scoring_df[context.target].to_numpy()
    pred_values = scoring_df[f"{context.target}_pred"].to_numpy()
    spearman_corr, _ = spearmanr(gt_values, pred_values)
    return spearman_corr


def calculate_selected_metrics(
    selected_metrics: list[str],
    context: DatasetScoringContext,
) -> dict[str, float | None]:
    """Calculate selected metrics for a scoring context.

    This function dynamically discovers all functions with the ``metric_`` prefix in
    this module and executes the requested ones. Each metric function receives the
    scoring context.
    """
    metric_functions = _discover_metric_functions()
    results: dict[str, float | None] = {}

    for metric_name in selected_metrics:
        if metric_name in metric_functions:
            results[metric_name] = metric_functions[metric_name](context)
        else:
            logger.warning(f"Metric '{metric_name}' not found in available metrics")

    return results


def calculate_metrics_by_mode(
    selected_metrics: list[str],
    context: SubsetScoringContext,
    test_fold: int,
    score_modes: Sequence[ScoreMode] = (
        ScoreMode.TEST,
        ScoreMode.TRAIN_AVAILABLE,
        ScoreMode.PER_FOLD,
    ),
) -> MetricsResult:
    """Calculate metrics in different scoring modes.

    Args:
        selected_metrics: List of metric names to calculate (e.g., ["spearman"]).
        context: The scoring context. Must be a SubsetScoringContext whose split
            names the cross-validation strategy to evaluate. The context's fold is
            ignored; the fold to score is determined per mode.
        test_fold: The fold index designated as the test fold.
        score_modes: Sequence of scoring modes (see ScoreMode). Defaults to
            (ScoreMode.TEST, ScoreMode.TRAIN_AVAILABLE, ScoreMode.PER_FOLD).

    Returns:
        A MetricsResult with the computed modes populated and ``metadata`` describing
        the test fold, the available train folds, and the total fold count. When
        full_dataset mode is used, it scores against the complete dataset ignoring all
        splits; the value is identical across folds since it evaluates the same data.
    """
    all_fold_indices = get_fold_indices(context.ground_truth, context.split)
    train_folds = [f for f in all_fold_indices if f != test_fold]

    test: dict[str, float | None] | None = None
    train_available: dict[str, float | None] | None = None
    per_fold: dict[str, dict[str, float | None]] | None = None
    full_dataset: dict[str, float | None] | None = None

    if ScoreMode.TEST in score_modes:
        test = calculate_selected_metrics(selected_metrics, context.for_fold(test_fold))

    if ScoreMode.TRAIN_AVAILABLE in score_modes:
        train_available = calculate_selected_metrics(
            selected_metrics, context.for_fold(train_folds)
        )

    if ScoreMode.PER_FOLD in score_modes:
        per_fold = {
            f"fold_{fold_idx}": calculate_selected_metrics(
                selected_metrics, context.for_fold(fold_idx)
            )
            for fold_idx in all_fold_indices
        }

    if ScoreMode.FULL_DATASET in score_modes:
        full_dataset = calculate_selected_metrics(
            selected_metrics, context.for_full_dataset()
        )

    return MetricsResult(
        test=test,
        train_available=train_available,
        per_fold=per_fold,
        full_dataset=full_dataset,
        metadata=MetricsProvenance(
            test_folds=[test_fold],
            train_available_folds=train_folds,
            total_folds=len(all_fold_indices),
        ),
    )
