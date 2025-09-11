"""
Module for testing dataset operators.
"""

import pytest
from Bio.Seq import Seq

from pg2_dataset.assay import Assay
from pg2_dataset.dataset import Dataset
from pg2_dataset.sequence import Sequence, SequenceAlphabet, SequenceType


@pytest.fixture
def empty_dataset() -> Dataset:
    """An empty dataset."""
    dataset = Dataset(
        name="empty_dataset",
        description="An empty dataset for testing purposes.",
        assay_conditions=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assay() -> Dataset:
    """A dataset containing a single assay."""
    assay = Assay(name="assay1", records=[("SEQ1", 1.0)])
    dataset = Dataset(
        name="dataset_with_single_assay",
        description="A dataset containing a single assay.",
        assay_conditions=[],
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_sequence() -> Dataset:
    """A dataset containing a single sequence."""
    sequence = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    dataset = Dataset(
        name="dataset_with_single_sequence",
        description="A dataset containing a single sequence.",
        assay_conditions=[],
        assays=[],
        sequences=[sequence],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def datasets(
    empty_dataset: Dataset, dataset_with_assay: Dataset, dataset_with_sequence: Dataset
) -> list[Dataset]:
    """All test datasets."""
    return [empty_dataset, dataset_with_assay, dataset_with_sequence]


@pytest.fixture
def dataset(request: pytest.FixtureRequest, datasets: list[Dataset]) -> Dataset:
    """A generic dataset for testing.

    Args:
        request (pytest.FixtureRequest): The pytest request object.
            Expecting to contain the dataset name in `request.param`.

    Returns:
        Dataset: The dataset with the requested name.
    """
    param = getattr(request, "param", "UNKNOWN")
    dataset = next((d for d in datasets if d.name == param), None)
    if dataset is None:
        raise ValueError(f"Unknown dataset: {param}")
    return dataset


ALL_DATASET_NAMES = [
    "empty_dataset",
    "dataset_with_single_assay",
    "dataset_with_single_sequence",
]


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_dataset_equals_itself(dataset: Dataset) -> None:
    """A dataset should equal itself."""
    assert dataset == dataset


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_dataset_contains_itself(dataset: Dataset) -> None:
    """A dataset should contain itself."""
    assert dataset in dataset
