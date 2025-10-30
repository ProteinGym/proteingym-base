"""
Module for testing dataset operators.
"""

from functools import reduce

import pytest

from proteingym.base.dataset import Dataset

ALL_DATASET_NAMES = [
    "dataset_empty",
    "dataset_with_single_assay",
    "dataset_with_multiple_assays",
    "dataset_with_single_sequence",
    "dataset_with_multiple_sequences",
    "dataset_with_single_structure",
    "dataset_with_multiple_structures",
    "dataset_with_single_msa",
    "dataset_with_multiple_msas",
    "dataset_with_everything",
]


def test_dataset_not_equals_integer(dataset_empty: Dataset) -> None:
    """A dataset should not equal an integer."""
    assert dataset_empty != 1


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_dataset_equals_itself(dataset: Dataset) -> None:
    """A dataset should equal itself."""
    assert dataset == dataset


def test_dataset_does_not_contain_integer(dataset_empty: Dataset) -> None:
    """A dataset should not contain an integer."""
    assert 1 not in dataset_empty


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_dataset_contains_itself(dataset: Dataset) -> None:
    """A dataset should contain itself."""
    assert dataset in dataset


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_dataset_always_contains_dataset_empty(
    dataset_empty: Dataset, dataset: Dataset
) -> None:
    """An empty dataset should be contained in any dataset."""
    assert dataset_empty in dataset


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_empty",
        "dataset_with_single_sequence",
        "dataset_with_single_structure",
        "dataset_with_single_msa",
    ],
    indirect=True,
)
def test_dataset_with_single_assay_not_in(
    dataset_with_assay: Dataset, dataset: Dataset
) -> None:
    """A dataset with a single assay should not be contained in the other dataset."""
    assert dataset_with_assay not in dataset


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_empty",
        "dataset_with_single_assay",
        "dataset_with_single_structure",
        "dataset_with_single_msa",
    ],
    indirect=True,
)
def test_dataset_with_single_sequence_not_in(
    dataset_with_sequence: Dataset, dataset: Dataset
) -> None:
    """A dataset with a single sequence should not be contained in the other dataset."""
    assert dataset_with_sequence not in dataset


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_empty",
        "dataset_with_single_assay",
        "dataset_with_single_sequence",
        "dataset_with_single_msa",
    ],
    indirect=True,
)
def test_dataset_with_single_structure_not_in(
    dataset_with_structure: Dataset, dataset: Dataset
) -> None:
    """A dataset with a single struct should not be contained in the other dataset."""
    assert dataset_with_structure not in dataset


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_empty",
        "dataset_with_single_assay",
        "dataset_with_single_sequence",
        "dataset_with_single_structure",
    ],
    indirect=True,
)
def test_dataset_with_single_msa_not_in(
    dataset_with_msa: Dataset, dataset: Dataset
) -> None:
    """A dataset with a single msa should not be contained in the other dataset."""
    assert dataset_with_msa not in dataset


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
@pytest.mark.parametrize("dataset2", ALL_DATASET_NAMES, indirect=True)
def test_dataset_union_contains_both(dataset: Dataset, dataset2: Dataset) -> None:
    """The union of two datasets should contain both datasets."""
    union = dataset | dataset2
    assert dataset in union
    assert dataset2 in union

    # If one dataset is not a subset of the other, then both should not be equal
    # to the union
    is_subset = dataset in dataset2 or dataset2 in dataset
    assert is_subset or dataset != union
    assert is_subset or dataset2 != union


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_dataset_with_everything_all_contains_other(
    datasets: list[Dataset], dataset: Dataset
) -> None:
    """A dataset with everything should always contain any other dataset."""
    dataset_with_all = reduce(lambda d1, d2: d1 | d2, datasets)
    assert dataset in dataset_with_all


def test_dataset_union_keeps_descriptions(
    dataset_empty: Dataset, dataset_with_assay: Dataset
) -> None:
    """The union of two datasets should keep the description of both dataset."""
    union = dataset_empty | dataset_with_assay
    assert dataset_empty.description in union.description
    assert dataset_with_assay.description in union.description
