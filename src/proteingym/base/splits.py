"""
The splits module provides functionality for splitting datasets.

For example, split dataset for machine learning into training, validation, and
test sets.
"""

import random

from .dataset import Dataset, DatasetSlice
from .superset import Superset


def _cast_indices_to_mask(indices: list[int], *, length: int) -> list[bool]:
    """Cast a list of indices to a boolean mask.

    Args:
        indices (list[int]): List of indices to be set to True.
        length (int): Length of the resulting mask.

    Returns:
        list[bool]: Boolean mask with True at the specified indices.
    """
    mask = [False] * length
    for index in indices:
        mask[index] = True
    return mask


def _reshape_list(flat_list: list, shape: tuple[int, ...]) -> list:
    """Reshape to a two-dimensional list with varying sizes of the sublists.

    Note that this different from numpy.reshape, which requires all sublists to
    have the same size and thus the shape contain the size of each dimension.

    Args:
        flat_list (list): The flat list to reshape.
        shape (tuple[int, ...]): The desired shape.

    Returns:
        list: The reshaped nested list.
    """
    if len(flat_list) != sum(shape):
        raise ValueError("The size of the flat list does not match the desired shape.")

    reshaped_list, index = [], 0
    for size in shape:
        sublist = flat_list[index : index + size]
        reshaped_list.append(sublist)
        index += size
    return reshaped_list


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
        given fractions. The task is approached by considering all records in
        all assays to be a single list. Then, we shuffle the indices across all
        records. Finally, we reshape shuffled indices back into the original
        assay shapes after converting them into a boolean mask.

        Returns:
            Superset: The superset containing the splits.
        """
        if len(self.dataset.assays) == 0:
            slices = [DatasetSlice(assays=[]) for _ in self.fractions]
            return Superset(dataset=self.dataset, slices=slices)

        records_shape = tuple(len(assay) for assay in self.dataset.assays)
        indices = list(range(sum(records_shape)))
        random.shuffle(indices)

        # Ensure all items are used due to rounding errors by treating the last
        # fraction separately
        sizes = [int(round(f * len(indices))) for f in self.fractions[:-1]]
        sizes.append(len(indices) - sum(sizes))

        slices, offset = [], 0
        for size in sizes:
            mask = _cast_indices_to_mask(
                indices[offset : offset + size], length=len(indices)
            )
            dataset_slice = DatasetSlice(
                assays=_reshape_list(mask, shape=records_shape)
            )
            slices.append(dataset_slice)
            offset += size

        superset = Superset(dataset=self.dataset, slices=slices)
        return superset
