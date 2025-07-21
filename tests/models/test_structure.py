from pathlib import Path

from pydantic import ValidationError

from pg2_dataset.models.structure import StructureManifestSection


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
