"""The protein gym 2 dataset.

A standardized format for storing and sharing datasets in the Protein Gym 2
ecosystem.

Attributes :
    Dataset :
        The main class for managing datasets.
    Manifest :
        Represents the metadata and resources of a dataset.  Entrypoint for
        loading and validating dataset from metadata.
    evaluate_splits :
        Calculate metrics for cross-validation splits (.splits.pgdata).
    evaluate_data :
        Calculate metrics for a plain dataset (.pgdata).
    calculate_selected_metrics :
        Calculate selected metrics comparing ground truth and predictions.
    calculate_metrics_by_mode :
        Calculate metrics across scoring modes (test, train_available, per_fold).
    DatasetScoringContext :
        A validated request bundling a Dataset ground truth, predictions, and target.
    SubsetScoringContext :
        A validated request bundling a Subsets ground truth, predictions, target,
        split, and fold(s).
    MetricsResult :
        Typed metrics computed across one or more scoring modes.
    ScoreMode :
        A scoring mode for evaluating cross-validation splits.
"""

from .dataset import Dataset, Subsets
from .evaluate import evaluate_data, evaluate_splits
from .manifest import Manifest
from .metrics import (
    DatasetScoringContext,
    MetricsProvenance,
    MetricsResult,
    ScoreMode,
    SubsetScoringContext,
    calculate_metrics_by_mode,
    calculate_selected_metrics,
)

__all__ = [
    "Dataset",
    "DatasetScoringContext",
    "Manifest",
    "MetricsProvenance",
    "MetricsResult",
    "ScoreMode",
    "Subsets",
    "SubsetScoringContext",
    "calculate_metrics_by_mode",
    "calculate_selected_metrics",
    "evaluate_data",
    "evaluate_splits",
]
