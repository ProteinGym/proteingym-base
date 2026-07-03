"""The protein gym 2 dataset.

A standardized format for storing and sharing datasets in the Protein Gym 2
ecosystem.

Attributes :
    Dataset :
        The main class for managing datasets.
    Manifest :
        Represents the metadata and resources of a dataset.  Entrypoint for
        loading and validating dataset from metadata.
    evaluate :
        Calculate performance metrics from prediction and dataset archives.
    calculate_selected_metrics :
        Calculate selected metrics comparing ground truth and predictions.
    calculate_metrics_by_mode :
        Calculate metrics across scoring modes (test, train_available, per_fold).
"""

from .dataset import Dataset, Subsets
from .manifest import Manifest
from .metrics import (
    calculate_metrics_by_mode,
    calculate_selected_metrics,
    evaluate,
)

__all__ = [
    "Dataset",
    "Manifest",
    "Subsets",
    "calculate_metrics_by_mode",
    "calculate_selected_metrics",
    "evaluate",
]
