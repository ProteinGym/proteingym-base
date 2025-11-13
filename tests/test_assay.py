from pathlib import Path
from zipfile import ZipFile

import polars as pl
import polars.testing
import pytest
from pydantic import ValidationError
from semver import Version

from proteingym.base import Dataset
from proteingym.base.assay import (
    Assay,
    AssayFormat,
    AssayManifestSection,
    AssayMeasurement,
    AssayStatistic,
    AssayTarget,
    AssayVariable,
)
from proteingym.base.dataset import DatasetArchiveLayout
from proteingym.base.manifest import Manifest
from proteingym.base.sequence import Sequence, SequenceAlphabet


@pytest.fixture
def assay_file(tmp_path: Path) -> Path:
    """Fixture to create a temporary assay file."""
    path = tmp_path / "assay.csv"
    path.write_text(
        """
sequence,target,target2
F1I,1.59,0.5
F1L,0.6,0.4""".lstrip()
    )
    return path


@pytest.fixture
def assay_measurement_file(tmp_path: Path) -> Path:
    """Fixture to create a temporary assay measurement file."""
    path = tmp_path / "measurements.csv"
    path.write_text(
        """
sequence,measurement1,measurement2
F1I,0.1,0.2
F1L,0.3,0.4""".lstrip()
    )
    return path


def test_assay_variable_minimal() -> None:
    """Test creating a minimal AssayVariable."""
    # This should not raise an error
    try:
        variable = AssayVariable(name="test")
    except ValidationError as e:
        raise AssertionError("Test failed") from e
    else:
        assert variable.name == "test"


def test_assay_target_minimal() -> None:
    """Test creating a minimal AssayTarget."""
    # This should not raise an error
    try:
        target = AssayTarget(name="DMS Score")
    except ValidationError as e:
        raise AssertionError(f"AssayTarget raised ValidationError: {e}") from e
    else:
        assert target.name == "DMS Score"


def test_assay_measurement_minimal() -> None:
    """Test creating a minimal AssayMeasurement."""
    try:
        statistic = AssayMeasurement(name="measurement1")
    except ValidationError as e:
        raise AssertionError(f"AssayMeasurement raised ValidationError: {e}") from e
    else:
        assert statistic.name == "measurement1"


def test_assay_statistic_minimal() -> None:
    """Test creating a minimal AssayStatistic."""
    try:
        statistic = AssayStatistic(name="statistic1")
    except ValidationError as e:
        raise AssertionError(f"AssayStatistic raised ValidationError: {e}") from e
    else:
        assert statistic.name == "statistic1"


def test_assay_manifest_section_with_relative_path(tmp_path: Path) -> None:
    """Test AssayManifestSection with a relative path."""
    path = tmp_path / "assay.csv"
    path.write_text("sequence,target\nF1I,1.59\nF1L,0.6")
    context = {"relative_to_path": tmp_path}

    section = AssayManifestSection.model_validate(
        {"path": "assay.csv"}, context=context
    )

    assert section.path == path


def test_assay_manifest_section_with_relative_measurements_path(
    tmp_path: Path, assay_file: Path
) -> None:
    """Test AssayManifestSection with a relative measurements path."""
    measurement_path = tmp_path / "measurements.csv"
    measurement_path.write_text("sequence,measurement1\nF1I,0.1\nF1L,0.3")
    context = {"relative_to_path": tmp_path}

    section = AssayManifestSection.model_validate(
        {
            "path": assay_file.as_posix(),
            "measurements_path": "measurements.csv",
        },
        context=context,
    )

    assert section.measurements_path == measurement_path


def test_assay_manifest_section_validate_feature_names(assay_file: Path) -> None:
    """Test that AssayManifestSection raises error for invalid feature names."""
    with pytest.raises(
        ValueError,
        match=r"Feature 'invalid_feature' not found in the file: .*assay.csv",
    ):
        AssayManifestSection(
            name="test_assay",
            description="Test assay",
            sequence="invalid_feature",
            sequence_alphabet="AA",
            targets={"DMS Score": "invalid_feature"},
            variables={"test_cond1": "true", "test_cond2": 42},
            path=assay_file,
        )


def test_assay_manifest_section_both_measurement_data_and_path_provided(
    assay_file: Path, assay_measurement_file: Path
) -> None:
    """Measurements path or data should be provided, not both."""

    with pytest.raises(
        ValueError,
        match=r"Only one of measurements_data or measurements_path should be provided.",
    ):
        AssayManifestSection(
            path=assay_file,
            measurements_path=assay_measurement_file,
            measurements_data=[
                [1, 2],
                [3, 4],
            ],
        )


def test_assay_manifest_section_measurements_path_missing_sequence_column(
    assay_file: Path,
) -> None:
    """The measurement data file should contain a sequence column."""
    measurement_path = assay_file.parent / "measurements.csv"
    measurement_path.write_text("""bad_name,measurement1,measurement2""")
    with pytest.raises(
        ValueError, match="sequence column not found in measurements file."
    ):
        AssayManifestSection(path=assay_file, measurements_path=measurement_path)


def test_assay_from_manifest_section(assay_file: Path) -> None:
    """Test creating an Assay from a manifest section."""
    try:
        assay = Assay.from_manifest_section(
            AssayManifestSection(
                name="assay",
                sequence="sequence",
                sequence_alphabet=SequenceAlphabet.DNA,
                targets={"DMS Score": "target", "DMS Score2": "target2"},
                path=assay_file,
                variables={"test_cond1": "true", "test_cond2": 42},
            ),
        )
    except ValidationError as e:
        raise AssertionError("Failed test assay from manifest section") from e
    else:
        assert assay.name == "assay"
        assert len(assay.records) == 2
        for rec in assay.records:
            assert isinstance(rec[0], Sequence)
            assert all(
                t in ["DMS Score", "DMS Score2"] for t in assay.target_feature_names
            )
        assert assay.sequence_feature_name == "sequence"


def test_from_manifest_section_measurement_file_with_missing_measurement(
    assay_file: Path,
) -> None:
    """Test raises error if the measurement data have missing measurement names."""
    assay_measurement_file = assay_file.parent / "measurements.csv"
    assay_measurement_file.write_text(
        """sequence,measurement1
        F1I,0.1
        F1L,0.2
        """
    )

    with pytest.raises(
        ValueError,
        match="Measurements {'measurement2'} not found in measurements.",
    ):
        Assay.from_manifest_section(
            AssayManifestSection(
                name="assay",
                sequence="sequence",
                sequence_alphabet=SequenceAlphabet.DNA,
                targets={"DMS Score": "target", "DMS Score2": "target2"},
                path=assay_file,
                measurements=[
                    AssayMeasurement(name="measurement1"),
                    AssayMeasurement(name="measurement2"),
                ],
                variables={"test_cond1": "true", "test_cond2": 42},
                measurements_path=assay_measurement_file,
            )
        )


def test_from_manifest_section_measurement_missing_sequences(assay_file: Path) -> None:
    """Test raises error if measurement data have sequences not in assay records."""
    assay_measurement_file = assay_file.parent / "measurements.csv"
    assay_measurement_file.write_text(
        """sequence,measurement1,measurement2
BAD_SEQ,0.1,0.2"""
    )

    with pytest.raises(
        ValueError,
        match="Sequences {'BAD_SEQ'} found in measurements data file but not in assay \
records.",
    ):
        Assay.from_manifest_section(
            AssayManifestSection(
                name="assay",
                sequence="sequence",
                sequence_alphabet=SequenceAlphabet.DNA,
                targets={"DMS Score": "target", "DMS Score2": "target2"},
                path=assay_file,
                measurements=[
                    AssayMeasurement(name="measurement1"),
                    AssayMeasurement(name="measurement2"),
                ],
                variables={"test_cond1": "true", "test_cond2": 42},
                measurements_path=assay_measurement_file,
            )
        )


def test_as_manifest_section(tmp_path: Path) -> None:
    """Test converting an Assay to a manifest section."""
    assay = Assay(
        name="assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                1.56,
            ),
            (
                Sequence(
                    name="seq2",
                    value="DEF",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
    )
    path = assay.dump(path=tmp_path, format=AssayFormat.CSV)
    manifest = assay.as_manifest_section(path=path)
    assert "DMS Score" in manifest.path.read_text()
    assert "sequence" in manifest.path.read_text()
    assert "1.56" in manifest.path.read_text()
    assert "2.0" in manifest.path.read_text()


def test_assay_to_df() -> None:
    """Test converting an Assay to a Polars DataFrame."""
    seq1 = Sequence(name="seq1", value="APC", type="standard_sequence", alphabet="DNA")
    seq2 = Sequence(name="seq2", value="DEF", type="standard_sequence", alphabet="DNA")
    assay = Assay(
        name="assay",
        records=[
            (seq1, 1.56, 0.5),
            (seq2, 2.0, 0.6),
        ],
        variables={"test_cond1": "true", "test_cond2": 42},
        columns=["sequence", "DMS Score", "DMS Score2"],
    )
    try:
        df = assay.to_df()
    except ValidationError as e:
        raise AssertionError(f"Assay raised ValidationError: {e}") from e
    else:
        assert "sequence" in df.columns
        assert "DMS Score" in df.columns
        assert all(
            assay_var in df.columns for assay_var in ["test_cond1", "test_cond2"]
        )
        assert df.shape == (2, 5)
        assert df["sequence"].to_list() == ["APC", "DEF"]
        assert df["DMS Score"].to_list() == [1.56, 2.0]
        assert df["DMS Score2"].to_list() == [0.5, 0.6]


def test_assay_to_df_single_string_target():
    """Test Assay.to_df with target_names as a single string."""
    seq1 = Sequence(name="seq1", value="APC", type="standard_sequence", alphabet="DNA")
    seq2 = Sequence(name="seq2", value="DEF", type="standard_sequence", alphabet="DNA")
    assay = Assay(
        name="assay",
        records=[
            (seq1, 1.56),
            (seq2, 2.0),
        ],
        columns=["sequence", "DMS Score"],
    )
    df = assay.to_df(target_names="DMS Score")
    assert "DMS Score" in df.columns
    assert df.shape == (2, 2)
    assert df["DMS Score"].to_list() == [1.56, 2.0]


def test_assay_to_df_invalid_target_name_returns_empty_df() -> None:
    """Test that Assay.to_df raises error for invalid target names."""
    assay = Assay(
        name="assay",
        records=[
            (
                Sequence(
                    name="seq1", value="APC", type="standard_sequence", alphabet="AA"
                ),
                1.56,
            ),
            (
                Sequence(
                    name="seq2", value="DEF", type="standard_sequence", alphabet="AA"
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
    )
    try:
        df = assay.to_df(target_names=["Invalid Target"])
    except ValueError as e:
        raise ValueError(f"Failed to convert assay to DataFrame: {e}") from e
    else:
        assert df.shape == (0, 1), "DataFrame should be empty for invalid target names"


def test_assay_to_df_no_records_returns_empty_df() -> None:
    """Test that Assay.to_df returns empty DataFrame for assay with no records."""
    assay = Assay(
        name="empty_assay",
        records=[],
    )
    try:
        df = assay.to_df()
    except ValueError as e:
        raise ValueError(f"Failed to convert assay to DataFrame: {e}") from e
    else:
        assert df.shape == (0, 1), "DataFrame should be empty for assay with no records"


def test_as_manifest_section_with_no_records(tmp_path: Path) -> None:
    """Test converting an Assay with no records to a manifest section."""
    assay = Assay(
        name="assay",
        records=[],
    )
    path = assay.dump(path=tmp_path, format=AssayFormat.CSV)
    manifest = assay.as_manifest_section(path=path)
    assert manifest.name == "assay"
    assert manifest.sequence_alphabet is None


def test_assay_dump(tmp_path: Path) -> None:
    """Test dumping an Assay to a file."""
    assay = Assay(
        name="assay",
        records=[
            (
                Sequence(
                    name="seq1", value="APC", type="standard_sequence", alphabet="AA"
                ),
                1.56,
            ),
            (
                Sequence(
                    name="seq2", value="DEF", type="standard_sequence", alphabet="AA"
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
    )
    dumped_path = assay.dump(path=tmp_path, format=AssayFormat.CSV)
    assert dumped_path == tmp_path / "assay.csv"
    assert (tmp_path / "assay.csv").exists()
    content = dumped_path.read_text()
    assert "APC,1.56" in content
    assert "DEF,2.0" in content


def test_manifest_with_valid_assay_variables(assay_file: Path) -> None:
    """Test creating a Manifest with valid assay variables."""
    try:
        manifest = Manifest(
            version=Version(1, 0),
            name="test_manifest",
            assay_variables=[{"name": "pH"}, {"name": "temperature"}],
            assays=[
                {
                    "path": assay_file,
                    "sequence_alphabet": "DNA",
                    "variables": {"pH": 7.0, "temperature": 37.0},
                }
            ],
        )
    except AssertionError as e:
        raise AssertionError(f"Manifest raised ValidationError: {e}") from e
    else:
        assert manifest.assay_variables, "Valid assay variables should be present"


def test_manifest_with_undefined_assay_variable(assay_file: Path) -> None:
    """Test creating a Manifest with undefined assay variables."""
    with pytest.raises(
        ValidationError,
        match=r"validation error for Manifest\n"
        r".*Value error, Assay .* contains undefined variables",
    ):
        Manifest(
            version=Version(1, 0),
            name="test_manifest",
            assay_variables=[{"name": "pH"}],
            assays=[
                {
                    "path": assay_file,
                    "sequence_alphabet": SequenceAlphabet.DNA,
                    "variables": {"temperature": 37.0},
                }
            ],
        )


def test_manifest_with_valid_assay_targets(assay_file: Path) -> None:
    """Test creating a Manifest with valid assay targets."""
    try:
        manifest = Manifest(
            version=Version(1, 0),
            name="test_manifest",
            assay_targets=[
                AssayTarget(name="DMS Score"),
                AssayTarget(name="DMS Score2"),
            ],
            assays=[
                {
                    "path": assay_file,
                    "sequence_alphabet": SequenceAlphabet.DNA,
                    "targets": {"DMS Score": "target", "DMS Score2": "target2"},
                }
            ],
        )
    except AssertionError as e:
        raise AssertionError(f"Manifest raised ValidationError: {e}") from e
    else:
        assert manifest.assay_targets, "Valid assay targets should be present"


def test_manifest_with_undefined_assay_target(assay_file: Path) -> None:
    """Test creating a Manifest with undefined assay targets."""
    with pytest.raises(
        ValidationError,
        match=r"validation error for Manifest\n"
        r".*Value error, Assay .* contains undefined targets",
    ):
        Manifest(
            version=Version(1, 0),
            name="test_manifest",
            assay_targets=[
                AssayTarget(name="DMS Bin"),
            ],
            assays=[
                {
                    "path": assay_file,
                    "sequence_alphabet": SequenceAlphabet.DNA,
                    "targets": {"DMS Score": "target", "DMS Score2": "target2"},
                }
            ],
        )


def test_dataset_to_df_no_assays() -> None:
    """Test converting a dataset with no assays to a DataFrame."""
    dataset = Dataset(name="test")
    try:
        df = dataset.to_df()
    except AssertionError as e:
        raise AssertionError(f"Should return empty DataFrame: {e}") from e
    else:
        assert df.is_empty()


@pytest.fixture
def seq1() -> Sequence:
    return Sequence(name="seq1", value="APC", type="standard_sequence", alphabet="DNA")


@pytest.fixture
def seq2() -> Sequence:
    return Sequence(name="seq2", value="DEF", type="standard_sequence", alphabet="DNA")


@pytest.fixture
def seq3() -> Sequence:
    return Sequence(name="seq3", value="GHI", type="standard_sequence", alphabet="DNA")


@pytest.fixture
def assay1(seq1: Sequence, seq2: Sequence) -> Assay:
    return Assay(
        name="assay1",
        records=[
            (seq1, 1.0, 0.5),
            (seq2, 2.0, 0.6),
        ],
        columns=["sequence", "DMS Score", "DMS Score2"],
    )


@pytest.fixture
def assay2(seq1: Sequence, seq3: Sequence) -> Assay:
    return Assay(
        name="assay2",
        records=[
            (seq1, 1.0, 0.7),
            (seq3, 3.0, 0.8),
        ],
        columns=["sequence", "DMS Score", "DMS Score3"],
    )


def test_dataset_to_df_single_target(assay1: Assay, assay2: Assay) -> None:
    """Test converting a dataset with assays to a DataFrame."""
    dataset = Dataset(
        name="test_dataset",
        assay_targets=[
            AssayTarget(name="DMS Score"),
            AssayTarget(name="DMS Score2"),
            AssayTarget(name="DMS Score3"),
        ],
        assays=[assay1, assay2],
    )

    try:
        df = dataset.to_df(target_names=["DMS Score"])
    except ValueError as e:
        raise ValueError(f"Failed to convert dataset to DataFrame: {e}") from e
    else:
        expected_df = pl.DataFrame(
            {
                "sequence": ["APC", "DEF", "GHI"],
                "DMS Score": [1.0, 2.0, 3.0],
            }
        )
        pl.testing.assert_frame_equal(
            df, expected_df, check_dtypes=False, check_column_order=False
        )


def test_dataset_to_df_no_target(assay1: Assay, assay2: Assay) -> None:
    dataset = Dataset(
        name="test_dataset",
        assay_targets=[
            AssayTarget(name="DMS Score"),
            AssayTarget(name="DMS Score2"),
            AssayTarget(name="DMS Score3"),
        ],
        assays=[assay1, assay2],
    )
    try:
        df = dataset.to_df()
    except ValueError as e:
        raise ValueError(f"Failed to convert dataset to DataFrame: {e}") from e
    else:
        expected_df = pl.DataFrame(
            {
                "sequence": ["APC", "DEF", "GHI"],
                "DMS Score": [1.0, 2.0, 3.0],
                "DMS Score2": [0.5, 0.6, None],
                "DMS Score3": [0.7, None, 0.8],
            }
        )
        pl.testing.assert_frame_equal(
            df, expected_df, check_dtypes=False, check_column_order=False
        )


def test_dataset_to_df_invalid_target(assay1: Assay, assay2: Assay) -> None:
    dataset = Dataset(
        name="test_dataset",
        assay_targets=[
            AssayTarget(name="DMS Score"),
            AssayTarget(name="DMS Score2"),
            AssayTarget(name="DMS Score3"),
        ],
        assays=[assay1, assay2],
    )
    with pytest.raises(
        ValueError,
        match=r"Target names must be valid assay target names.",
    ):
        dataset.to_df(target_names=["Invalid Target"])


def test_dataset_to_df_string_target(assay1: Assay, assay2: Assay) -> None:
    dataset = Dataset(
        name="test_dataset",
        assay_targets=[
            AssayTarget(name="DMS Score"),
            AssayTarget(name="DMS Score2"),
            AssayTarget(name="DMS Score3"),
        ],
        assays=[assay1, assay2],
    )
    try:
        df = dataset.to_df(target_names="DMS Score")
    except ValueError as e:
        raise ValueError(f"Failed to convert dataset to DataFrame: {e}") from e
    else:
        expected_df = pl.DataFrame(
            {"sequence": ["APC", "DEF", "GHI"], "DMS Score": [1.0, 2.0, 3.0]}
        )
        pl.testing.assert_frame_equal(
            df, expected_df, check_dtypes=False, check_column_order=False
        )


def test_dataset_to_df_assay_with_different_targets(
    seq1: Sequence, seq2: Sequence, seq3: Sequence
) -> None:
    """Test converting a dataset with assays having different targets to a DataFrame."""

    assay1 = Assay(
        name="assay1",
        records=[
            (seq1, 1.0),
            (seq2, 2.0),
        ],
        variables={"pH": 7.0, "T": 30},
        columns=["sequence", "DMS Score"],
    )
    assay2 = Assay(
        name="assay2",
        records=[
            (seq1, 3.0),
        ],
        variables={"pH": 7.0, "T": 30},
        columns=["sequence", "DMS Score"],
    )
    assay3 = Assay(
        name="assay3",
        records=[
            (seq1, 0.8, 5.0),
            (seq3, 0.9, 2.0),
        ],
        variables={"pH": 7.0},
        columns=["sequence2", "Binding Affinity", "Other Target"],
    )
    assay4 = Assay(
        name="assay4",
        records=[],
        columns=["sequence", "DMS Score"],
    )

    dataset = Dataset(
        name="test_dataset",
        assay_targets=[
            AssayTarget(name="DMS Score"),
            AssayTarget(name="Binding Affinity"),
        ],
        assay_variables=[AssayVariable(name="pH"), AssayVariable(name="T")],
        assays=[assay1, assay2, assay3, assay4],
    )

    try:
        df = dataset.to_df(target_names=["DMS Score", "Binding Affinity"])
    except ValueError as e:
        raise ValueError(f"Failed to convert dataset to DataFrame: {e}") from e
    else:
        expected_df = pl.DataFrame(
            {
                "sequence": ["APC", "APC", "DEF", "GHI"],
                "pH": [7.0, 7.0, 7.0, 7.0],
                "T": [None, 30, 30, None],
                "DMS Score": [None, 2.0, 2.0, None],
                "Binding Affinity": [0.8, None, None, 0.9],
            }
        )
        pl.testing.assert_frame_equal(
            df, expected_df, check_dtypes=False, check_column_order=False
        )


def test_dataset_to_df_failed_assay_to_df() -> None:
    """Test that Dataset.to_df raises error if all Assay.to_df fail."""
    seq1 = Sequence(name="seq1", value="APC", type="standard_sequence", alphabet="DNA")
    seq2 = Sequence(name="seq2", value="DEF", type="standard_sequence", alphabet="DNA")
    assay1 = Assay(
        name="assay1",
        records=[
            (seq1, 1.0),
            (seq2, 2.0),
        ],
        columns=["sequence", "DMS Score"],
    )
    assay2 = Assay(
        name="assay2",
        records=[(seq1, 1.0)],
        columns=["sequence", "DMS Score"],
    )
    dataset = Dataset(
        name="test_dataset",
        assay_targets=[AssayTarget(name="DMS Score2")],
        assays=[assay1, assay2],
    )
    try:
        df = dataset.to_df(target_names=["DMS Score2"])
    except ValueError as e:
        raise ValueError("Dataset to_df failed") from e
    else:
        assert df.shape == (0, 2), "DataFrame should be empty if all assays fail"


def test_dataset_to_df_drops_empty_target_rows() -> None:
    """Test that Dataset.to_df drops rows with all target values as None."""
    seq1 = Sequence(name="seq1", value="APC", type="standard_sequence", alphabet="DNA")
    seq2 = Sequence(name="seq2", value="DEF", type="standard_sequence", alphabet="DNA")
    assay1 = Assay(
        name="assay1",
        records=[
            (seq1, 1.0),
            (seq2, None),
        ],
        columns=["sequence", "DMS Score"],
    )
    assay2 = Assay(
        name="assay2",
        records=[
            (seq1, None),
            (seq2, None),
        ],
        columns=["sequence", "DMS Score"],
    )
    dataset = Dataset(
        name="test_dataset",
        assay_targets=[AssayTarget(name="DMS Score")],
        assays=[assay1, assay2],
    )
    df = dataset.to_df(target_names=["DMS Score"])
    assert df.shape == (1, 2), (
        "DataFrame should drop rows with all target values as None"
    )
    assert df["sequence"].to_list() == ["APC"]
    assert df["DMS Score"].to_list() == [1.0]


def test_dataset_with_dump_assays(tmp_path: Path) -> None:
    """Test creating a Dataset with dumped assays."""
    assay1 = Assay(
        name="assay1",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="DEF",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
    )
    assay2 = Assay(
        name="assay2",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="DEF",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                3.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
    )
    dataset = Dataset(
        name="test_dataset",
        assay_targets=[AssayTarget(name="DMS Score")],
        assays=[assay1, assay2],
    )
    archive_path = dataset.dump(path=tmp_path)
    assert archive_path.exists(), "Dataset archive was not created"

    zipped_file_names = ZipFile(archive_path).namelist()
    assert (
        DatasetArchiveLayout.ASSAYS_DIRECTORY / "assay1.csv"
    ).as_posix() in zipped_file_names
    assert (
        DatasetArchiveLayout.ASSAYS_DIRECTORY / "assay2.csv"
    ).as_posix() in zipped_file_names


def test_dataset_instance_from_dump_assays(tmp_path: Path) -> None:
    """Test a Dataset instance equality from dumped assays."""
    assay1 = Assay(
        name="assay1",
        records=[
            # The sequence names are kept same as
            (
                Sequence(
                    name="APC", value="APC", type="standard_sequence", alphabet="AA"
                ),
                1.56,
                0.5,
            ),
            (
                Sequence(
                    name="DEF", value="DEF", type="standard_sequence", alphabet="AA"
                ),
                2.0,
                0.6,
            ),
        ],
        columns=["sequence", "DMS Score", "DMS Score2"],
    )
    dataset = Dataset(
        name="test_dataset",
        assays=[assay1],
        assay_targets=[AssayTarget(name="DMS Score"), AssayTarget(name="DMS Score2")],
    )
    archive_path = dataset.dump(path=tmp_path)
    loaded_dataset = Dataset.from_path(archive_path)
    assert loaded_dataset.name == dataset.name
    assert len(loaded_dataset.assays) == len(dataset.assays)

    for original_assay, loaded_assay in zip(
        dataset.assays, loaded_dataset.assays, strict=True
    ):
        assert isinstance(loaded_assay, Assay)
        assert original_assay.name == loaded_assay.name
        assert original_assay.records == loaded_assay.records


def test_dataset_fails_with_duplicate_assay_names() -> None:
    """A dataset fails if there are duplicate assay names."""
    duplicate_names = ["duplicate1", "duplicate2"]
    assay1 = Assay(
        name=duplicate_names[0],
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                1.0,
            )
        ],
        columns=["sequence", "DMS Score"],
    )
    assay2 = Assay(
        name=duplicate_names[0],
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                2.0,
            )
        ],
        columns=["sequence", "DMS Score"],
    )
    assay3 = Assay(
        name=duplicate_names[1],
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                3.0,
            )
        ],
        columns=["sequence", "DMS Score"],
    )
    assay4 = Assay(
        name=duplicate_names[1],
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                4.0,
            )
        ],
        columns=["sequence", "DMS Score"],
    )

    with pytest.raises(
        ValidationError,
        match=rf"Duplicate names found in:.*Assays:.*{', '.join(duplicate_names)}",
    ):
        Dataset(name="test", assays=[assay1, assay2, assay3, assay4])


def test_dataset_fails_with_duplicate_assay_variable_names() -> None:
    """A dataset fails if there are duplicate assay names."""
    duplicate_names = ["duplicate1", "duplicate2"]
    assay_variables = [
        AssayVariable(name=duplicate_names[0]),
        AssayVariable(name=duplicate_names[0]),
        AssayVariable(name=duplicate_names[0]),
        AssayVariable(name=duplicate_names[1]),
        AssayVariable(name="unique1"),
        AssayVariable(name=duplicate_names[1]),
    ]

    match = rf"Duplicate names found in: AssayVariables:.*{', '.join(duplicate_names)}"
    with pytest.raises(ValidationError, match=match):
        Dataset(name="test", assay_variables=assay_variables)


def test_dataset_fails_with_duplicate_assay_target_names() -> None:
    """A dataset fails if there are duplicate assay target names."""
    duplicate_names = ["duplicate1", "duplicate2"]
    assay_targets = [
        AssayTarget(name=duplicate_names[0]),
        AssayTarget(name=duplicate_names[0]),
        AssayTarget(name=duplicate_names[0]),
        AssayTarget(name=duplicate_names[1]),
        AssayTarget(name="unique1"),
        AssayTarget(name=duplicate_names[1]),
    ]

    match = r"Duplicate names found in: AssayTargets:.*" + ", ".join(duplicate_names)
    with pytest.raises(ValidationError, match=match):
        Dataset(name="test", assay_targets=assay_targets)


def test_assay_repr() -> None:
    """Test the string representation of the Assay class."""
    assay = Assay(
        name="test assay",
        records=[
            (
                Sequence(
                    name="seq1", value="APC", type="standard_sequence", alphabet="AA"
                ),
                1.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
    )
    repr_str = repr(assay)
    assert "Assay(\n\tname='test assay'," in repr_str
    assert "description: None," in repr_str
    assert "variables: 0," in repr_str
    assert "records:" in repr_str

    assay = Assay(
        name="short desc",
        records=[
            (
                Sequence(
                    name="seq1", value="APC", type="standard_sequence", alphabet="AA"
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
        description="Short description.",
    )
    repr_str = repr(assay)
    assert "\tdescription: Short description." in repr_str

    long_desc = "A" * 61 + "BCD"
    assay = Assay(
        name="long desc",
        records=[
            (
                Sequence(
                    name="seq1", value="APC", type="standard_sequence", alphabet="AA"
                ),
                3.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
        description=long_desc,
    )
    repr_str = repr(assay)
    assert f"\tdescription: {long_desc[:60]}..." in repr_str

    assay = Assay(
        name="with vars",
        records=[
            (
                Sequence(
                    name="seq1", value="APC", type="standard_sequence", alphabet="AA"
                ),
                4.0,
            ),
        ],
        columns=["sequence", "DMS Score"],
        variables={"var1": 42, "var2": "x"},
    )
    repr_str = repr(assay)
    assert "variables: 2," in repr_str
    assert "\t\tvar1: 42," in repr_str
    assert "\t\tvar2: x," in repr_str

    records = [
        (
            Sequence(
                name=f"seq{i}", value=f"SEQ{i}", type="standard_sequence", alphabet="AA"
            ),
            i,
        )
        for i in range(5)
    ]
    assay = Assay(
        name="trunc records",
        records=records,
        columns=["sequence", "DMS Score"],
    )
    repr_str = repr(assay)
    assert "\t\t..." in repr_str

    assay = Assay(
        name="no records",
        records=[],
        columns=["sequence", "DMS Score"],
    )
    repr_str = repr(assay)
    assert "\t\t<no records>" in repr_str
