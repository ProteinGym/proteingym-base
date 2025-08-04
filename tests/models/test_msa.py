from pathlib import Path

import pytest
from Bio import AlignIO
from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import ValidationError

from pg2_dataset.models.dataset import Dataset, Manifest
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


def test_msa_manifest_section_with_directory(tmp_path: Path) -> None:
    """A directory is also allowed as a path."""
    path = tmp_path / "msas/"
    path.mkdir()

    try:
        MSAManifestSection(path=path)
    except ValidationError as e:
        raise AssertionError("Could not create MSAManifestSection") from e
    else:
        assert True, "MSAManifestSection created successfully with minimal fields."


def test_msa_manifest_section_missing_path() -> None:
    """A validation error is raised if path is missing."""
    match = (
        r"(?s)2 validation errors for MSAManifestSection"
        r".*Path does not point to a file"
        r".*Path does not point to a directory"
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
    """FASTA MSA file for testing."""
    path = tmp_path / "msa.fasta"
    AlignIO.write(multiple_sequence_alignment, path, "fasta")
    return path


def test_msa_from_manifest_section_with_fasta_file(fasta_file: Path) -> None:
    """A MSA can be created from a manifest section with FASTA file."""
    section = MSAManifestSection(path=fasta_file)

    msa = next(MSA.from_manifest_section(section))

    assert msa.name == "msa"
    assert isinstance(msa.value, MultipleSeqAlignment)


@pytest.fixture
def fasta_directory(
    tmp_path: Path, multiple_sequence_alignment: MultipleSeqAlignment
) -> Path:
    """A directory with two fasta files for testing."""
    path = tmp_path / "msas/"
    path.mkdir()
    fasta_file1 = path / "msa1.fasta"
    fasta_file2 = path / "msa2.fasta"
    AlignIO.write(multiple_sequence_alignment, fasta_file1, "fasta")
    AlignIO.write(multiple_sequence_alignment, fasta_file2, "fasta")
    return path


def test_msa_from_manifest_section_with_fasta_directory(fasta_directory: Path) -> None:
    """A MSA can be created from a manifest section with FASTA file."""
    section = MSAManifestSection(path=fasta_directory)

    msas = list(MSA.from_manifest_section(section))

    assert len(msas) == 2
    assert msas[0].name == "msa1"
    assert msas[1].name == "msa2"


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


def test_dataset_from_manifest_section_with_msa(
    fasta_file: Path, multiple_sequence_alignment: MultipleSeqAlignment
) -> None:
    """A dataset can be created from a manifest section with MSAs."""
    manifest_section = MSAManifestSection(path=fasta_file)
    manifest = Manifest(name="test_msa", msas=[manifest_section])
    dataset = Dataset.from_manifest(manifest)

    assert len(dataset.msas) == 1, "Dataset should contain one MSA"

    msa = dataset.msas[0]
    assert msa.name == "msa"
    assert msa.value.alignment == multiple_sequence_alignment.alignment
