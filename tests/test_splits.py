import pytest

from proteingym.base import Dataset
from proteingym.base.splits import RandomSplitter


def test_random_splitter_raises_value_error_if_fractions_do_not_sum_to_one(
    empty_dataset: Dataset,
):
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must sum to 1."):
        RandomSplitter(dataset=empty_dataset, fractions=[0.7, 0.3, 0.1])


def test_random_splitter_raises_value_error_if_fraction_below_zero(
    empty_dataset: Dataset,
):
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must be positive numbers."):
        RandomSplitter(dataset=empty_dataset, fractions=[0.7, 0.4, -0.1])


def test_random_splitter_splits_length(empty_dataset: Dataset):
    """Test that RandomSplitter splits the dataset into the correct number of slices."""
    fractions = [0.8, 0.2]
    splitter = RandomSplitter(dataset=empty_dataset, fractions=fractions)
    superset = splitter.split()
    assert len(superset) == len(fractions)
