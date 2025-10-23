from pathlib import Path
from zipfile import ZipFile

import pytest

from proteingym.base.dataset import Dataset, DatasetSlice
from proteingym.base.superset import Superset


def test_superset_iterate_over_empty(dataset_empty: Dataset) -> None:
    """Test that iterating over an empty superset does not yield any elements."""
    superset = Superset(dataset=dataset_empty, slices=[])
    for _ in superset:
        raise AssertionError("Should not iterate over empty superset")


@pytest.mark.parametrize(
    "slices, length",
    [([], 0), ([True, False], 2)],
)
def test_superset_length(dataset_empty: Dataset, slices: list, length: int) -> None:
    """Test that iterating over an empty superset does not yield any elements."""
    superset = Superset(dataset=dataset_empty, slices=slices)
    assert len(superset) == length


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
def test_superset_iterate_over_single_full_slice(dataset: Dataset) -> None:
    """Iterating over a superset with a single full slice yields the entire dataset."""
    slc = DatasetSlice(assays=[[True] * len(assay) for assay in dataset.assays])
    superset = Superset(dataset=dataset, slices=[slc])
    assert list(superset) == [dataset]


@pytest.fixture
def superset_fifty_fifty(dataset_with_assay: Dataset) -> Superset:
    """A superset which cuts a dataset with two assays in half."""
    slc1 = DatasetSlice(assays=[[True, False]])
    slc2 = DatasetSlice(assays=[[False, True]])
    superset = Superset(dataset=dataset_with_assay, slices=[slc1, slc2])
    return superset


def test_superset_iterate_over_dataset_cut_in_half(
    superset_fifty_fifty: Superset,
) -> None:
    """Iterating over a superset which cuts the dataset in half yields two datasets."""
    datasets = list(superset_fifty_fifty)
    assert len(datasets) == 2
    assert datasets[0] != datasets[1]


def test_superset_dump_from_path_is_unit_function(
    tmp_path: Path, superset_fifty_fifty: Superset
) -> None:
    """Dumping and loading a superset is a unit function."""
    archive_path = superset_fifty_fifty.dump(path=tmp_path)
    superset_recovered = Superset.from_path(archive_path)
    assert superset_fifty_fifty == superset_recovered


def test_superset_dump_creates_non_empty_file(
    tmp_path: Path, superset_fifty_fifty: Superset
) -> None:
    """Dumping a superset creates a non-empty file."""
    archive_path = superset_fifty_fifty.dump(path=tmp_path)
    assert archive_path.is_file()
    assert archive_path.stat().st_size > 0


def test_superset_dump_archive_extension(
    tmp_path: Path, superset_fifty_fifty: Superset
) -> None:
    """Validate the archive extension of a dumped superset."""
    archive_path = superset_fifty_fifty.dump(path=tmp_path)
    assert archive_path.as_posix().endswith(".splits.pgdata")


def test_superset_dump_creates_valid_archive(
    tmp_path: Path, superset_fifty_fifty: Superset
) -> None:
    """Dumping a superset creates a valid archive."""
    archive_path = superset_fifty_fifty.dump(path=tmp_path)
    with ZipFile(archive_path, "r") as zip:
        assert zip.testzip() is None  # No corrupt files
