"""
The splits module provides functionality for splitting datasets.

For example, split dataset for machine learning into training, validation, and
test sets.

TODO
----
- Introduce parent Splitter class when splitter patterns emerge.
"""

import logging
import numbers

import numpy as np

from .assay import AssaySlice
from .dataset import Dataset, DatasetSlice, Subsets

logger = logging.getLogger(__name__)


def _check_random_state(
    seed: None | int | np.random.RandomState,
) -> np.random.RandomState:
    """Turn seed into a np.random.RandomState instance.

    Parameters
    ----------
    seed : None, int or instance of RandomState
        If seed is None, return the RandomState singleton used by np.random.
        If seed is an int, return a new RandomState instance seeded with seed.
        If seed is already a RandomState instance, return it.
        Otherwise, raise ValueError.

    Returns
    -------
    :class:`numpy:numpy.random.RandomState`
        The random state object based on `seed` parameter.

    Examples
    --------
    >>> from sklearn.utils.validation import check_random_state
    >>> check_random_state(42)
    RandomState(MT19937) at 0x...

    Sources
    -------
    Copied from scikit-learn: https://github.com/scikit-learn/scikit-learn/blob/886829ae577ba7a47307e9cfbe6bcc6118296830/sklearn/utils/validation.py#L1439
    """
    if seed is None or seed is np.random:
        return np.random.mtrand._rand
    if isinstance(seed, numbers.Integral):
        return np.random.RandomState(seed)
    if isinstance(seed, np.random.RandomState):
        return seed
    raise ValueError(
        "%r cannot be used to seed a numpy.random.RandomState instance" % seed
    )


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
        random_state (int | np.random.RandomState | None): Seed or random state for
            reproducibility. If None, the global numpy random state is used.
    """

    def __init__(
        self,
        fractions: list[float],
        *,
        random_state: int | np.random.RandomState | None = None,
    ) -> None:
        sum_precision = 2  # Sum of fractions must be equal to 1.0 up to this precision.
        if not round(sum(fractions), sum_precision) == 1.0:
            raise ValueError("Fractions must sum to 1.")
        if not all(0 < fraction for fraction in fractions):
            raise ValueError("Fractions must be positive numbers.")

        self.fractions = fractions
        self.random_state = _check_random_state(random_state)

    def split(self, dataset: Dataset, *, targets: list[str] = None) -> Subsets:
        """Splits the dataset into a subsets.

        The dataset is split into subsets with randomized splits according to
        given fractions. The task is approached by considering all records in
        all assays to be a single list. Then, we shuffle the indices across all
        records. Finally, we reshape shuffled indices back into the original
        assay shapes after converting them into a boolean mask.

        Args:
            dataset (Dataset): The dataset to split.
            targets (list[str] | None): List of target column names to include in the
                splits. If None, all columns are included.

        Returns:
            Subsets: The subsets containing the splits.
        """
        records_shape = tuple(len(assay) for assay in dataset.assays)
        indices = list(range(sum(records_shape)))
        self.random_state.shuffle(indices)

        # Ensure all items are used due to rounding errors by treating the last
        # fraction separately
        sizes = [int(round(f * len(indices))) for f in self.fractions[:-1]]
        sizes.append(len(indices) - sum(sizes))

        slices, offset = [], 0
        for size in sizes:
            index_slice = indices[offset : offset + size]
            masks = _reshape_list(
                _cast_indices_to_mask(index_slice, length=len(indices)), records_shape
            )

            assay_slices = []
            for mask, assay in zip(masks, dataset.assays, strict=True):
                if targets is not None:
                    if not any(target in assay.columns for target in targets):
                        # Skipping the assay if none of the targets are present
                        columns = []
                    else:
                        columns = [assay.sequence_feature_name] + list(
                            set(targets) & set(assay.columns)
                        )
                else:
                    columns = None
                assay_slice = AssaySlice(records=mask, columns=columns)
                assay_slices.append(assay_slice)

            dataset_slice = DatasetSlice(assays=assay_slices)
            slices.append(dataset_slice)
            offset += size

        subsets = Subsets(dataset=dataset, slices=slices)
        return subsets


class KFoldSplitter:
    """Split a dataset into k folds for cross-validation.

    Args:
        n_splits (int): Number of folds. Must be at least 2.
        shuffle (bool): Whether to shuffle the dataset before splitting.
            Defaults to False.
        random_state (int | np.random.RandomState | None): Seed or random state for
            reproducibility. If None, the global numpy random state is used.
    """

    def __init__(
        self,
        n_splits: int,
        *,
        shuffle: bool = False,
        random_state: int | np.random.RandomState | None = None,
    ) -> None:
        if n_splits < 2:
            raise ValueError("Number of splits must be at least 2.")
        if not shuffle and random_state is not None:
            logger.warning("random_state is ignored when shuffle is False.")
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.random_state = _check_random_state(random_state)

    def split(
        self, dataset: Dataset, targets: list[str] | None = None
    ) -> list[Subsets]:
        """Splits the dataset into k folds for cross-validation.

        The dataset is split into k folds with approximately equal sizes. Each
        fold is used as a validation set once, while the remaining folds form
        the training set.

        Args:
            dataset (Dataset): The dataset to split.
            targets (list[str] | None): List of target column names to include in the
                splits. If None, all columns are included.

        Returns:
            list[Subsets]: A list of Subsets, where each Subset contains a training set
            and a validation set for one fold.
        """
        records_shape = tuple(len(assay) for assay in dataset.assays)
        indices = list(range(sum(records_shape)))

        if self.shuffle:
            self.random_state.shuffle(indices)

        # Split indices into k folds
        sizes = [len(indices) // self.n_splits] * self.n_splits
        for i in range(len(indices) % self.n_splits):
            sizes[i] += 1

        slices, offset = [], 0
        for size in sizes:
            index_slice = indices[offset : offset + size]
            masks = _reshape_list(
                _cast_indices_to_mask(index_slice, length=len(indices)), records_shape
            )

            assay_slices = []
            for mask, assay in zip(masks, dataset.assays, strict=True):
                if targets is not None:
                    if not any(target in assay.columns for target in targets):
                        # Skipping the assay if none of the targets are present
                        columns = []
                    else:
                        columns = [assay.sequence_feature_name] + list(
                            set(targets) & set(assay.columns)
                        )
                else:
                    columns = None
                assay_slice = AssaySlice(records=mask, columns=columns)
                assay_slices.append(assay_slice)

            dataset_slice = DatasetSlice(assays=assay_slices)
            slices.append(dataset_slice)
            offset += size

        subsets = Subsets(dataset=dataset, slices=slices)
        return subsets
