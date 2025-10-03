import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from typer.testing import CliRunner

from proteingym.base.__main__ import app
from proteingym.base.dataset import Dataset


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


@pytest.fixture
def runner() -> CliRunner:
    """Test runner for CLI commands."""
    return CliRunner()


@pytest.fixture
def dataset_file(tmp_path: Path) -> Path:
    """A (temporary) dataset file."""
    dataset = Dataset(name="test_dataset")
    dataset_path = dataset.dump(path=tmp_path)
    return dataset_path


def test_list_datasets_command(runner: CliRunner, dataset_file: Path) -> None:
    """Test the list-datasets CLI command."""
    result = runner.invoke(app, ["list-datasets", str(dataset_file)])

    assert result.exit_code == 0

    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 1

    dataset_data = output_data[0]
    assert dataset_data["name"] == "test_dataset"
    assert "input_filename" in dataset_data


def test_list_datasets_directory_with_multiple_files(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Test list-datasets with a directory containing multiple dataset files."""
    dataset1 = Dataset(name="dataset_one")
    dataset1.dump(path=tmp_path)

    dataset2 = Dataset(name="dataset_two")
    dataset2.dump(path=tmp_path)

    result = runner.invoke(app, ["list-datasets", str(tmp_path)])

    assert result.exit_code == 0
    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 2

    dataset_names = [dataset["name"] for dataset in output_data]
    assert "dataset_one" in dataset_names
    assert "dataset_two" in dataset_names


def test_list_datasets_directory_empty(runner: CliRunner, tmp_path: Path) -> None:
    """Test list-datasets with a directory containing no dataset files."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = runner.invoke(app, ["list-datasets", str(empty_dir)])

    assert result.exit_code == 0
    output_data = json.loads(result.stdout)
    assert isinstance(output_data, list)
    assert len(output_data) == 0


def test_list_datasets_nonexistent_path(runner: CliRunner, tmp_path: Path) -> None:
    """Test list-datasets with a non-existent path."""
    nonexistent_path = tmp_path / "does_not_exist"

    result = runner.invoke(app, ["list-datasets", str(nonexistent_path)])

    assert result.exit_code == 2


def test_list_datasets_invalid_format(runner: CliRunner, dataset_file: Path) -> None:
    """Test list-datasets with invalid format option."""
    result = runner.invoke(app, ["list-datasets", str(dataset_file), "--format", "xml"])

    assert result.exit_code == 2


def test_dataset_repr() -> None:
    """Test the string representation of the Dataset class."""
    dataset = Dataset(name="test dataset")
    repr_str = repr(dataset)
    assert "Dataset(\n\tname='test dataset'," in repr_str
    assert "\tdescription: None," in repr_str
    assert "contents:" in repr_str
    assert "assays: 0," in repr_str
    assert "sequences: 0," in repr_str
    assert "structures: 0," in repr_str
    assert "msas: 0," in repr_str
    assert "assay_variables: 0," in repr_str

    dataset = Dataset(name="short desc", description="Short description.")
    repr_str = repr(dataset)
    assert "\tdescription: Short description." in repr_str

    long_desc = "A" * 61 + "BCD"
    dataset = Dataset(name="long desc", description=long_desc)
    repr_str = repr(dataset)
    # Should be truncated to 60 chars + '...'
    assert f"\tdescription: {long_desc[:60]}..." in repr_str
