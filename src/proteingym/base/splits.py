"""
The splits module provides functionality for splitting datasets.

For example, split dataset for machine learning into training, validation, and
test sets.
"""

from .dataset import Dataset
from .superset import Superset


class RandomSplitter:
    """Randomly split a dataset.

    Args:
        dataset (Dataset): The dataset to split.
        fractions (list[float]): A list of floats representing the fractions.
            The fractions must sum to 1. Provide two fractions for a train/test split;
            provide three fractions for a train/val/test split.
    """

    def __init__(self, dataset: Dataset, fractions: list[float]) -> None:
        sum_precision = 2  # Sum of fractions must be equal to 1.0 up to this precision.
        if not round(sum(fractions), sum_precision) == 1.0:
            raise ValueError("Fractions must sum to 1.")
        if not all(0 < fraction < 1 for fraction in fractions):
            raise ValueError("Fractions must be between 0 and 1.")

        self.dataset = dataset
        self.fractions = fractions

    def split(self) -> Superset:
        """Splits the dataset into a Superset."""
        slices = []
        # TODO; Implement random splitting logic.
        superset = Superset(dataset=self.dataset, slices=slices)
        return superset
