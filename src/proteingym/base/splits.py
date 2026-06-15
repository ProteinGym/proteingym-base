"""The splits module provides functionality for splitting datasets.

For example, split dataset for machine learning into training, validation, and
test sets.

Todo:
----
- Introduce parent Splitter class when splitter patterns emerge.
"""

import logging
import numbers

import numpy as np
import numpy.typing as npt
from Bio.Seq import Seq

from .assay import SEQUENCE, AssaySlice
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
    """Subsample True values in a boolean mask.

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


def _split_mask_into_folds(
    mask: npt.NDArray,
    n_splits: int,
    *,
    shuffle: bool = False,
    random_state: int | np.random.RandomState | None = None,
) -> list[npt.NDArray]:
    """Split the True values of a boolean mask into folds.

    The indices where the mask is True are partitioned into ``n_splits`` folds of
    approximately equal size (the remainder is distributed over the first folds).
    Each returned mask is True only at the indices belonging to that fold, so the
    folds are mutually exclusive and their union equals the input mask.

    Args:
        mask: Boolean array to split.
        n_splits: Number of folds to create.
        shuffle: Whether to shuffle the True indices before splitting.
        random_state: reproducibility. If None, the global numpy random state is used.

    Returns:
        list[npt.NDArray]: A list of ``n_splits`` boolean masks, one per fold.
    """
    true_indices = np.where(mask)[0]
    if shuffle:
        random_state = _check_random_state(random_state)
        random_state.shuffle(true_indices)

    n_true = len(true_indices)
    sizes = [n_true // n_splits] * n_splits
    for i in range(n_true % n_splits):
        sizes[i] += 1

    folds, offset = [], 0
    for size in sizes:
        fold_mask = np.zeros_like(mask, dtype=bool)
        fold_mask[true_indices[offset : offset + size]] = True
        folds.append(fold_mask)
        offset += size
    return folds


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


def _assays_contain_target(dataset: Dataset, target: str) -> list[bool]:
    """For each assay in the dataset, whether it contains the given target field."""
    return [
        target in [field.name for field in assay.fields] for assay in dataset.assays
    ]


def _check_single_variable_combination(
    dataset: Dataset, *, assays_contain_target: list[bool]
) -> None:
    """Validate that the assays combined for a target share one variable combination.

    Quantile splitting derives a single threshold from the target values pooled across
    all assays that contain the target. That threshold is only meaningful if those
    values are comparable. When the combined assays differ in their ``variables`` (e.g.
    measured at different pH), a target value carries a different meaning under each
    combination and a shared threshold is ill-defined.

    Args:
        dataset: The dataset to split.
        assays_contain_target: Per-assay flag whether the assay contains the target,
            aligned with ``dataset.assays``.

    Raises:
        ValueError: If the combined assays span more than one variable combination.
    """
    variable_names = [variable.name for variable in dataset.assay_variables]
    combinations = {
        tuple((name, assay.variables.get(name)) for name in variable_names)
        for assay, contains_target in zip(
            dataset.assays, assays_contain_target, strict=True
        )
        if contains_target
    }
    if len(combinations) > 1:
        raise ValueError(
            "Quantile splitting does not support combining assays with varying assay "
            "variables."
        )


def _target_assay_slices(
    dataset: Dataset,
    *,
    target: str,
    selected_sequences: set[Seq],
    assays_contain_target: list[bool],
) -> list[AssaySlice]:
    """Build per-assay slices selecting the records of the given variant sequences.

    Every record of a selected sequence is included in every assay the sequence appears
    in. This keeps a variant on a single side of the split.

    Args:
        dataset: The dataset whose assays are sliced.
        target: Target field name retained in the slices.
        selected_sequences: The sequence strings of the variants to include.
        assays_contain_target: Per-assay flag whether the assay contains the target,
            aligned with ``dataset.assays``.

    Returns:
        list[AssaySlice]: One slice per assay, positionally aligned with
        ``dataset.assays``. Assays without the target yield an empty slice.
    """
    assay_slices = []
    for assay, contains_target in zip(
        dataset.assays, assays_contain_target, strict=True
    ):
        if not contains_target:
            assay_slices.append(AssaySlice(records=None, columns=[]))
            continue
        assay_sequences = [Seq(record[0].value) for record in assay.records]
        mask = _sequences_to_mask(
            list(selected_sequences), all_sequences=assay_sequences
        )
        assay_slices.append(
            AssaySlice(records=mask, columns=[assay.sequence_feature_name, target])
        )
    return assay_slices


def _count_high_property_variants(
    dataset: Dataset, test_slice: DatasetSlice, *, target: str, threshold: float
) -> int:
    """Count the high-property variants present in a test slice.

    The count is computed from the same aggregated view the user consumes, i.e.
    ``Dataset.to_df``, so it remains correct even when assays sharing sequences are
    combined and their measurements aggregated. A high-property variant is an
    aggregated record whose target value exceeds ``threshold``.

    Args:
        dataset: The dataset that is sliced.
        test_slice: The test slice to inspect.
        target: Target field name on which the threshold is defined.
        threshold: The quantile threshold separating low- and high-property variants.

    Returns:
        int: The number of high-property variants in the test slice.
    """
    df = dataset[test_slice].to_df(target_names=[target])
    if df.is_empty():
        return 0
    return int((df[target] > threshold).sum())


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
        """Splits the dataset into training and test sets based on quantile thresholds.

        The quantile threshold is calculated on the combined, aggregated view of the
        target obtained from :meth:`Dataset.to_df`, so that assays sharing the target
        contribute to a single threshold rather than one threshold each. The threshold
        divides the unique variants into a lower and an upper interval. The training set
        is composed by sampling self.fraction from the lower interval, and the test set
        is composed by sampling 1 - self.fraction from the upper interval, and the
        remaining lower-interval variants.

        Splitting is done per variant (identified by its sequence): a variant is
        assigned to a single side of the split together with all of its records across
        all assays. The resulting test slice is tagged with ``top_k`` in its metadata,
        the number of high-property variants (aggregated target value exceeding the
        threshold) it contains.

        Note:
            ``top_k`` is defined with respect to the default aggregation used by
            :meth:`Dataset.to_df` (mean for numeric targets). Variants are identified by
            sequence, consistent with the other splitters.

        Args:
            dataset: The dataset to split.
            target: Target field name to include in the
                splits.

        Returns:
            Subsets: The subsets containing the splits.
        """
        assays_contain_target = _assays_contain_target(dataset, target)
        if not any(assays_contain_target):
            empty = [AssaySlice(records=None, columns=[]) for _ in dataset.assays]
            train_dataset_slice = DatasetSlice(assays=empty)
            test_dataset_slice = DatasetSlice(assays=empty, metadata={"top_k": 0})
            return Subsets(
                dataset=dataset, slices=[train_dataset_slice, test_dataset_slice]
            )

        _check_single_variable_combination(
            dataset, assays_contain_target=assays_contain_target
        )
        df = dataset.to_df(target_names=[target])
        if not df[target].dtype.is_numeric():
            raise ValueError(
                f"QuantileSplitter requires a numeric target, but '{target}' is "
                f"{df[target].dtype}."
            )
        target_values = df[target].to_numpy()
        sequences = [Seq(s) for s in df[SEQUENCE]]
        threshold = float(np.quantile(target_values, self.quantile))

        lower_mask = target_values <= threshold
        upper_mask = target_values > threshold
        train_mask = _subsample_mask(
            lower_mask, fraction=self.fraction, random_state=self.random_state
        )
        test_upper_mask = _subsample_mask(
            upper_mask, fraction=1 - self.fraction, random_state=self.random_state
        )
        test_mask = test_upper_mask | (lower_mask & ~train_mask)

        train_sequences = {
            s for s, keep in zip(sequences, train_mask, strict=True) if keep
        }
        test_sequences = {
            s for s, keep in zip(sequences, test_mask, strict=True) if keep
        }

        train_assay_slices = _target_assay_slices(
            dataset,
            target=target,
            selected_sequences=train_sequences,
            assays_contain_target=assays_contain_target,
        )
        test_assay_slices = _target_assay_slices(
            dataset,
            target=target,
            selected_sequences=test_sequences,
            assays_contain_target=assays_contain_target,
        )

        train_dataset_slice = DatasetSlice(assays=train_assay_slices)
        test_dataset_slice = DatasetSlice(assays=test_assay_slices)
        top_k = _count_high_property_variants(
            dataset, test_dataset_slice, target=target, threshold=threshold
        )
        test_dataset_slice = DatasetSlice(
            assays=test_assay_slices, metadata={"top_k": top_k}
        )
        subsets = Subsets(
            dataset=dataset, slices=[train_dataset_slice, test_dataset_slice]
        )
        return subsets


class KFoldQuantileSplitter:
    """Split a dataset into k folds, reserving high-property variants for testing.

    Like the QuantileSplitter, a quantile threshold divides the data for a single
    target into a lower and an upper interval. Both intervals are then randomly split
    into k folds, similar to the KFoldSplitter. For each fold, a dedicated training
    set and test set are created: the test set of fold i combines fold i of the upper
    interval with fold i of the lower interval, while the training set of fold i
    combines every fold except fold i from only the lower interval.

    This split is only defined for a single target in the dataset, because the
    quantile threshold can only be defined for a single target.

    Args:
        quantile: A float between 0 and 1 used to derive the percentile that will be
            used as a threshold. Values exceeding the threshold are considered the hit
            variants.
        n_splits: Number of folds. Must be at least 2.
        shuffle: Whether to shuffle the masks before splitting them into folds.
            Defaults to False.
        random_state: Seed or random state for reproducibility. If None, the global
            numpy random state is used.
    """

    def __init__(
        self,
        quantile: float,
        n_splits: int,
        *,
        shuffle: bool = False,
        random_state: int | np.random.RandomState | None = None,
    ) -> None:
        if not 0 <= quantile <= 1:
            raise ValueError("Quantile must lie between 0 and 1.")
        if n_splits < 2:
            raise ValueError("Number of splits must be at least 2.")
        if not shuffle and random_state is not None:
            logger.warning("random_state is ignored when shuffle is False.")
        self.quantile = quantile
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.random_state = _check_random_state(random_state)

    def split(self, dataset: Dataset, *, target: str) -> tuple[Subsets, Subsets]:
        """Splits the dataset into a Subsets object storing k training and test sets.

        For a single target, the quantile threshold is calculated based on
        self.quantile. The threshold is used to divide the data into an upper and lower
        interval. Both intervals are split into self.n_splits folds. For fold i, the
        test set is composed of fold i of the upper interval and fold i of the lower
        interval, while the training set is composed of every fold except fold i from
        only the lower interval.

        The two resulting Subsets stores their slices as lists of folds with paired
        ordering. The former contains all training folds, and the latter all tests
        folds.

        Args:
            dataset: The dataset to split.
            target: Target field name to include in the splits.

        Returns:
            Subsets: The subsets containing the splits.
        """
        assays_contain_target = _assays_contain_target(dataset, target)
        train_slices = []
        test_slices = []
        if not any(assays_contain_target):
            for _ in range(self.n_splits):
                empty = [AssaySlice(records=None, columns=[]) for _ in dataset.assays]
                train_slices.append(DatasetSlice(assays=empty))
                test_slices.append(DatasetSlice(assays=empty, metadata={"top_k": 0}))
            return Subsets(dataset=dataset, slices=train_slices), Subsets(
                dataset=dataset, slices=test_slices
            )

        _check_single_variable_combination(
            dataset, assays_contain_target=assays_contain_target
        )
        df = dataset.to_df(target_names=[target])
        if not df[target].dtype.is_numeric():
            raise ValueError(
                f"KFoldQuantileSplitter requires a numeric target, but '{target}' is "
                f"{df[target].dtype}."
            )
        target_values = df[target].to_numpy()
        sequences = [Seq(s) for s in df[SEQUENCE].to_list()]
        threshold = float(np.quantile(target_values, self.quantile))

        lower_mask = target_values <= threshold
        upper_mask = target_values > threshold
        lower_folds = _split_mask_into_folds(
            lower_mask,
            self.n_splits,
            shuffle=self.shuffle,
            random_state=self.random_state,
        )
        upper_folds = _split_mask_into_folds(
            upper_mask,
            self.n_splits,
            shuffle=self.shuffle,
            random_state=self.random_state,
        )

        for fold in range(self.n_splits):
            test_mask = upper_folds[fold] | lower_folds[fold]
            train_mask = np.zeros_like(lower_mask, dtype=bool)
            for other in range(self.n_splits):
                if other != fold:
                    train_mask |= lower_folds[other]

            train_sequences = {
                s for s, keep in zip(sequences, train_mask, strict=True) if keep
            }
            test_sequences = {
                s for s, keep in zip(sequences, test_mask, strict=True) if keep
            }

            train_assay_slices = _target_assay_slices(
                dataset,
                target=target,
                selected_sequences=train_sequences,
                assays_contain_target=assays_contain_target,
            )
            test_assay_slices = _target_assay_slices(
                dataset,
                target=target,
                selected_sequences=test_sequences,
                assays_contain_target=assays_contain_target,
            )

            test_dataset_slice = DatasetSlice(assays=test_assay_slices)
            top_k = _count_high_property_variants(
                dataset, test_dataset_slice, target=target, threshold=threshold
            )
            train_slices.append(DatasetSlice(assays=train_assay_slices))
            test_slices.append(
                DatasetSlice(assays=test_assay_slices, metadata={"top_k": top_k})
            )
        train_subsets = Subsets(dataset=dataset, slices=train_slices)
        test_subsets = Subsets(dataset=dataset, slices=test_slices)
        return train_subsets, test_subsets


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
        """Checks if the split column is present in atleast one assay of the dataset."""
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
        """Checks if all observed values are in split_order and orders accordingly."""
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
