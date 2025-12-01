from pathlib import Path
from zipfile import ZipFile

import pytest

from proteingym.base.assay import AssaySlice
from proteingym.base.dataset import Dataset, DatasetSlice, Subsets


def test_subsets_iterate_over_empty(dataset_empty: Dataset) -> None:
    """Iterating over an empty collection of subsets does not yield any elements."""
    subsets = Subsets(dataset=dataset_empty, slices=[])
    for _ in subsets:
        raise AssertionError("Should not iterate over empty collection of subsets")


def test_subsets_iterate_over_strategies_raises_type_error(
    dataset_empty: Dataset,
) -> None:
    """Iterating over a dictionary of subsets should raise a TypeError."""
    subsets = Subsets(dataset=dataset_empty, slices={})
    with pytest.raises(
        TypeError, match="Cannot iterate over subsets when slices are not a list.*"
    ):
        list(subsets)


@pytest.mark.parametrize(
    "slices, length",
    [
        ([], 0),
        (
            [
                DatasetSlice(assays=[[True, False]]),
                DatasetSlice(assays=[[False, True]]),
            ],
            2,
        ),
    ],
)
def test_subsets_length(
    dataset_with_assay: Dataset, slices: list[DatasetSlice], length: int
) -> None:
    """Test subsets length equal to number of slices."""
    subsets = Subsets(dataset=dataset_with_assay, slices=slices)
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
    slc = DatasetSlice(
        assays=[AssaySlice(records=[True] * len(assay)) for assay in dataset.assays]
    )
    subsets = Subsets(dataset=dataset, slices=[slc])
    assert list(subsets) == [dataset]


@pytest.fixture
def subsets_fifty_fifty(dataset_with_assay: Dataset) -> Subsets:
    """Subsets that cut a dataset with two assay records in halfs."""
    slc1 = DatasetSlice(assays=[AssaySlice(records=[True, False])])
    slc2 = DatasetSlice(assays=[AssaySlice(records=[False, True])])
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
    with ZipFile(archive_path, "r") as zip_:
        assert zip_.testzip() is None  # No corrupt files


@pytest.fixture
def subsets_with_data_distribution_scenarios(dataset_with_assay: Dataset) -> Subsets:
    """Create a Subsets instance with skewed and balanced slices."""
    slices_skewed = [
        DatasetSlice(assays=[AssaySlice(records=[True, True])]),
        DatasetSlice(assays=[AssaySlice(records=[False, False])]),
    ]
    slices_balanced = [
        DatasetSlice(assays=[AssaySlice(records=[True, False])]),
        DatasetSlice(assays=[AssaySlice(records=[False, True])]),
    ]
    subsets = Subsets(
        dataset=dataset_with_assay,
        slices={"balanced": slices_balanced, "skewed": slices_skewed},
    )
    return subsets


def test_subsets_dump_from_path_is_unit_function_with_strategies(
    tmp_path: Path,
    subsets_with_data_distribution_scenarios: Subsets,
) -> None:
    """Dumping and loading subsets is a unit function."""
    archive_path = subsets_with_data_distribution_scenarios.dump(path=tmp_path)
    subsets_recovered = Subsets.from_path(archive_path)
    assert subsets_with_data_distribution_scenarios == subsets_recovered
    with ZipFile(archive_path, "r") as zip_:
        assert zip_.testzip() is None  # No corrupt files


def test_dataset_slice_with_columns_slices_assay_columns(
    dataset_with_assay: Dataset,
) -> None:
    """Slicing a dataset with columns should slice the assay columns."""
    expected_columns = ["DMS Score"]
    slc = DatasetSlice(assays=[AssaySlice(columns=["DMS Score"])])

    subset = dataset_with_assay[slc]

    assert all(assay.columns == expected_columns for assay in subset.assays)


def test_subsets_with_strategies_get_skewed(
    subsets_with_data_distribution_scenarios: Subsets,
) -> None:
    """The skewed subsets have different lengths."""
    subsets_skewed = subsets_with_data_distribution_scenarios["skewed"]
    left, right = tuple(subsets_skewed)
    assert len(left.to_df()) != len(right.to_df())


def test_subsets_with_strategies_get_balanced(
    subsets_with_data_distribution_scenarios: Subsets,
) -> None:
    """The balanced subsets have the same lengths."""
    subsets_balanced = subsets_with_data_distribution_scenarios["balanced"]
    left, right = tuple(subsets_balanced)
    assert len(left.to_df()) == len(right.to_df())


def test_subsets_update_contains_new_strategy(
    dataset_with_assay: Dataset,
    subsets_with_data_distribution_scenarios: Subsets,
) -> None:
    """Updating subsets with a new strategy works."""
    slices = [
        DatasetSlice(assays=[AssaySlice(records=[False, False])]),
        DatasetSlice(assays=[AssaySlice(records=[False, False])]),
    ]
    subsets = Subsets(dataset=dataset_with_assay, slices=slices)
    subsets_with_data_distribution_scenarios.update(no_data=subsets)
    assert "no_data" in subsets_with_data_distribution_scenarios.slices


def test_subsets_update_raises_type_error_when_slices_are_a_list(
    dataset_with_assay: Dataset,
) -> None:
    """Updating a list of slices should raise a TypeError."""
    slices = [
        DatasetSlice(assays=[AssaySlice(records=[False, False])]),
        DatasetSlice(assays=[AssaySlice(records=[False, False])]),
    ]
    subsets = Subsets(dataset=dataset_with_assay, slices=slices)
    match = "Cannot update subsets when slices are not a dictionary."
    with pytest.raises(TypeError, match=match):
        subsets.update(raises_type_error=subsets)


def test_subsets_update_raises_value_error_when_updating_with_different_dataset(
    dataset_empty: Dataset,
    dataset_with_assay: Dataset,
) -> None:
    """Subsets should refer to the same dataset when updating."""
    slices = [
        DatasetSlice(assays=[AssaySlice(records=[False, False])]),
        DatasetSlice(assays=[AssaySlice(records=[False, False])]),
    ]
    subsets = Subsets(dataset=dataset_with_assay, slices={"no_data": slices})
    match = "Cannot update subsets with different datasets.*"
    with pytest.raises(ValueError, match=match):
        subsets.update(raise_value_error=Subsets(dataset=dataset_empty, slices=slices))
