import json
from pathlib import Path
from zipfile import ZipFile

import polars as pl
import pytest
from Bio.Seq import Seq
from biotite.structure import AtomArray
from typer.testing import CliRunner

from proteingym.base.__main__ import app
from proteingym.base.assay import SEQUENCE, AssaySlice, Field
from proteingym.base.dataset import (
    Dataset,
    DatasetSlice,
)
from proteingym.base.dataset import (
    dummy_dataset as _dummy_dataset,
)
from proteingym.base.msa import MSA, MsaProteinSequence
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType
from proteingym.base.structure import Structure


@pytest.fixture
def dummy_dataset():
    return _dummy_dataset()


def test_dataset_slice_from_dict() -> None:
    """Test that a dataset slice can be created from a JSON string."""
    expected = DatasetSlice(
        assays=[
            AssaySlice(records=[True, False, True]),
            AssaySlice(records=[False, True, False]),
        ],
        metadata={"fraction": 0.8},
    )
    contents = {
        "assays": [{"records": [True, False, True]}, {"records": [False, True, False]}],
        "metadata": {"fraction": 0.8},
    }
    slc = DatasetSlice.from_dict(contents)
    assert slc == expected


def test_dataset_slice_from_json_mask() -> None:
    """Test that a dataset slice can be created from a JSON string."""
    expected = DatasetSlice(
        assays=[
            AssaySlice(records=[True, False, True]),
            AssaySlice(records=[False, True, False]),
        ]
    )
    contents = (
        '{"assays": ['
        '{"records": [true, false, true]}, '
        '{"records": [false, true, false]}]}'
    )
    slc = DatasetSlice.from_json(contents)
    assert slc == expected


def test_dataset_slice_dumps_mask() -> None:
    """Test that a dataset slice with a boolean mask is correctly dumped to JSON."""
    contents = (
        '{"assays": ['
        '{"columns": null, "records": [true, false, true], "metadata": null}, '
        '{"columns": null, "records": [false, true, false], "metadata": null}], '
        '"metadata": null}'
    )
    slc = DatasetSlice(
        assays=[
            AssaySlice(records=[True, False, True]),
            AssaySlice(records=[False, True, False]),
        ]
    )
    assert slc.to_json() == contents


def test_dataset_getitem_with_none_assays(dummy_dataset) -> None:
    """Slice with no assays should return all assays"""
    slice_with_none_assays = DatasetSlice(assays=None)

    result = dummy_dataset[slice_with_none_assays]
    assert len(result.assays) == len(dummy_dataset.assays)


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


def test_list_datasets_json_serialization() -> None:
    sequence = Sequence(
        name="test",
        value=Seq("test"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )

    structure = Structure(
        name="test",
        value=AtomArray(10),
    )

    msa = MSA(name="test", value=list[MsaProteinSequence])

    dataset = Dataset(
        name="dataset", sequences=[sequence], structures=[structure], msas=[msa]
    )

    dataset_str = dataset.model_dump_json()
    dataset_obj = json.loads(dataset_str)

    assert isinstance(dataset_obj, dict)
    assert dataset_obj["sequences"][0]["value"] == "test"
    assert isinstance(dataset_obj["msas"][0]["value"], str)


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


def test_reference_sequence_present_in_dataset() -> None:
    seq = Sequence(
        name="ref_seq",
        value=Seq("TTTTTTT"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    dataset = Dataset(name="test", reference_sequence_name="ref_seq", sequences=[seq])
    assert dataset.reference_sequence == seq


def test_reference_sequence_not_present_errors() -> None:
    seq = Sequence(
        name="ref_seq",
        value=Seq("TTTTTTT"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    with pytest.raises(ValueError, match="not present among the dataset's sequences"):
        Dataset(name="test", reference_sequence_name="foo", sequences=[seq])


def test_predictions_delta_basic(dummy_dataset) -> None:
    """Test basic predictions_delta functionality."""
    from proteingym.base.assay import Assay

    predictions_df = pl.DataFrame(
        {"sequence": ["ACDEFG", "GFEDCA"], "numerical": [1.2, 2.3]}
    )

    delta = dummy_dataset.predictions_delta(predictions_df, target="numerical")

    seq1 = dummy_dataset.assays[0].records[0][0]
    seq2 = dummy_dataset.assays[0].records[2][0]

    expected_assay = Assay(
        name="assay1",
        records=[(seq1, 1.2), (seq1, 1.2), (seq2, 2.3), (seq2, 2.3)],
        fields=[
            Field(name=SEQUENCE, description=None),
            Field(name="numerical", description=None),
        ],
        variables={"var1": 2},
        non_targets=[],
    )

    expected_dataset = Dataset(
        name="dataset_with_single_assay_predictions",
        description=None,
        reference_sequence_name=None,
        assay_variables=[Field(name="var1", description=None)],
        assay_targets=[Field(name="numerical", description=None)],
        assays=[expected_assay],
        assays_raw=[],
        sequences=[],
        structures=[],
        msas=[],
        msa_weights=[],
        publication=None,
    )

    assert delta == expected_dataset


def test_predictions_delta_round_trip(dummy_dataset, tmp_path: Path) -> None:
    """Test that predictions_delta output can be dumped and reloaded."""
    predictions_df = pl.DataFrame(
        {"sequence": ["ACDEFG", "GFEDCA"], "numerical": [1.5, 2.5]}
    )

    delta = dummy_dataset.predictions_delta(predictions_df, target="numerical")

    path = delta.dump(path=tmp_path)
    reloaded = Dataset.from_path(path)

    # Check structure preserved after reload
    assert len(reloaded.assays) == len(delta.assays)
    assert reloaded.to_df(target_names="numerical").equals(
        delta.to_df(target_names="numerical")
    )


def test_predictions_delta_missing_predictions(dummy_dataset) -> None:
    """Test that records without predictions get null values."""
    # Only predict for one sequence
    predictions_df = pl.DataFrame({"sequence": ["ACDEFG"], "numerical": [1.2]})
    delta = dummy_dataset.predictions_delta(predictions_df, target="numerical")
    expected_df = pl.DataFrame(
        {"sequence": ["ACDEFG"], "var1": [2], "numerical": [1.2]}
    )
    result_df = delta.to_df(target_names="numerical")
    assert result_df.equals(expected_df)


def test_predictions_delta_invalid_target_raises(dummy_dataset) -> None:
    """Test that invalid target name raises ValueError."""
    predictions_df = pl.DataFrame({"sequence": ["ACDEFG"], "numerical": [1.2]})

    with pytest.raises(ValueError, match="not a valid assay target"):
        dummy_dataset.predictions_delta(predictions_df, target="invalid_target")


def test_predictions_delta_missing_sequence_column_raises(
    dummy_dataset,
) -> None:
    """Test that missing sequence column raises ValueError."""
    predictions_df = pl.DataFrame({"numerical": [1.2]})

    with pytest.raises(ValueError, match="must have a 'sequence' column"):
        dummy_dataset.predictions_delta(predictions_df, target="numerical")


def test_predictions_delta_missing_target_column_raises(dummy_dataset) -> None:
    """Test that missing target column raises ValueError."""
    predictions_df = pl.DataFrame({"sequence": ["ACDEFG"]})

    with pytest.raises(ValueError, match="must have a 'numerical' column"):
        dummy_dataset.predictions_delta(predictions_df, target="numerical")


def test_predictions_delta_preserves_sequence_objects(dummy_dataset) -> None:
    """Test that Sequence objects are preserved from the original dataset."""
    predictions_df = pl.DataFrame(
        {"sequence": ["ACDEFG", "GFEDCA"], "numerical": [1.2, 2.3]}
    )
    delta = dummy_dataset.predictions_delta(predictions_df, target="numerical")
    original_seq = dummy_dataset.assays[0].records[0][0]
    delta_seq = delta.assays[0].records[0][0]
    assert delta_seq == original_seq


def test_predictions_delta_raises_on_unused(dummy_dataset) -> None:
    """Test that a warning is issued when many predictions don't match."""
    # Create predictions with extra sequences
    predictions_df = pl.DataFrame(
        {
            "sequence": ["ACDEFG", "GFEDCA"] + [f"SEQ{i}" for i in range(20)],
            "numerical": [1.2, 2.3] + [float(i) for i in range(20)],
        }
    )

    with pytest.raises(ValueError, match="don't match any sequence"):
        _ = dummy_dataset.predictions_delta(
            predictions_df, target="numerical", allow_extra_predictions=False
        )


def test_predictions_delta_no_target_records_when_target_not_in_assay(
    datasets_with_different_targets_across_assays,
) -> None:
    """Test that assays without the target only store sequence records."""
    predictions_df = pl.DataFrame(
        {"sequence": ["ACDEFG", "GFEDCA"], "target_A": [1.5, 2.5]}
    )
    delta = datasets_with_different_targets_across_assays.predictions_delta(
        predictions_df, target="target_A"
    )
    # Check assay structure
    assert len(delta.assays) == 2

    # Check assay 1 has predictions
    seq1 = datasets_with_different_targets_across_assays.assays[0].records[0][0]
    seq2 = datasets_with_different_targets_across_assays.assays[0].records[1][0]
    expected_records_assay1 = [(seq1, 1.5), (seq2, 2.5)]
    assert delta.assays[0].records == expected_records_assay1

    # Check assay 1 fields
    expected_fields_assay1 = [
        Field(name=SEQUENCE, description=None),
        Field(name="target_A", description=None),
    ]
    assert delta.assays[0].fields == expected_fields_assay1

    # Check assay 2 only has sequence field (no target since target_A not in assay 2)
    expected_fields_assay2 = [Field(name=SEQUENCE, description=None)]
    assert delta.assays[1].fields == expected_fields_assay2
