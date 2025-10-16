"""
The splits module provides functionality for splitting datasets.

For example, split dataset for machine learning into training, validation, and
test sets.
"""

import random

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
        if not all(0 < fraction for fraction in fractions):
            raise ValueError("Fractions must be positive numbers.")

        self.dataset = dataset
        self.fractions = fractions

    def split(self) -> Superset:
        """Splits the dataset into a Superset.

        The dataset is split into a Superset with randomized splits according to
        fractions.

        Returns:
            Superset: The superset containing the splits.
        """
        if len(self.dataset.assays) > 1:
            raise NotImplementedError(
                "Random splitting is not implemented for multi-assay datasets."
            )

        indices = list(range(len(self.dataset.assays)))
        random.shuffle(indices)

        sizes = [int(round(f * len(self.dataset.assays))) for f in self.fractions[:-1]]
        sizes.append(
            len(self.dataset.assays) - sum(sizes[:-1])
        )  # Ensure all items are used

        slices, offset = [], 0
        for size in sizes:
            # TODO: Convert indices to a mask
            split_indices = indices[offset : offset + size]
            slices.append(split_indices)
            offset += size

        superset = Superset(dataset=self.dataset, slices=slices)
        return superset
