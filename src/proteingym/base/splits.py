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
import numpy.typing as npt
from Bio.Seq import Seq

from .assay import AssaySlice
from .dataset import Dataset, DatasetSlice, Subsets

logger = logging.getLogger(__name__)


def _check_random_state(
    seed: None | int | np.random.RandomState,
) -> np.random.RandomState:
    """Turn seed into a np.random.RandomState instance.

    Args:
        seed : None, int or instance of RandomState
            If seed is None, return the RandomState singleton used by np.random.
            If seed is an int, return a new RandomState instance seeded with seed.
            If seed is already a RandomState instance, return it.
            Otherwise, raise ValueError.

    Returns:
        The random state object based on `seed` parameter.

    Examples:
    >>> from sklearn.utils.validation import check_random_state
    >>> check_random_state(42)
    RandomState(MT19937) at 0x...

    Sources:
    Copied from scikit-learn: https://github.com/scikit-learn/scikit-learn/blob/
    886829ae577ba7a47307e9cfbe6bcc6118296830/sklearn/utils/validation.py#L1439
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
        indices: List of indices to be set to True.
        length: Length of the resulting mask.

    Returns:
        list: Boolean mask with True at the specified indices.
    """
    mask = [False] * length
    for index in indices:
        mask[index] = True
    return mask


def _sequences_to_mask(selection: list[Seq], *, all_sequences: list[Seq]) -> list[bool]:
    """Cast a list of indices to a boolean mask.

    The indices in the input list are set to True in the output mask, while all other
    positions are set to False.

    Args:
        selection: List of sequences for which the mask shall be True
        all_sequences: List of sequences at each position of mask

    Returns:
        list[bool]: Boolean mask with True at the specified indices.
    """
    mask = [False] * len(all_sequences)
    for index, seq in enumerate(all_sequences):
        if seq in selection:
            mask[index] = True
    return mask


def _subsample_mask(
    mask: npt.NDArray,
    fraction: float,
    random_state: int | np.random.RandomState | None = None,
) -> npt.NDArray:
    """
    Subsample True values in a boolean mask.

    Calculates the number of True values to keep using the fraction argument, checks
    which indices in the mask are set to True, uniformly samples those indices, and
    then creates a new mask with True values at the sampled indices.

    Args:
        mask: Boolean array to subsample
        fraction: Fraction of True values to keep (0.0 to 1.0)
            E.g., 0.8 means keep 80% and flip 20% to False
        random_state: reproducibility. If None, the global numpy random state is used.

    Returns:
        npt.NDArray: New boolean mask with subsampled True values
    """
    if not 0 <= fraction <= 1:
        raise ValueError("Fraction must be between 0 and 1")
    true_indices = np.where(mask)[0]
    n_true = len(true_indices)
    n_keep = int(n_true * fraction)
    random_state = _check_random_state(random_state)
    keep_indices = random_state.choice(true_indices, size=n_keep, replace=False)
    new_mask = np.zeros_like(mask, dtype=bool)
    new_mask[keep_indices] = True
    return new_mask


def _reshape_list(flat_list: list, shape: tuple[int, ...]) -> list:
    """Reshape to a two-dimensional list with varying sizes of the sublists.

    Note that this different from numpy.reshape, which requires all sublists to
    have the same size and thus the shape contain the size of each dimension.

    Args:
        flat_list: The flat list to reshape.
        shape: The desired shape.

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


def _unique_sequences_for_targets(
    dataset: Dataset, targets: list[str] = None
) -> list[Seq]:
    """Get the unique sequences for all assays, for a given list of targets.

    Args:
        dataset: the dataset with assays
        targets: list of targets for which we shall collect unique sequences.
    """
    sequences = set()
    for assay in dataset.assays:
        if not targets:
            sequences |= {r[0].value for r in assay.records}
        else:
            target_names = [e.name for e in assay.fields]
            target_indices = [
                target_names.index(t) for t in targets if t in target_names
            ]
            sequences |= {
                r[0].value
                for r in assay.records
                if any(r[idx] is not None for idx in target_indices)
            }

    return list(sequences)


class QuantileSplitter:
    """Splits the data by reserving samples with high property values for the test set.

    Split a dataset a random training set and a test set with a sample of hit
    variants defined as values exceeding a quantile threshold. This split is only
    defined for a single target in the dataset, because the quantile threshold can only
    be defined for a single target.

    Args:
        quantile: A float between 0 and 1 used to derive the percentile that will be
            used as a threshold. Values exceeding the threshold are considered the hit
            variants.
        random_state: Seed or random state for
            reproducibility. If None, the global numpy random state is used.
    """

    def __init__(
        self,
        quantile: float,
        fraction: float,
        *,
        random_state: int | np.random.RandomState | None = None,
    ) -> None:
        if not 0 <= quantile <= 1:
            raise ValueError("Quantile must lie between 0 and 1.")
        if not 0 <= fraction <= 1:
            raise ValueError("Fraction must lie between 0 and 1.")
        self.quantile = quantile
        self.fraction = fraction
        self.random_state = _check_random_state(random_state)

    def split(self, dataset: Dataset, *, target: str) -> Subsets:
        """Splits the dataset into a Subsets object storing a training set and a test
        set.

        For a single target, the quantile threshold is calculated based on
        self.quantile. The threshold is used to divide the data into an upper and lower
        interval. The training set is composed by sampling self.fraction from the lower
        interval, and the test set is composed by sampling 1 - self.fraction from the
        upper interval, and 1 - self.fraction from the lower interval.

        Args:
            dataset: The dataset to split.
            target: Target field name to include in the
                splits.

        Returns:
            Subsets: The subsets containing the splits.
        """
        train_assay_slices = []
        test_assay_slices = []
        for assay in dataset.assays:
            target_names_in_assay = [e.name for e in assay.fields]
            if target not in target_names_in_assay:
                columns = []
                train_assay_slices.append(AssaySlice(records=None, columns=columns))
                test_assay_slices.append(AssaySlice(records=None, columns=columns))
            else:
                columns = [assay.sequence_feature_name, target]
                target_index = next(
                    i for i, field in enumerate(assay.fields) if field.name == target
                )
                target_values = np.array([r[target_index] for r in assay.records])

                threshold = np.quantile(target_values, self.quantile)
                lower_mask = ~np.isnan(target_values) & (target_values <= threshold)
                upper_mask = ~np.isnan(target_values) & (target_values > threshold)
                train_mask = _subsample_mask(
                    lower_mask, fraction=self.fraction, random_state=self.random_state
                )
                test_mask = _subsample_mask(
                    upper_mask,
                    fraction=1 - self.fraction,
                    random_state=self.random_state,
                ) | (~train_mask & lower_mask)
                train_assay_slices.append(
                    AssaySlice(records=train_mask, columns=columns)
                )
                test_assay_slices.append(AssaySlice(records=test_mask, columns=columns))
        train_dataset_slice = DatasetSlice(assays=train_assay_slices)
        test_dataset_slice = DatasetSlice(assays=test_assay_slices)
        subsets = Subsets(
            dataset=dataset, slices=[train_dataset_slice, test_dataset_slice]
        )
        return subsets


class RandomSplitter:
    """Randomly split a dataset.

    Args:
        fractions: A list of floats representing the fractions.
            The fractions must sum to 1. Provide two fractions for a train/test split;
            provide three fractions for a train/val/test split.
        random_state: Seed or random state for
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

        The unique sequences from the records of all assays that list at least one of
        the given targets, are split into random subsets according to the given
        fractions. The task is approached by considering all records in all assays to
        be a single list. We collect the unique sequences, shuffle and split those,
        then turn these into a boolean masks based on non-unique sequences to slice
        the assays. Note that depending on the duplicity of sequences among datasets,
        the resulting sizes may deviate from those implied by the given fractions.

        Args:
            dataset: The dataset to split.
            targets: List of target field names to include in the
                splits. If None, all fields are included.

        Returns:
            Subsets: The subsets containing the splits.
        """
        sequences = [
            record[0].value for assay in dataset.assays for record in assay.records
        ]
        unique_sequences = _unique_sequences_for_targets(dataset, targets)
        self.random_state.shuffle(unique_sequences)

        records_shape = tuple(len(assay) for assay in dataset.assays)

        # Ensure all items are used due to rounding errors by treating the last
        # fraction separately
        sizes = [int(round(f * len(unique_sequences))) for f in self.fractions[:-1]]
        sizes.append(len(unique_sequences) - sum(sizes))

        slices, offset = [], 0
        for size in sizes:
            sequence_slice = unique_sequences[offset : offset + size]
            masks = _reshape_list(
                _sequences_to_mask(sequence_slice, all_sequences=sequences),
                records_shape,
            )

            assay_slices = []
            for mask, assay in zip(masks, dataset.assays, strict=True):
                target_names = [e.name for e in assay.fields]
                if targets is not None:
                    if not any(target in target_names for target in targets):
                        # Skipping the assay if none of the targets are present
                        columns = []
                    else:
                        columns = [assay.sequence_feature_name] + list(
                            set(targets) & set(target_names)
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
        n_splits: Number of folds. Must be at least 2.
        shuffle: Whether to shuffle the dataset before splitting.
            Defaults to False.
        random_state: Seed or random state for
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

    def split(self, dataset: Dataset, targets: list[str] | None = None) -> Subsets:
        """Splits the dataset into k folds for cross-validation.

        The unique sequences from the records of all assays that list at least one of
        the given targets, are split into k folds with approximately equal sizes.
        Each fold is used as a validation set once, while the remaining folds form
        the training set.

        Args:
            dataset: The dataset to split.
            targets: List of target field names to include in the
                splits. If None, all fields are included.

        Returns:
            list: A list of Subsets, where each Subset contains a training set
            and a validation set for one fold.
        """
        sequences = [
            record[0].value for assay in dataset.assays for record in assay.records
        ]
        unique_sequences = _unique_sequences_for_targets(dataset, targets)
        if self.shuffle:
            self.random_state.shuffle(unique_sequences)

        records_shape = tuple(len(assay) for assay in dataset.assays)

        # Split sequences into k folds
        sizes = [len(unique_sequences) // self.n_splits] * self.n_splits
        for i in range(len(unique_sequences) % self.n_splits):
            sizes[i] += 1

        slices, offset = [], 0
        for size in sizes:
            sequence_slice = unique_sequences[offset : offset + size]
            masks = _reshape_list(
                _sequences_to_mask(sequence_slice, all_sequences=sequences),
                records_shape,
            )

            assay_slices = []
            for mask, assay in zip(masks, dataset.assays, strict=True):
                target_names = [e.name for e in assay.fields]
                if targets is not None:
                    if not any(target in target_names for target in targets):
                        # Skipping the assay if none of the targets are present
                        columns = []
                    else:
                        columns = [assay.sequence_feature_name] + list(
                            set(targets) & set(target_names)
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


class PredefinedSplitter:
    """Split a dataset based on pre-defined splits from a column.

    Attributes:
        split_column: Name of the column containing split labels
            (e.g., 'train', 'val', 'test').
        split_order: Explicit order of split keys to return.
    """

    def __init__(self, split_column: str, split_order: list[str]) -> None:
        self.split_column = split_column
        self.split_order = split_order

    def _validate_split_column_is_present(self, dataset) -> None:
        """Checks if the split column is present in atleast one assay of the dataset"""
        for assay in dataset.assays:
            field_names = [f.name for f in assay.fields]
            if self.split_column in field_names:
                return
        raise ValueError(
            f"Split column '{self.split_column}' not found in any assay of the dataset."
        )

    def _collect_observed_values(self, dataset) -> set[str]:
        """Collect all unique split values from the dataset."""
        observed = set()
        for assay in dataset.assays:
            field_names = [f.name for f in assay.fields]
            if self.split_column not in field_names:
                continue
            col_idx = field_names.index(self.split_column)
            observed.update(record[col_idx] for record in assay.records)
        return observed

    def _validate_split_values(self, dataset) -> list[str]:
        """Checks if all observed values are in split_order and orders accordingly"""
        observed = self._collect_observed_values(dataset)
        order_set = set(self.split_order)

        # Check for unknown keys present in data
        unknown = observed - set(self.split_order)
        if unknown:
            raise ValueError(
                f"Found split values in dataset not in split_order: {sorted(unknown)}\n"
                f"Allowed split_order: {self.split_order}"
            )

        # Check for split_order keys not present in data
        missing = order_set - observed
        if missing:
            raise ValueError(
                f"Dataset is missing required split values from split_order.\n"
                f"  Missing keys: {sorted(missing)}\n"
                f"  Observed keys: {sorted(observed)}"
            )

        return list(self.split_order)

    def _validate_no_sequence_overlap(
        self, dataset: Dataset, split_values: list[str]
    ) -> None:
        """Validate that sequences don't appear in multiple splits."""
        split_sequences = {}

        for split_value in split_values:
            sequences = set()
            for assay in dataset.assays:
                field_names = [f.name for f in assay.fields]
                if self.split_column in field_names:
                    col_idx = field_names.index(self.split_column)
                    for record in assay.records:
                        if record[col_idx] == split_value:
                            sequences.add(record[0].value)
            split_sequences[split_value] = sequences

        for i, split1 in enumerate(split_values):
            for split2 in split_values[i + 1 :]:
                overlap = split_sequences[split1] & split_sequences[split2]
                if overlap:
                    raise ValueError(
                        f"Sequence overlap detected between '{split1}' "
                        f"and '{split2}' splits. "
                        f"Found {len(overlap)} overlapping sequence(s)."
                    )

    def split(self, dataset: Dataset, *, targets: list[str] | None = None) -> Subsets:
        """Splits the dataset based on pre-defined split column values.

        Args:
            dataset: The dataset to split.
            targets: List of target column names to include in the splits.
                If None, all columns are included.

        Returns:
            Subsets: The subsets containing the splits.

        Raises:
            ValueError: If sequences appear in multiple splits.
            ValueError: If the split column contains split values not in split order.
        """

        self._validate_split_column_is_present(dataset)
        split_values = self._validate_split_values(dataset)
        self._validate_no_sequence_overlap(dataset, split_values)

        # Create one subset per split value (e.g., train, val, test)
        slices = []
        for split_value in split_values:
            assay_slices = []
            for assay in dataset.assays:
                field_names = [f.name for f in assay.fields]

                # Split column doesn't exist in this assay, exclude all records
                if self.split_column not in field_names:
                    assay_slices.append(
                        AssaySlice(records=[False] * len(assay), columns=[])
                    )
                    continue

                col_idx = field_names.index(self.split_column)
                mask = [record[col_idx] == split_value for record in assay.records]

                # Determine which columns to include in the slice
                if targets is not None:
                    if not any(target in field_names for target in targets):
                        # Skip assay if none of the target columns exist
                        columns = []
                    else:
                        # Include sequence column plus requested target columns
                        columns = [assay.sequence_feature_name] + list(
                            set(targets) & set(field_names)
                        )
                else:
                    columns = None  # None include all columns by default

                assay_slices.append(AssaySlice(records=mask, columns=columns))

            slices.append(DatasetSlice(assays=assay_slices))

        subsets = Subsets(dataset=dataset, slices=slices)

        return subsets
