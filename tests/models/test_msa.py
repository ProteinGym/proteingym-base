from pathlib import Path

import pytest
from Bio import AlignIO
from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import ValidationError

from pg2_dataset.models.msa import MSA, MSAManifestSection


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


def test_msa_manifest_section_with_relative_path(tmp_path: Path) -> None:
    """The path can be relative to another path."""
    path = tmp_path / "test.msa"
    path.touch()
    context = {"relative_to_path": tmp_path}

    try:
        MSAManifestSection.model_validate({"path": "test.msa"}, context=context)
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


def test_msa_manifest_section_serialize_path_as_posix_relative_to(
    tmp_path: Path,
) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "test.msa"
    path.touch()
    context = {"relative_to_path": tmp_path}

    section = MSAManifestSection(path=path)

    assert section.model_dump(context=context).get("path") == "test.msa"


def test_msa_minimal() -> None:
    """Only name and value are required for a minimal MSA."""
    try:
        MSA(name="test", value=MultipleSeqAlignment([]))
    except ValidationError as e:
        raise AssertionError("Could not create MSA") from e
    else:
        assert True, "MSA created successfully with minimal fields."


@pytest.mark.parametrize("field", ["name", "description"])
def test_msa_empty_string_field(field: str) -> None:
    """A validation error is raised if string <field> is empty."""

    match = (
        f"validation error for MSA\n{field}\n  String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        MSA(value=MultipleSeqAlignment([]), **{"name": "test", field: ""})


@pytest.fixture
def multiple_sequence_alignment() -> MultipleSeqAlignment:
    """Minimal biopython multiple sequence alignment for testing."""
    alignment = MultipleSeqAlignment([])

    a = SeqRecord(Seq("AAAACGT"), id="Alpha")
    b = SeqRecord(Seq("AAA-CGT"), id="Beta")
    c = SeqRecord(Seq("AAAAGGT"), id="Gamma")
    alignment = MultipleSeqAlignment(
        [a, b, c], annotations={"tool": "demo"}, column_annotations={"stats": "CCCXCCC"}
    )
    return alignment


@pytest.fixture
def fasta_file(
    tmp_path: Path, multiple_sequence_alignment: MultipleSeqAlignment
) -> Path:
    """FASTA structure file for testing."""
    path = tmp_path / "structure.fasta"
    AlignIO.write(multiple_sequence_alignment, path, "fasta")
    return path


def test_msa_from_manifest_section_with_fasta(fasta_file: Path) -> None:
    """A MSA can be created from a manifest section with FASTA file."""
    section = MSAManifestSection(path=fasta_file)

    msa = MSA.from_manifest_section(section)

    assert msa.name == "structure"
    assert isinstance(msa.value, MultipleSeqAlignment)


def test_msa_as_manifest_section(fasta_file: Path) -> None:
    """A MSA can be converted to a manifest section."""
    msa = MSA(name="test_msa", value=MultipleSeqAlignment([]))

    section = msa.as_manifest_section(path=fasta_file)

    assert section.path == fasta_file
    assert section.name == "test_msa"
    assert section.description is None


def test_msa_dump_to_file(
    tmp_path: Path, multiple_sequence_alignment: MultipleSeqAlignment
) -> None:
    """A MSA can be dumped to a FASTA file."""
    msa = MSA(name="test", value=multiple_sequence_alignment)

    path = msa.dump(path=tmp_path / "msa.fasta")

    loaded_msa = AlignIO.read(path, path.suffix[1:].lower())
    assert msa.value.alignment == loaded_msa.alignment


def test_msa_dump_to_directory(
    tmp_path: Path, multiple_sequence_alignment: MultipleSeqAlignment
) -> None:
    """A MSA can be dumped to a FASTA file inside a directory."""
    msa = MSA(name="test", value=multiple_sequence_alignment)

    path = msa.dump(path=tmp_path)

    loaded_msa = AlignIO.read(path, path.suffix[1:].lower())
    assert msa.value.alignment == loaded_msa.alignment
