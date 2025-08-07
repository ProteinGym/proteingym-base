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
    condition = AssayCondition(name="test", type="boolean")
    assert condition.name == "test"
    assert condition.type == "boolean"


def test_assay_condition_invalid_inputs() -> None:
    """Test invalid AssayCondition inputs raise ValidationError."""
    with pytest.raises(
        ValidationError,
        match=r"validation error for AssayCondition\ntype\n.*"
        "Input should be 'categorical', 'numerical' or 'boolean'",
    ):
        AssayCondition(name="test", type="bool")

    with pytest.raises(
        ValidationError,
        match=r"validation error for AssayCondition\nname\n.*Field required",
    ):
        AssayCondition(type="categorical")


def test_assay_condition_assign_from_name() -> None:
    """Test assigning a condition from a name."""
    condition_list = [AssayCondition(name="test", type="boolean")]
    condition = AssayCondition.assign_from_name("test", condition_list)
    assert condition.name == "test"
    with pytest.raises(
        ValueError, match="Condition 'non_existent' not found in available conditions."
    ):
        AssayCondition.assign_from_name("non_existent", condition_list)


def test_assay_condition_assign_from_name_mutable() -> None:
    """Test assigning a condition from a name and modifying it."""
    # This test ensures that modifying the condition does not affect the original list
    # by creating a new instance.
    condition_list = [AssayCondition(name="test", type="boolean")]
    condition = AssayCondition.assign_from_name("test", condition_list)
    condition.value = "new_value"
    assert condition.value == "new_value"
    assert condition_list[0].value is None


def test_assay() -> None:
    """Test creating an Assay instance."""
    records = [("F1I", 1.56), ("F1L", 2.0)]
    conditions = [
        AssayCondition(name="test_cond1", type="boolean"),
        AssayCondition(name="test_cond2", type="numerical"),
    ]
    Assay(conditions=conditions, records=records)
    with pytest.raises(
        ValidationError,
        match=r"validation error for Assay\nconditions\n.*Input should be a valid list",
    ):
        Assay(conditions="bad_condition", records=[("F1I", 1)])


def test_assay_from_manifest_section(assay_file: Path) -> None:
    """Test creating an Assay from a manifest section."""
    conditions = [
        AssayCondition(name="test_cond1", type="boolean"),
        AssayCondition(name="test_cond2", type="numerical"),
    ]
    assay = Assay.from_manifest_section(
        AssayManifestSection(
            sequence="sequence",
            target="target",
            path=assay_file,
            conditions={"test_cond1": "true", "test_cond2": 42},
        ),
        conditions,
    )
    assert all([isinstance(cond, AssayCondition) for cond in assay.conditions])

    # Test with bad conditions
    with pytest.raises(
        ValueError, match="Condition 'bad_condition' not found in available conditions."
    ):
        Assay.from_manifest_section(
            AssayManifestSection(
                sequence="sequence",
                target="target",
                path=assay_file,
                conditions={
                    "bad_condition": "true",
                },
            ),
            conditions,
        )


def test_as_manifest_section(assay_file: Path) -> None:
    """Test converting an Assay to a manifest section."""
    assay = Assay(
        records=[("ARFS", 1), ("SDFSDf", 2)],
    )
    manifest = assay.as_manifest_section(path=assay_file)
    assert manifest.path == assay_file
