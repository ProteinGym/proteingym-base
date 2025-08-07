import io
from pathlib import Path
from zipfile import ZipFile

import pytest
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import ValidationError

from pg2_dataset.models.constants import SequenceAlphabet, SequenceType
from pg2_dataset.models.dataset import Dataset
from pg2_dataset.models.sequence import (
    Sequence,
    SequenceFormat,
    SequenceManifestSection,
)


def test_sequence_manifest_section_minimal(tmp_path: Path) -> None:
    """Check with a minimal sequence manifest section."""
    path = tmp_path / "sequence.fasta"
    path.touch()

    try:
        SequenceManifestSection(
            sequence_type="wild_type", sequence_alphabet="DNA", path=path
        )
    except ValidationError as e:
        raise AssertionError("Could not create SequenceManifestSection") from e
    else:
        assert True, "SequenceManifestSection created successfully with minimal fields."


def test_sequence_manifest_section_with_relative_path(tmp_path: Path) -> None:
    """The path can be relative to another path."""
    path = tmp_path / "sequence.fasta"
    path.touch()
    context = {"relative_to_path": tmp_path}

    try:
        SequenceManifestSection.model_validate(
            {
                "sequence_type": "wild_type",
                "sequence_alphabet": "DNA",
                "path": "sequence.fasta",
            },
            context=context,
        )
    except ValidationError as e:
        raise AssertionError("Could not create SequenceManifestSection") from e
    else:
        assert True, "SequenceManifestSection created successfully with minimal fields."


def test_sequence_manifest_section_missing_path() -> None:
    """A validation error is raised if path is missing."""
    match = (
        r"(?s)2 validation errors for SequenceManifestSection"
        r".*Path does not point to a file"
        r".*Path does not point to a directory"
    )
    with pytest.raises(ValidationError, match=match):
        SequenceManifestSection(
            sequence_type="wild_type",
            sequence_alphabet="DNA",
            path="non_existent.fasta",
        )


@pytest.mark.parametrize("field", ["sequence_type", "sequence_alphabet"])
def test_sequence_manifest_section_empty_string_field(
    tmp_path: Path, field: str
) -> None:
    """A validation error is raised if string <field> is empty."""
    path = tmp_path / "sequence.fasta"
    path.touch()

    match = (
        f"validation error for SequenceManifestSection\n{field}\n  "
        "String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        SequenceManifestSection(
            path=path,
            **{"sequence_type": "wild_type", "sequence_alphabet": "DNA", field: ""},
        )


def test_sequence_manifest_section_serialize_path_as_posix(tmp_path: Path) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "sequence.fasta"
    path.touch()

    section = SequenceManifestSection(
        sequence_type="wild_type", sequence_alphabet="DNA", path=path
    )

    assert section.model_dump().get("path") == path.as_posix()


def test_sequence_manifest_section_serialize_path_as_posix_relative_to(
    tmp_path: Path,
) -> None:
    """The path is serialized as a Posix path relatie to another path."""
    path = tmp_path / "sequence.fasta"
    path.touch()
    context = {"relative_to_path": tmp_path}

    section = SequenceManifestSection(
        sequence_type="wild_type", sequence_alphabet="DNA", path=path
    )

    assert section.model_dump(context=context).get("path") == "sequence.fasta"


@pytest.mark.parametrize(
    "name, value, description, type, alphabet",
    [
        ("seq1", Seq("ATCG"), "Test sequence 1", SequenceType("wild_type"), "DNA"),
        ("seq2", Seq("AUGC"), "Test sequence 2", "starting_sequence", "RNA"),
        (
            "seq3",
            Seq("MKTAYIAKQRQISF"),
            "Test sequence 3",
            "engineered_sequence",
            SequenceAlphabet("AA"),
        ),
    ],
)
def test_sequence(name, value, description, type, alphabet):
    sequence = Sequence(
        name=name,
        value=value,
        description=description,
        type=SequenceType(type),
        alphabet=SequenceAlphabet(alphabet),
    )
    assert isinstance(sequence.value, Seq)
    assert isinstance(sequence.type, SequenceType)
    assert isinstance(sequence.alphabet, SequenceAlphabet)


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    "name, value, description, type, alphabet",
    [
        ("seq1", "ATCG", "Test sequence 1", "invalid_type", "DNA"),
        ("seq2", "AUGC", "Test sequence 2", "wild_type", "invalid_alphabet"),
        ("seq3", "", "Test sequence 3", "engineered_sequence", "AA"),
    ],
)
def test_invalid_sequence(name, value, description, type, alphabet):
    sequence = Sequence(
        name=name,
        value=value,
        description=description,
        type=SequenceType(type),
        alphabet=SequenceAlphabet(alphabet),
    )
    assert isinstance(sequence.value, Seq)
    assert isinstance(sequence.type, SequenceType)
    assert isinstance(sequence.alphabet, SequenceAlphabet)


def test_sequence_dump(tmp_path: Path) -> None:
    sequence = Sequence(
        name="test_seq",
        value=Seq("ATCG"),
        description="Test sequence for dumping",
        type=SequenceType("wild_type"),
        alphabet=SequenceAlphabet("DNA"),
    )
    sequence.dump(path=Path(tmp_path))
    file_path = Path(tmp_path) / f"test_seq.{SequenceFormat.FASTA.value}"
    assert file_path.exists()
    with open(file_path, "r") as f:
        content = f.read()
        assert ">test_seq" in content
        assert "ATCG" in content

    sequence_record = SeqIO.read(file_path, "fasta")
    assert isinstance(sequence_record, SeqRecord)


def test_dataset_dump_with_sequences(tmp_path: Path) -> None:
    """Test the zip file created by the Dataset dump with sequences.

    The created archive:
    - Should not contain a bad file.
    - Should contain the sequence file.
    - Should result the sequence being loaded correctly.
    """
    bio_sequence = Seq("ATCGATCGATCG")
    sequence = Sequence(
        name="seq",
        value=bio_sequence,
        description="Test sequence",
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    dataset = Dataset(name="test", sequences=[sequence])

    path = dataset.dump(path=tmp_path)

    zip = ZipFile(path)
    assert not zip.testzip(), "Dataset dump contains a bad file."
    assert "sequences/seq.fasta" in zip.namelist(), (
        "Sequence file not found in dataset dump."
    )

    with zip.open("sequences/seq.fasta", "r") as sequence_file:
        string_io = io.StringIO(sequence_file.read().decode("utf-8"))
        loaded_sequence = SeqIO.read(string_io, "fasta")
        assert bio_sequence == loaded_sequence.seq
