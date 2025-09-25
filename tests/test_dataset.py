from pathlib import Path
from zipfile import ZipFile

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


def test_dataset_repr() -> None:
    """Test the string representation of the Dataset class."""
    dataset = Dataset(name="test dataset")

    repr_str = repr(dataset)
    assert "Dataset(\n\tname='test dataset'," in repr_str
    assert "contents:" in repr_str
    assert "assays: 0," in repr_str
    assert "sequences: 0," in repr_str
    assert "structures: 0," in repr_str
    assert "msas: 0," in repr_str
    assert "assay_variables: 0," in repr_str
