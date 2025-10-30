from pathlib import Path
from zipfile import ZipFile

import pytest

from proteingym.base.dataset import Dataset, DatasetSlice, Subsets


def test_subsets_iterate_over_empty(dataset_empty: Dataset) -> None:
    """Iterating over an empty collection of subsets does not yield any elements."""
    subsets = Subsets(dataset=dataset_empty, slices=[])
    for _ in subsets:
        raise AssertionError("Should not iterate over empty collection of subsets")


@pytest.mark.parametrize(
    "slices, length",
    [([], 0), ([True, False], 2)],
)
def test_subsets_length(dataset_empty: Dataset, slices: list, length: int) -> None:
    """Test subsets length equal to number of slices."""
    subsets = Subsets(dataset=dataset_empty, slices=slices)
    assert len(subsets) == length


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
]


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_subsets_iterate_over_single_full_slice(dataset: Dataset) -> None:
    """Iterating over subsets with a single full slice yields the entire dataset."""
    slc = DatasetSlice(assays=[[True] * len(assay) for assay in dataset.assays])
    subsets = Subsets(dataset=dataset, slices=[slc])
    assert list(subsets) == [dataset]


@pytest.fixture
def subsets_fifty_fifty(dataset_with_assay: Dataset) -> Subsets:
    """Subsets that cut a dataset with two assay records in halfs."""
    slc1 = DatasetSlice(assays=[[True, False]])
    slc2 = DatasetSlice(assays=[[False, True]])
    subsets = Subsets(dataset=dataset_with_assay, slices=[slc1, slc2])
    return subsets


def test_subsets_iterate_over_dataset_cut_in_half(
    subsets_fifty_fifty: Subsets,
) -> None:
    """Iterating over subsets which cuts the dataset in halfs yields two datasets."""
    datasets = list(subsets_fifty_fifty)
    assert len(datasets) == 2
    assert datasets[0] != datasets[1]


def test_subsets_dump_from_path_is_unit_function(
    tmp_path: Path, subsets_fifty_fifty: Subsets
) -> None:
    """Dumping and loading subsets is a unit function."""
    archive_path = subsets_fifty_fifty.dump(path=tmp_path)
    subsets_recovered = Subsets.from_path(archive_path)
    assert subsets_fifty_fifty == subsets_recovered


def test_subsets_dump_creates_non_empty_file(
    tmp_path: Path, subsets_fifty_fifty: Subsets
) -> None:
    """Dumping a subsets creates a non-empty file."""
    archive_path = subsets_fifty_fifty.dump(path=tmp_path)
    assert archive_path.is_file()
    assert archive_path.stat().st_size > 0


def test_subsets_dump_archive_extension(
    tmp_path: Path, subsets_fifty_fifty: Subsets
) -> None:
    """Validate the archive extension of a dumped subsets."""
    archive_path = subsets_fifty_fifty.dump(path=tmp_path)
    assert archive_path.as_posix().endswith(".splits.pgdata")


def test_subsets_dump_creates_valid_archive(
    tmp_path: Path, subsets_fifty_fifty: Subsets
) -> None:
    """Dumping a subsets creates a valid archive."""
    archive_path = subsets_fifty_fifty.dump(path=tmp_path)
    with ZipFile(archive_path, "r") as zip:
        assert zip.testzip() is None  # No corrupt files
