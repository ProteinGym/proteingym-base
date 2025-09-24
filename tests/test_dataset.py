from pathlib import Path
from zipfile import ZipFile

from pg2_dataset.assay import Assay, AssayCondition
from pg2_dataset.dataset import Dataset


def test_dataset_dump_extension(tmp_path: Path) -> None:
    """The dataset dump should create a .pgdata file.

    Docs:
        ../docs/decisions/0003-dataset-archive.md
    """
    dataset = Dataset(name="test")

    path = dataset.dump(path=tmp_path)

    assert path.suffix == ".pgdata", f"Expected .pgdata file: {path.suffix}"
    assert path.as_posix().endswith(".pgdata"), f"Expected .pgdata file: {path}"


def test_dataset_dump_test_zip_minimal(tmp_path: Path) -> None:
    """Test the zip file created by the Dataset dump.

    Docs:
        https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.testzip
    """
    dataset = Dataset(name="test")

    path = dataset.dump(path=tmp_path)

    assert not ZipFile(path).testzip(), "Dataset dump contains a bad file."


def test_dataset_dump_creates_one_file(tmp_path: Path) -> None:
    """The dataset dump should create a single file."""
    dataset = Dataset(name="test")

    path = dataset.dump(path=tmp_path)

    paths = list(tmp_path.iterdir())
    assert [path] == paths, f"Expected one file in the directory, but found: {paths}"


def test_dataset_from_path_simple(tmp_path: Path) -> None:
    """Create a dataset from a path to a zip file."""
    dataset_path = Dataset(name="test").dump(path=tmp_path)

    dataset = Dataset.from_path(dataset_path)

    assert dataset.name == "test", "Dataset name does not match the expected name."


def test_dataset_filter_empty_query() -> None:
    """Test filter with empty query string returns True."""
    dataset = Dataset(name="test_dataset")
    assert dataset.filter("") is True


def test_dataset_filter_simple_field() -> None:
    """Test filter with simple field - exists and matches vs doesn't exist."""
    dataset = Dataset(name="NEIME_2019")
    assert dataset.filter("name=NEIME_2019") is True
    assert dataset.filter("name=OTHER") is False
    assert dataset.filter("nonexistent=value") is False


def test_dataset_filter_nested_field_list() -> None:
    """Test filter with nested field in list - all values exist vs partial match."""
    conditions = [
        AssayCondition(name="PH", unit="pH", value=7.0),
        AssayCondition(name="T", unit="C", value=25.0),
    ]
    dataset = Dataset(name="test", assay_conditions=conditions)
    assert dataset.filter("assay_conditions.name=PH,T") is True
    assert dataset.filter("assay_conditions.name=PH,MISSING") is False
    assert dataset.filter("nonexistent.name=value") is False


def test_dataset_filter_multiple_conditions() -> None:
    """Test filter with multiple conditions using AND logic."""
    conditions = [AssayCondition(name="PH", unit="pH", value=7.0)]
    dataset = Dataset(name="NEIME_2019", assay_conditions=conditions)
    assert dataset.filter("name=NEIME_2019&assay_conditions.name=PH") is True
    assert dataset.filter("name=NEIME_2019&assay_conditions.name=MISSING") is False


def test_dataset_filter_three_level_nesting() -> None:
    """Test filter with 3-level nesting like 'assays.conditions.T'."""
    # Create a dataset with 3-level nested structure matching TOML format
    assay = Assay(
        name="assay",
        records=[],
        sequence_alphabet="AA",
        conditions={"T": 37, "PH": 7},
    )
    dataset = Dataset(name="test", assays=[assay])

    assert dataset.filter("assays.conditions.T=37") is True
    assert dataset.filter("assays.conditions.PH=7") is True
    assert dataset.filter("assays.conditions.T=25") is False
    assert dataset.filter("assays.conditions.nonexistent=value") is False


def test_dataset_filter_deeper_nesting() -> None:
    """Test filter with deeper nesting (> 3 levels) returns False."""
    dataset = Dataset(name="test")
    assert dataset.filter("level1.level2.level3.level4=value") is False
