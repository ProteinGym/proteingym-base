import pytest

from proteingym.base import Dataset
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


def test_random_splitter_raises_value_error_if_fractions_do_not_sum_to_one(
    dataset_empty: Dataset,
) -> None:
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must sum to 1."):
        RandomSplitter(dataset=dataset_empty, fractions=[0.7, 0.3, 0.1])


def test_random_splitter_raises_value_error_if_fraction_below_zero(
    dataset_empty: Dataset,
) -> None:
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must be positive numbers."):
        RandomSplitter(dataset=dataset_empty, fractions=[0.7, 0.4, -0.1])


def test_random_splitter_splits_length(dataset_empty: Dataset) -> None:
    """Test that RandomSplitter splits the dataset into the correct number of slices."""
    fractions = [0.8, 0.2]
    splitter = RandomSplitter(dataset=dataset_empty, fractions=fractions)
    superset = splitter.split()
    assert len(superset) == len(fractions)


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
    splitter = RandomSplitter(dataset=dataset, fractions=fractions)
    superset = splitter.split()
    for i, split in enumerate(superset):
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
    splitter = RandomSplitter(dataset=dataset, fractions=fractions)
    split_first, split_second = tuple(splitter.split())
    assert split_first not in split_second
    assert split_second not in split_first


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
def test_kfold_splitter_splits_length(dataset: Dataset, n_splits: int) -> None:
    """Test that KFoldSplitter splits the dataset into the correct number of folds."""
    splitter = KFoldSplitter(dataset=dataset, n_splits=n_splits)
    superset = splitter.split()
    assert len(superset) == n_splits


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_assay_empty",
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_splitter_splits_in_dataset(dataset: Dataset, n_splits: int) -> None:
    """Test that KFoldSplitter splits the dataset into the correct number of slices."""
    splitter = KFoldSplitter(dataset=dataset, n_splits=n_splits)
    superset = splitter.split()
    for i, split in enumerate(superset):
        assert split in dataset, f"Split {i + 1} not in original dataset."


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_assay_empty",
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_splitter_splits_are_disjoint(dataset: Dataset, n_splits: int) -> None:
    """Test that KFoldSplitter splits are disjoint."""
    splitter = KFoldSplitter(dataset=dataset, n_splits=n_splits)
    superset = splitter.split()
    for i, split_first in enumerate(superset):
        for j, split_second in enumerate(superset):
            if i == j:
                continue
            assert split_first not in split_second
            assert split_second not in split_first
