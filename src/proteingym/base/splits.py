"""
The splits module provides functionality for splitting datasets.

For example, split dataset for machine learning into training, validation, and
test sets.
"""

import random

from .dataset import Dataset, DatasetSlice
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
        assay = self.dataset.assays[0]

        indices = list(range(len(assay)))
        random.shuffle(indices)

        sizes = [int(round(f * len(assay))) for f in self.fractions[:-1]]
        sizes.append(len(assay) - sum(sizes[:-1]))  # Ensure all items are used

        slices, offset = [], 0
        for size in sizes:
            # TODO: Convert indices to a mask
            slc = indices[offset : offset + size]
            dataset_slice = DatasetSlice(assays=[slc])  # Assuming one assay here
            slices.append(dataset_slice)
            offset += size

        superset = Superset(dataset=self.dataset, slices=slices)
        return superset
