from pathlib import Path

import pytest
from pydantic import ValidationError

from pg2_dataset.models.assay import (
    Assay,
    AssayCondition,
    AssayManifestSection,
)


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
        description="Test assay",
        sequence="sequence",
        target="target",
        conditions={"test_cond1": "true", "test_cond2": 42},
        path=assay_file,
    )


def test_assay_manifest_section_invalid_columns(assay_file) -> None:
    """Test that AssayManifestSection raises error for invalid columns."""
    with pytest.raises(
        ValueError,
        match=r"Feature 'invalid_feature' not found in the file: .*assay.csv",
    ):
        AssayManifestSection(
            description="Test assay",
            sequence="invalid_feature",
            target="target",
            conditions={"test_cond1": "true", "test_cond2": 42},
            path=assay_file,
        )


def test_assay() -> None:
    """Test creating an Assay instance."""
    records = [("F1I", 1.56), ("F1L", 2.0)]
    Assay(conditions={"test_cond1": "true", "test_cond2": 42}, records=records)
    with pytest.raises(
        ValidationError,
        match=r"validation error for Assay\nconditions\n.*Input should be a valid "
        "dictionary",
    ):
        Assay(conditions="bad_condition", records=[("F1I", 1)])


def test_assay_from_manifest_section(assay_file: Path) -> None:
    """Test creating an Assay from a manifest section."""
    Assay.from_manifest_section(
        AssayManifestSection(
            sequence="sequence",
            target="target",
            path=assay_file,
            conditions={"test_cond1": "true", "test_cond2": 42},
        ),
    )


def test_as_manifest_section(assay_file: Path) -> None:
    """Test converting an Assay to a manifest section."""
    assay = Assay(
        records=[("ARFS", 1), ("SDFSDf", 2)],
    )
    manifest = assay.as_manifest_section(path=assay_file)
    assert manifest.path == assay_file
