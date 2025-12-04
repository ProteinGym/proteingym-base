import functools

import polars as pl
import polars.testing
import pytest

from proteingym.base.dataset import Dataset, Subsets
from proteingym.base.splits import (
    KFoldSplitter,
    RandomSplitter,
    _cast_indices_to_mask,
    _reshape_list,
)


@pytest.mark.parametrize(
    "indices, length, expected",
    [
        ([0, 2, 4], 6, [True, False, True, False, True, False]),
        ([1, 3], 5, [False, True, False, True, False]),
        ([], 4, [False, False, False, False]),
    ],
)
def test_cast_indices_to_mask(
    indices: list[int], length: int, expected: list[bool]
) -> None:
    """Unit test the _cast_indices_to_mask function."""
    assert _cast_indices_to_mask(indices, length=length) == expected


@pytest.mark.parametrize(
    "flat_list, shape, expected",
    [
        ([1, 2, 3, 4], (1, 3), [[1], [2, 3, 4]]),
        ([1, 2, 3, 4], (4,), [[1, 2, 3, 4]]),
        ([1, 2, 3, 4, 5, 6], (2, 2, 2), [[1, 2], [3, 4], [5, 6]]),
    ],
)
def test_reshape_list(
    flat_list: list[int], shape: tuple[int, ...], expected: list[int]
) -> None:
    """Unit test the _reshape_list function."""
    assert _reshape_list(flat_list, shape) == expected


def test_random_splitter_raises_value_error_if_fractions_do_not_sum_to_one() -> None:
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must sum to 1."):
        RandomSplitter(fractions=[0.7, 0.3, 0.1])


def test_random_splitter_raises_value_error_if_fraction_below_zero() -> None:
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must be positive numbers."):
        RandomSplitter(fractions=[0.7, 0.4, -0.1])


def test_random_splitter_splits_length(dataset_empty: Dataset) -> None:
    """Test that RandomSplitter splits the dataset into the correct number of slices."""
    fractions = [0.8, 0.2]
    splitter = RandomSplitter(fractions)
    subsets = splitter.split(dataset_empty)
    assert len(subsets) == len(fractions)


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_empty_assay",
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    "fractions",
    [
        [0.5, 0.5],  # Each split with one record
        [0.9, 0.1],  # One split with no records
    ],
)
def test_random_splitter_splits_in_dataset(
    dataset: Dataset, fractions: list[float]
) -> None:
    """Test that RandomSplitter splits the dataset into the correct number of slices."""
    splitter = RandomSplitter(fractions)
    subsets = splitter.split(dataset)
    for i, split in enumerate(subsets):
        assert split in dataset, f"Split {i + 1} not in original dataset."


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
def test_random_splitter_splits_are_disjoint(dataset: Dataset) -> None:
    """Test that RandomSplitter splits are disjoint."""
    fractions = [0.5, 0.5]
    splitter = RandomSplitter(fractions)
    split_first, split_second = tuple(splitter.split(dataset=dataset))
    assert split_first not in split_second
    assert split_second not in split_first


def test_kfold_splitter_raises_value_error_if_n_splits_below_two() -> None:
    """Test that KFoldSplitter raises ValueError if n_splits is below 2."""
    with pytest.raises(ValueError, match="Number of splits must be at least 2."):
        KFoldSplitter(n_splits=1)


@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_splitter_splits_length(dataset_empty: Dataset, n_splits: int) -> None:
    """Test that KFoldSplitter splits the dataset into the correct number of folds."""
    splitter = KFoldSplitter(n_splits=n_splits)
    superset = splitter.split(dataset_empty)
    assert len(superset) == n_splits


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_empty_assay",
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_splitter_splits_in_dataset(dataset: Dataset, n_splits: int) -> None:
    """Test that KFoldSplitter splits the dataset into the correct number of slices."""
    splitter = KFoldSplitter(n_splits=n_splits)
    superset = splitter.split(dataset)
    for i, split in enumerate(superset):
        assert split in dataset, f"Split {i + 1} not in original dataset."


def test_kfold_splitter_splits_are_disjoint(dataset_with_assays: Dataset) -> None:
    """Test that KFoldSplitter splits are disjoint."""
    splitter = KFoldSplitter(n_splits=2)
    superset = splitter.split(dataset_with_assays)
    split_first, split_second = tuple(superset)
    assert split_first not in split_second
    assert split_second not in split_first


@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_splitter_splits_contain_all_records(
    dataset_with_assays: Dataset, n_splits: int
) -> None:
    """Test that KFoldSplitter splits contain all records from the original dataset."""
    splitter = KFoldSplitter(n_splits=n_splits)
    subsets = splitter.split(dataset_with_assays)
    dataset_with_all_splits = functools.reduce(lambda d1, d2: d1 | d2, subsets)
    # Using a dataframe comparison here as the dataset reconstructed from the
    # folds will have the records spread over multiple assays
    pl.testing.assert_frame_equal(
        dataset_with_assays.to_df(),
        dataset_with_all_splits.to_df(),
        check_dtypes=False,
        check_column_order=False,
    )


@pytest.mark.parametrize(
    "splitter",
    [
        RandomSplitter(fractions=[0.5, 0.5]),
        KFoldSplitter(n_splits=2),
    ],
)
def test_splitter_splits_with_targets_columns(
    dataset_with_assay: Dataset,
    splitter: RandomSplitter | KFoldSplitter,
) -> None:
    """A split with targets should contain the target and sequence columns."""
    expected_columns = ["sequence", "DMS Score"]
    splits = splitter.split(dataset_with_assay, targets=["DMS Score"])
    assays = [assay for split in splits for assay in split.assays]
    assert all(expected_columns == assay.fields for assay in assays)


@pytest.mark.parametrize(
    "splitter",
    [
        RandomSplitter(fractions=[0.5, 0.5]),
        KFoldSplitter(n_splits=2),
    ],
)
def test_splitter_splits_with_target_not_in_all_assays(
    dataset_with_assays: Dataset,
    splitter: RandomSplitter | KFoldSplitter,
) -> None:
    """If a target is not in all assays, the assays without the targets are empty."""
    splits = splitter.split(dataset_with_assays, targets=["stability"])
    assays = [assay for split in splits for assay in split.assays]
    assert all(assay.is_empty() for assay in assays if "stability" not in assay.fields)
    # Make sure we do not lose all data
    assert any(not split.to_df().is_empty() for split in splits)


def test_random_splitter_combining_split_targets(dataset_with_assays: Dataset) -> None:
    """Test that different splits for different targets can be combined."""
    subsets = Subsets(dataset=dataset_with_assays)

    splitter = RandomSplitter(fractions=[0.5, 0.5])
    subsets.update(
        random_dms_score=splitter.split(dataset_with_assays, targets=["DMS Score"])
    )
    subsets.update(
        random_stability=splitter.split(dataset_with_assays, targets=["stability"])
    )

    assays = [assay for split in subsets["random_dms_score"] for assay in split.assays]
    expected_columns = ["sequence", "DMS Score"]
    assert all(expected_columns == assay.fields for assay in assays if assay.fields)

    assays = [assay for split in subsets["random_stability"] for assay in split.assays]
    expected_columns = ["sequence", "stability"]
    assert all(expected_columns == assay.fields for assay in assays if assay.fields)


def test_splitters_combining_split_strategies(dataset_with_assays: Dataset) -> None:
    """Test that different split strategies can be combined."""
    subsets = Subsets(dataset=dataset_with_assays)

    random_splitter = RandomSplitter(fractions=[0.5, 0.5])
    subsets.update(random=random_splitter.split(dataset_with_assays))

    kfold_splitter = KFoldSplitter(n_splits=2)
    subsets.update(kfold=kfold_splitter.split(dataset_with_assays))

    assert "random" in subsets.slices and len(subsets.slices["random"]) == 2
    assert "kfold" in subsets.slices and len(subsets.slices["kfold"]) == 2
