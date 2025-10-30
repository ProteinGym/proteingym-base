"""
The splits module provides functionality for splitting datasets.

For example, split dataset for machine learning into training, validation, and
test sets.
"""

import random

from .dataset import Dataset, DatasetSlice, Subsets


def _cast_indices_to_mask(indices: list[int], *, length: int) -> list[bool]:
    """Cast a list of indices to a boolean mask.

    The indices in the input list are set to True in the output mask, while all other
    positions are set to False.

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
        fractions (list[float]): A list of floats representing the fractions.
            The fractions must sum to 1. Provide two fractions for a train/test split;
            provide three fractions for a train/val/test split.
    """

    def __init__(self, fractions: list[float]) -> None:
        sum_precision = 2  # Sum of fractions must be equal to 1.0 up to this precision.
        if not round(sum(fractions), sum_precision) == 1.0:
            raise ValueError("Fractions must sum to 1.")
        if not all(0 < fraction for fraction in fractions):
            raise ValueError("Fractions must be positive numbers.")

        self.fractions = fractions

    def split(self, dataset: Dataset) -> Subsets:
        """Splits the dataset into a subsets.

        The dataset is split into subsets with randomized splits according to
        given fractions. The task is approached by considering all records in
        all assays to be a single list. Then, we shuffle the indices across all
        records. Finally, we reshape shuffled indices back into the original
        assay shapes after converting them into a boolean mask.

        Args:
            dataset (Dataset): The dataset to split.

        Returns:
            Subsets: The subsets containing the splits.
        """
        records_shape = tuple(len(assay) for assay in dataset.assays)
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
            dataset_slice = DatasetSlice(assays=_reshape_list(mask, records_shape))
            slices.append(dataset_slice)
            offset += size

        subsets = Subsets(dataset=dataset, slices=slices)
        return subsets
