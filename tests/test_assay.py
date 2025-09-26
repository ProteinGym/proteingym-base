from pathlib import Path
from zipfile import ZipFile

import pytest
from pydantic import ValidationError
from semver import Version

from pg2_dataset.assay import (
    Assay,
    AssayFormat,
    AssayManifestSection,
    AssayTarget,
    AssayVariable,
)
from pg2_dataset.dataset import Dataset, DatasetArchiveLayout
from pg2_dataset.manifest import Manifest
from pg2_dataset.sequence import Sequence, SequenceAlphabet


@pytest.fixture
def assay_file(tmp_path: Path) -> Path:
    """Fixture to create a temporary assay file."""
    path = tmp_path / "assay.csv"
    path.write_text(
        """
sequence,target
F1I,1.59
F1L,0.6""".lstrip()
    )
    return path


def test_assay_variable_minimal() -> None:
    """Test creating a minimal AssayVariable."""
    # This should not raise an error
    try:
        variable = AssayVariable(name="test")
    except ValidationError as e:
        AssertionError(f"AssayVariable raised ValidationError: {e}")
    assert variable.name == "test"


def test_assay_variable_invalid_inputs() -> None:
    """Test invalid AssayVariable inputs raise ValidationError."""
    with pytest.raises(
        ValidationError,
        match=r"validation error for AssayVariable\nname\n.*Field required",
    ):
        AssayVariable()


def test_assay_target_minimal() -> None:
    """Test creating a minimal AssayTarget."""
    # This should not raise an error
    try:
        target = AssayTarget(name="DMS Score")
    except ValidationError as e:
        raise AssertionError(f"AssayTarget raised ValidationError: {e}") from e
    else:
        assert target.name == "DMS Score"


def test_assay_target_invalid_inputs() -> None:
    """Test invalid AssayTarget inputs raise ValidationError."""
    with pytest.raises(
        ValidationError,
        match=r"validation error for AssayTarget\nname\n.*Field required",
    ):
        AssayTarget()


def test_assay_manifest_section(assay_file: Path) -> None:
    """Test creating an AssayManifestSection."""
    try:
        section = AssayManifestSection(
            name="test_assay",
            description="Test assay",
            sequence="sequence",
            sequence_alphabet="AA",
            targets={"DMS Score": "target"},
            variables={"test_cond1": "true", "test_cond2": 42},
            path=assay_file,
        )
    except ValidationError as e:
        AssertionError(f"AssayManifestSection raised ValidationError: {e}")

    assert isinstance(section.path, Path)
    with assay_file.open() as f:
        content = f.read()
    assert section.sequence in content
    assert all(target in content for target in section.targets.values())


def test_assay_manifest_section_with_relative_path(tmp_path: Path) -> None:
    """Test AssayManifestSection with a relative path."""
    path = tmp_path / "assay.csv"
    path.write_text("sequence,target\nF1I,1.59\nF1L,0.6")
    context = {"relative_to_path": tmp_path}
    section = AssayManifestSection.model_validate(
        {"path": "assay.csv", "sequence_alphabet": "AA"},
        context=context,
    )
    assert section.path == path


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
            targets={"DMS Score": "target"},
            variables={"test_cond1": "true", "test_cond2": 42},
            path=assay_file,
        )


def test_assay() -> None:
    """Test creating an Assay instance."""
    records = [
        (
            Sequence(
                name="seq1",
                value="APC",
                type="standard_sequence",
                alphabet=SequenceAlphabet.DNA,
            ),
            [AssayTarget(name="DMS Score", value=1.56)],
        ),
        (
            Sequence(
                name="seq2",
                value="DEF",
                type="standard_sequence",
                alphabet=SequenceAlphabet.DNA,
            ),
            [AssayTarget(name="DMS Score", value=2.0)],
        ),
    ]

    try:
        assay = Assay(
            name="assay",
            variables={"test_cond1": "true", "test_cond2": 42},
            records=records,
            sequence_alphabet="AA",
        )
    except ValidationError as e:
        AssertionError(f"Assay raised ValidationError: {e}")
    assert assay.sequence_feature_name == "sequence"
    assert all(
        target_name in ["DMS Score"] for target_name in assay.target_feature_names
    )


def test_assay_from_manifest_section(assay_file: Path) -> None:
    """Test creating an Assay from a manifest section."""
    try:
        assay = Assay.from_manifest_section(
            AssayManifestSection(
                name="assay",
                sequence="sequence",
                sequence_alphabet=SequenceAlphabet.DNA,
                targets={"DMS Score": "target"},
                path=assay_file,
                variables={"test_cond1": "true", "test_cond2": 42},
            ),
        )
    except ValidationError as e:
        AssertionError(f"Assay raised ValidationError: {e}")
    assert assay.name == "assay"
    assert len(assay.records) == 2
    for rec in assay.records:
        assert isinstance(rec[0], Sequence)
        assert all(isinstance(t, AssayTarget) for t in rec[1])


def test_as_manifest_section(tmp_path: Path) -> None:
    """Test converting an Assay to a manifest section."""
    assay = Assay(
        name="assay",
        sequence_alphabet=SequenceAlphabet.DNA,
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                [AssayTarget(name="DMS Score", value=1.56)],
            ),
            (
                Sequence(
                    name="seq2",
                    value="DEF",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                [AssayTarget(name="DMS Score", value=2.0)],
            ),
        ],
    )
    path = assay.dump(path=tmp_path, format=AssayFormat.CSV)
    manifest = assay.as_manifest_section(path=path)
    assert "DMS Score" in manifest.path.read_text()
    assert "sequence" in manifest.path.read_text()
    assert "1.56" in manifest.path.read_text()
    assert "2.0" in manifest.path.read_text()


def test_assay_dump(tmp_path: Path) -> None:
    """Test dumping an Assay to a file."""
    assay = Assay(
        name="assay",
        records=[
            (
                Sequence(
                    name="seq1", value="APC", type="standard_sequence", alphabet="AA"
                ),
                [AssayTarget(name="DMS Score", value=1.56)],
            ),
            (
                Sequence(
                    name="seq2", value="DEF", type="standard_sequence", alphabet="AA"
                ),
                [AssayTarget(name="DMS Score", value=2.0)],
            ),
        ],
        sequence_alphabet="AA",
        sequence_feature_name="sequence",
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
                    "sequence_type": SequenceAlphabet.DNA,
                    "variables": {"pH": 7.0, "temperature": 37.0},
                }
            ],
        )
    except ValidationError as e:
        AssertionError(f"Manifest raised ValidationError: {e}")
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
                [AssayTarget(name="DMS Score", value=1.56)],
            ),
            (
                Sequence(
                    name="seq2",
                    value="DEF",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                [AssayTarget(name="DMS Score", value=2.0)],
            ),
        ],
        sequence_alphabet="AA",
        sequence_feature_name="sequence",
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
                [AssayTarget(name="DMS Score", value=1.0)],
            ),
            (
                Sequence(
                    name="seq2",
                    value="DEF",
                    type="standard_sequence",
                    alphabet=SequenceAlphabet.DNA,
                ),
                [AssayTarget(name="DMS Score", value=3.0)],
            ),
        ],
        sequence_alphabet="AA",
        sequence_feature_name="sequence",
    )
    dataset = Dataset(
        name="test_dataset",
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
                [AssayTarget(name="DMS Score", value=1.56)],
            ),
            (
                Sequence(
                    name="DEF", value="DEF", type="standard_sequence", alphabet="AA"
                ),
                [AssayTarget(name="DMS Score", value=2.0)],
            ),
        ],
        sequence_alphabet="AA",
        sequence_feature_name="sequence",
    )
    dataset = Dataset(
        name="test_dataset",
        assays=[assay1],
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
        print(original_assay.records[0])
        print(loaded_assay.records[0])
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
                [AssayTarget(name="DMS Score", value=1.0)],
            )
        ],
        sequence_alphabet="AA",
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
                [AssayTarget(name="DMS Score", value=2.0)],
            )
        ],
        sequence_alphabet="AA",
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
                [AssayTarget(name="DMS Score", value=3.0)],
            )
        ],
        sequence_alphabet="AA",
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
                [AssayTarget(name="DMS Score", value=4.0)],
            )
        ],
        sequence_alphabet="AA",
    )

    with pytest.raises(
        ValidationError,
        match=rf"Duplicate names found in:.*Assays:.*{', '.join(duplicate_names)}",
    ):
        Dataset(name="test", assays=[assay1, assay2, assay3, assay4])
