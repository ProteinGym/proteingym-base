import pytest

from proteingym.base import Dataset
from proteingym.base.splits import RandomSplitter


def test_random_splitter_raises_value_error_if_fractions_do_not_sum_to_one(
    empty_dataset: Dataset,
):
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must sum to 1."):
        RandomSplitter(dataset=empty_dataset, fractions=[0.7, 0.3, 0.1])
