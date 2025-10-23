import pytest

from proteingym.base import Dataset
from proteingym.base.splits import RandomSplitter


def test_random_splitter_raises_value_error_if_fractions_do_not_sum_to_one(
    empty_dataset: Dataset,
) -> None:
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must sum to 1."):
        RandomSplitter(dataset=empty_dataset, fractions=[0.7, 0.3, 0.1])


def test_random_splitter_raises_value_error_if_fraction_below_zero(
    empty_dataset: Dataset,
) -> None:
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must be positive numbers."):
        RandomSplitter(dataset=empty_dataset, fractions=[0.7, 0.4, -0.1])


def test_random_splitter_splits_length(empty_dataset: Dataset) -> None:
    """Test that RandomSplitter splits the dataset into the correct number of slices."""
    fractions = [0.8, 0.2]
    splitter = RandomSplitter(dataset=empty_dataset, fractions=fractions)
    superset = splitter.split()
    assert len(superset) == len(fractions)


@pytest.mark.parametrize(
    "fractions",
    [
        [0.5, 0.5],  # Each splits with one record
        [0.9, 0.1],  # One split with no records
    ],
)
def test_random_splitter_splits_in_dataset(
    dataset_with_assay: Dataset, fractions: list[float]
) -> None:
    """Test that RandomSplitter splits the dataset into the correct number of slices."""
    splitter = RandomSplitter(dataset=dataset_with_assay, fractions=fractions)
    superset = splitter.split()
    for i, split in enumerate(superset):
        assert split in dataset_with_assay, f"Split {i + 1} not in original dataset."


def test_random_splitter_splits_are_disjoint(dataset_with_assay: Dataset) -> None:
    """Thest that RandomSplitter splits are disjoint."""
    fractions = [0.5, 0.5]
    splitter = RandomSplitter(dataset=dataset_with_assay, fractions=fractions)
    split_first, split_second = list(splitter.split())
    assert split_first not in split_second
    assert split_second not in split_first
