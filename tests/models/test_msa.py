from pathlib import Path

import pytest
from pydantic import ValidationError

from pg2_dataset.models.msa import MSAManifestSection


def test_msa_manifest_section_minimal(tmp_path: Path) -> None:
    """Only path is required for a minimal MSA manifest section."""
    path = tmp_path / "test.msa"
    path.touch()

    try:
        MSAManifestSection(path=path)
    except ValidationError as e:
        raise AssertionError("Could not create MSAManifestSection") from e
    else:
        assert True, "MSAManifestSection created successfully with minimal fields."


def test_msa_manifest_section_missing_path() -> None:
    """A validation error is raised if path is missing."""
    match = (
        "validation error for MSAManifestSection\npath\n  Path does not point to a file"
    )
    with pytest.raises(ValidationError, match=match):
        MSAManifestSection(path="non_existent.msa")


@pytest.mark.parametrize("field", ["name", "description"])
def test_msa_manifest_section_empty_string_field(tmp_path: Path, field: str) -> None:
    """A validation error is raised if string <field> is empty."""
    path = tmp_path / "test.msa"
    path.touch()

    match = (
        f"validation error for MSAManifestSection\n{field}\n  "
        "String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        MSAManifestSection(path=path, **{field: ""})


def test_msa_manifest_section_serialize_path_as_posix(tmp_path: Path) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "test.msa"
    path.touch()

    section = MSAManifestSection(path=path)

    assert section.model_dump().get("path") == path.as_posix()
