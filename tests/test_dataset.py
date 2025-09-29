from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile
import pytest
from typer.testing import CliRunner
from proteingym.base.__main__ import app
import json


from Bio.Align import MultipleSeqAlignment
from Bio.PDB.Structure import Structure as BioStructure
from Bio.Seq import Seq

from proteingym.base.assay import Assay
from proteingym.base.dataset import Dataset
from proteingym.base.msa import MSA
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType
from proteingym.base.structure import Structure


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


def test_serialize_sequences() -> None:
    """Test the serialize_sequences field_serializer."""
    sequence1 = Sequence(
        name="seq1",
        value=Seq("ATCG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
        description="Test sequence 1",
    )
    sequence2 = Sequence(
        name="seq2",
        value=Seq("MKLL"),
        type=SequenceType.ENGINEERED_SEQUENCE,
        alphabet=SequenceAlphabet.AA,
        description=None,
    )

    dataset = Dataset(name="test", sequences=[sequence1, sequence2])

    serialized = dataset.serialize_sequences([sequence1, sequence2])

    expected = [
        {
            "name": "seq1",
            "type": "wild_type",
            "alphabet": "DNA",
            "description": "Test sequence 1",
        },
        {
            "name": "seq2",
            "type": "engineered_sequence",
            "alphabet": "AA",
            "description": None,
        },
    ]

    assert serialized == expected


def test_serialize_assays() -> None:
    """Test the serialize_assays field_serializer."""
    assay1 = Assay(
        name="assay1",
        records=[],
        sequence_alphabet="AA",
        variables={"temp": 25, "pH": 7.4},
        description="Test assay 1",
        sequence_feature_name="sequence",
        target_feature_name="activity",
    )
    assay2 = Assay(
        name="assay2",
        records=[],
        sequence_alphabet="DNA",
        variables={},
        description=None,
        sequence_feature_name="seq",
        target_feature_name="target",
    )

    dataset = Dataset(name="test", assays=[assay1, assay2])

    serialized = dataset.serialize_assays([assay1, assay2])

    expected = [
        {
            "name": "assay1",
            "sequence_alphabet": "AA",
            "variables": {"temp": 25, "pH": 7.4},
            "description": "Test assay 1",
            "sequence_feature_name": "sequence",
            "target_feature_name": "activity",
        },
        {
            "name": "assay2",
            "sequence_alphabet": "DNA",
            "variables": {},
            "description": None,
            "sequence_feature_name": "seq",
            "target_feature_name": "target",
        },
    ]

    assert serialized == expected


def test_serialize_structures() -> None:
    """Test the serialize_structures field_serializer."""
    mock_bio_structure1 = Mock(spec=BioStructure)
    mock_bio_structure2 = Mock(spec=BioStructure)

    structure1 = Structure(
        name="struct1",
        value=mock_bio_structure1,
        description="Test structure 1",
        metadata={"resolution": "2.1", "method": "X-ray"},
    )
    structure2 = Structure(
        name="struct2", value=mock_bio_structure2, description=None, metadata={}
    )

    dataset = Dataset(name="test", structures=[structure1, structure2])

    serialized = dataset.serialize_structures([structure1, structure2])

    expected = [
        {
            "name": "struct1",
            "description": "Test structure 1",
            "metadata": {"resolution": "2.1", "method": "X-ray"},
        },
        {"name": "struct2", "description": None, "metadata": {}},
    ]

    assert serialized == expected


def test_serialize_msas() -> None:
    """Test the serialize_msas field_serializer."""
    mock_msa1 = Mock(spec=MultipleSeqAlignment)
    mock_msa2 = Mock(spec=MultipleSeqAlignment)

    msa1 = MSA(name="msa1", value=mock_msa1, description="Test MSA 1")
    msa2 = MSA(name="msa2", value=mock_msa2, description=None)

    dataset = Dataset(name="test", msas=[msa1, msa2])

    serialized = dataset.serialize_msas([msa1, msa2])

    expected = [
        {"name": "msa1", "description": "Test MSA 1"},
        {"name": "msa2", "description": None},
    ]

    assert serialized == expected

    
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
    assert "path" in dataset_data


def test_list_datasets_command_yaml_format(runner: CliRunner, dataset_file: Path) -> None:
    """Test the list-datasets CLI command with YAML format."""
    result = runner.invoke(app, ["list-datasets", str(dataset_file), "--format", "yaml"])

    assert result.exit_code == 0
    assert "name: test_dataset" in result.stdout


def test_list_datasets_directory_with_multiple_files(runner: CliRunner, tmp_path: Path) -> None:
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
    assert "Invalid value for 'PATH'" in result.stderr


def test_list_datasets_invalid_format(runner: CliRunner, dataset_file: Path) -> None:
    """Test list-datasets with invalid format option."""
    result = runner.invoke(app, ["list-datasets", str(dataset_file), "--format", "xml"])

    assert result.exit_code == 2
    assert "Invalid value for '--format'" in result.stderr