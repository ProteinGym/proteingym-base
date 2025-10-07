from pathlib import Path
from zipfile import ZipFile

import pytest

from proteingym.base.dataset import Dataset, DatasetSlice
from proteingym.base.superset import Superset


def test_superset_iterate_over_empty(empty_dataset: Dataset) -> None:
    """Test that iterating over an empty superset does not yield any elements."""
    superset = Superset(dataset=empty_dataset, slices=[])
    for _ in superset:
        raise AssertionError("Should not iterate over empty superset")


ALL_DATASET_NAMES = [
    "empty_dataset",
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
    slc = DatasetSlice(assays=[slice(None)] * len(dataset.assays))
    superset = Superset(dataset=dataset, slices=[slc])
    assert list(superset) == [dataset]


def test_superset_iterate_over_dataset_cut_in_half(dataset_with_assay: Dataset) -> None:
    """Iterating over a superset which cuts the dataset in half yields two datasets."""
    slc1 = DatasetSlice(assays=[[True, False]])
    slc2 = DatasetSlice(assays=[[False, True]])
    superset = Superset(dataset=dataset_with_assay, slices=[slc1, slc2])

    datasets = list(superset)
    assert len(datasets) == 2
    assert datasets[0] != datasets[1]
    assert datasets[0].assays[0].records[0] == ("SEQ1", 1.0)
    assert datasets[1].assays[0].records[0] == ("SEQ2", 2.0)


def test_superset_dump_from_path_is_unit_function(
    tmp_path: Path, empty_dataset: Dataset
) -> None:
    """Dumping and loading a superset is a unit function."""
    superset = Superset(dataset=empty_dataset, slices=[])

    archive_path = superset.dump(path=tmp_path)
    superset_recovered = Superset.from_path(archive_path)

    assert superset == superset_recovered


def test_superset_dump_creates_non_empty_file(
    tmp_path: Path, empty_dataset: Dataset
) -> None:
    """Dumping a superset creates a non-empty file."""
    superset = Superset(dataset=empty_dataset, slices=[])

    archive_path = superset.dump(path=tmp_path)

    assert archive_path.is_file()
    assert archive_path.stat().st_size > 0


def test_superset_dump_creates_valid_archive(
    tmp_path: Path, empty_dataset: Dataset
) -> None:
    """Dumping a superset creates a valid archive."""
    superset = Superset(dataset=empty_dataset, slices=[])

    archive_path = superset.dump(path=tmp_path)

    with ZipFile(archive_path, "r") as zip:
        assert zip.testzip() is None  # No corrupt files
