from pathlib import Path
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from pg2_dataset.models.assay import (
    Assay,
    AssayCondition,
    AssayFormat,
    AssayManifestSection,
)
from pg2_dataset.models.dataset import Dataset, DatasetArchiveLayout, Manifest


@pytest.fixture
def assay_file(tmp_path) -> Path:
    """Fixture to create a temporary assay file."""
    path = tmp_path / "assay.csv"
    path.write_text("""
sequence,target
F1I,1.59
F1L,0.6""")
    return path


def test_assay_condition_minimal() -> None:
    """Test creating a minimal AssayCondition."""
    # This should not raise an error
    condition = AssayCondition(name="test")
    assert condition.name == "test"


def test_assay_condition_invalid_inputs() -> None:
    """Test invalid AssayCondition inputs raise ValidationError."""
    with pytest.raises(
        ValidationError,
        match=r"validation error for AssayCondition\nname\n.*Field required",
    ):
        AssayCondition(unit="test_unit")


def test_assay_manifest_section(assay_file) -> None:
    """Test creating an AssayManifestSection."""
    AssayManifestSection(
        name="test_assay",
        description="Test assay",
        sequence="sequence",
        target="target",
        conditions={"test_cond1": "true", "test_cond2": 42},
        path=assay_file,
    )


def test_assay_manifest_section_with_relative_path(tmp_path) -> None:
    """Test AssayManifestSection with a relative path."""
    path = tmp_path / "assay.csv"
    path.write_text("sequence,target\nF1I,1.59\nF1L,0.6")
    context = {"relative_to_path": tmp_path}

    section = AssayManifestSection.model_validate(
        {"path": "assay.csv"},
        context=context,
    )
    assert section.path == path


def test_assay_manifest_section_validate_feature_names(assay_file) -> None:
    """Test that AssayManifestSection raises error for invalid feature names."""
    with pytest.raises(
        ValueError,
        match=r"Feature 'invalid_feature' not found in the file: .*assay.csv",
    ):
        AssayManifestSection(
            name="test_assay",
            description="Test assay",
            sequence="invalid_feature",
            target="target",
            conditions={"test_cond1": "true", "test_cond2": 42},
            path=assay_file,
        )


def test_assay() -> None:
    """Test creating an Assay instance."""
    records = [("F1I", 1.56), ("F1L", 2.0)]
    Assay(
        name="assay",
        conditions={"test_cond1": "true", "test_cond2": 42},
        records=records,
    )
    with pytest.raises(
        ValidationError,
        match=r"validation error for Assay\nconditions\n.*Input should be a valid "
        "dictionary",
    ):
        Assay(name="assay", conditions="bad_condition", records=[("F1I", 1)])


def test_assay_hidden_variables(tmp_path: Path) -> None:
    """Test that sequence and target feature names are excluded from the model."""
    assay = Assay(
        name="assay",
        records=[("F1I", 1.56), ("F1L", 2.0)],
        sequence_feature_name="new_sequence",
        target_feature_name="new_target",
    )
    file_path = assay.dump(path=tmp_path)
    assay_models_keys = assay.model_dump().keys()
    assert all(
        hidden_var not in assay_models_keys
        for hidden_var in [
            "sequence_feature_name",
            "target_feature_name",
        ]
    )

    manifest_section = assay.as_manifest_section(path=file_path)
    assert manifest_section.sequence == "new_sequence"
    assert manifest_section.target == "new_target"


def test_assay_from_manifest_section(assay_file: Path) -> None:
    """Test creating an Assay from a manifest section."""
    Assay.from_manifest_section(
        AssayManifestSection(
            name="assay",
            sequence="sequence",
            target="target",
            path=assay_file,
            conditions={"test_cond1": "true", "test_cond2": 42},
        ),
    )


def test_as_manifest_section(assay_file: Path) -> None:
    """Test converting an Assay to a manifest section."""
    assay = Assay(
        name="assay",
        records=[("ARFS", 1), ("SDFSDf", 2)],
    )
    manifest = assay.as_manifest_section(path=assay_file)
    assert manifest.path == assay_file


def test_assay_dump(tmp_path) -> None:
    """Test dumping an Assay to a file."""
    assay = Assay(
        name="assay",
        records=[("F1I", 1.56), ("F1L", 2.0)],
        sequence_feature_name="sequence",
        target_feature_name="target",
    )
    dumped_path = assay.dump(path=tmp_path, format=AssayFormat.CSV)
    assert dumped_path == tmp_path / "assay.csv"
    assert (tmp_path / "assay.csv").exists()
    content = dumped_path.read_text()
    assert "F1I,1.56" in content
    assert "F1L,2.0" in content


# Tests with Dataset and Manifest
def test_manifest_validate_assay_conditions(assay_file: Path) -> None:
    """The manifest validates assay conditions."""
    Manifest(
        name="test_manifest",
        assay_conditions=[{"name": "pH"}, {"name": "temperature"}],
        assays=[{"path": assay_file, "conditions": {"pH": 7.0, "temperature": 37.0}}],
    )
    with pytest.raises(
        ValidationError,
        match=r"validation error for Manifest\n"
        r".*Value error, Assay .* contains undefined conditions",
    ):
        Manifest(
            name="test_manifest",
            assay_conditions=[{"name": "pH"}],
            assays=[{"path": assay_file, "conditions": {"temperature": 37.0}}],
        )


def test_dataset_with_dump_assays(tmp_path: Path) -> None:
    """Test creating a Dataset with dumped assays."""
    assay1 = Assay(
        name="assay1",
        records=[("F1I", 1.56), ("F1L", 2.0)],
        sequence_feature_name="sequence",
        target_feature_name="target",
    )
    assay2 = Assay(
        name="assay2",
        records=[("F2I", 1.0), ("F2L", 3.0)],
        sequence_feature_name="sequence",
        target_feature_name="target",
    )
    dataset = Dataset(
        name="test_dataset",
        assays=[assay1, assay2],
    )
    archive_path = dataset.dump(path=tmp_path)
    assert archive_path.exists(), "Dataset archive was not created"

    zip = ZipFile(archive_path)
    assert all(
        DatasetArchiveLayout.ASSAYS_DIRECTORY + f"{assay.name}{AssayFormat.CSV}"
        in zip.namelist()
        for assay in dataset.assays
    )


def test_dataset_instance_from_dump_assays(tmp_path: Path) -> None:
    """Test a Dataset instance equality from dumped assays."""
    assay1 = Assay(
        name="assay1",
        records=[("F1I", 1.56), ("F1L", 2.0)],
        sequence_feature_name="sequence",
        target_feature_name="target",
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
        assert original_assay.records == loaded_assay.records
