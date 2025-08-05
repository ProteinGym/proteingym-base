import pytest
from pydantic import ValidationError

from pg2_dataset.models.assays import (
    Assay,
    AssayCondition,
    AssayManifestSection,
)


@pytest.fixture
def assay_file(tmp_path):
    """Fixture to create a temporary assay file."""
    path = tmp_path / "assay.csv"
    path.write_text(
        """sequence,target
        F1I,1.59
        F1L,0.6
        """
    )
    return path


def test_assay_condition_minimal():
    try:
        AssayCondition(name="test", type="boolean")
    except ValidationError:
        pytest.fail("Could not create AssayCondition with type and name")

    with pytest.raises(ValidationError):
        AssayCondition(name="test", type="bool")

    with pytest.raises(ValidationError):
        AssayCondition(type="categorical")


def test_assay_condition_assign_from_name():
    condition_list = [AssayCondition(name="test", type="boolean")]
    condition = AssayCondition.assign_from_name("test", condition_list)
    assert condition.name == "test"
    with pytest.raises(ValueError):
        AssayCondition.assign_from_name("non_existent", condition_list)


def test_assay_condition_assign_from_name_mutable():
    condition_list = [AssayCondition(name="test", type="boolean")]
    condition = AssayCondition.assign_from_name("test", condition_list)
    condition.value = "new_value"
    assert condition.value == "new_value"
    assert condition_list[0].value is None


def test_assay():
    records = [("F1I", 1.56), ("F1L", 2)]
    conditions = [
        AssayCondition(name="test_cond1", type="boolean"),
        AssayCondition(name="test_cond2", type="numerical"),
    ]
    Assay(conditions=conditions, records=records)
    with pytest.raises(ValidationError):
        Assay(conditions="bad_condition", records=[("F1I", "invalid_value")])


def test_assay_from_manifest_section(assay_file):
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

    with pytest.raises(ValueError):
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


def test_as_manifest_section(assay_file):
    assay = Assay(
        records=[("ARFS", 1), ("SDFSDf", 2)],
    )
    manifest = assay.as_manifest_section(path=assay_file)
    print(assay_file)
    assert manifest.path == assay_file
