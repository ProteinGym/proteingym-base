from pathlib import Path

import pytest
from Bio.PDB.Structure import Structure as BioStructure
from pydantic import ValidationError

from pg2_dataset.models.structure import Structure, StructureManifestSection


def test_structure_manifest_section_minimal(tmp_path: Path) -> None:
    """Only path is required for a minimal structure manifest section."""
    path = tmp_path / "test.pdb"
    path.touch()

    try:
        StructureManifestSection(path=path)
    except ValidationError as e:
        raise AssertionError("Could not create StructureManifestSection") from e
    else:
        assert True, (
            "StructureManifestSection created successfully with minimal fields."
        )


def test_structure_manifest_missing_path() -> None:
    """A validation error is raised if path is missing."""
    match = (
        "validation error for StructureManifestSection\npath\n  "
        "Path does not point to a file"
    )
    with pytest.raises(ValidationError, match=match):
        StructureManifestSection(path="non_existent.pdb")


@pytest.mark.parametrize("field", ["name", "description"])
def test_structure_manifest_empty_string_field(tmp_path: Path, field: str) -> None:
    """A validation error is raised if <field> is empty."""
    path = tmp_path / "test.pdb"
    path.touch()

    match = (
        f"validation error for StructureManifestSection\n{field}\n  "
        "String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        StructureManifestSection(path=path, **{field: ""})


def test_structure_manifest_serialize_path_as_posix(tmp_path: Path) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "test.pdb"
    path.touch()

    section = StructureManifestSection(path=path)
    assert section.model_dump().get("path") == path.as_posix()


def test_structure_minimal() -> None:
    """A minimal Structure can be created."""
    try:
        Structure(name="test", value=BioStructure("test"))
    except ValidationError as e:
        raise AssertionError("Could not create Structure") from e
    else:
        assert True, "Structure created successfully with minimal fields."


@pytest.mark.parametrize("field", ["name", "description"])
def test_structure_empty_string_field(tmp_path: Path, field: str) -> None:
    """A validation error is raised if <field> is empty."""

    match = (
        f"validation error for Structure\n{field}\n  "
        "String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        Structure(value=BioStructure("test"), **{"name": "test", field: ""})
