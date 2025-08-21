import io
from pathlib import Path
from zipfile import ZipFile

import pytest
import toml
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import ValidationError

from pg2_dataset.dataset import Dataset
from pg2_dataset.manifest import MANIFEST_LATEST_VERSION, Manifest
from pg2_dataset.sequence import (
    Sequence,
    SequenceAlphabet,
    SequenceFormat,
    SequenceManifestSection,
    SequenceType,
)


def test_sequence_manifest_section_minimal(tmp_path: Path) -> None:
    """Check with a minimal sequence manifest section."""
    path = tmp_path / "sequence.fasta"
    path.touch()

    try:
        SequenceManifestSection(type="wild_type", alphabet="DNA", path=path)
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
                "type": "wild_type",
                "alphabet": "DNA",
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
        "validation error for SequenceManifestSection\npath\n  "
        "Path does not point to a file"
    )
    with pytest.raises(ValidationError, match=match):
        SequenceManifestSection(
            type="wild_type",
            alphabet="DNA",
            path=Path("non_existent.fasta"),
        )


def test_sequence_manifest_section_serialize_path_as_posix(tmp_path: Path) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "sequence.fasta"
    path.touch()

    section = SequenceManifestSection(type="wild_type", alphabet="DNA", path=path)

    assert section.model_dump().get("path") == path.as_posix()


def test_sequence_manifest_section_serialize_path_as_posix_relative_to(
    tmp_path: Path,
) -> None:
    """The path is serialized as a Posix path relatie to another path."""
    path = tmp_path / "sequence.fasta"
    path.touch()
    context = {"relative_to_path": tmp_path}

    section = SequenceManifestSection(type="wild_type", alphabet="DNA", path=path)

    assert section.model_dump(context=context).get("path") == "sequence.fasta"


def test_sequence_manifest_section_serialize_strenum_as_string(tmp_path: Path) -> None:
    """The sequence type and alphabet is serialized as a string.

    The StrEnum is tricky to test as it is both a string and enum, hence,
    we test it with a TOML serialization to be sure it is serialized correctly.
    """
    path = tmp_path / "sequence.fasta"
    path.touch()

    section = SequenceManifestSection(
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
        path=path,
    )

    section_in_toml = toml.dumps(section.model_dump())
    assert SequenceType.WILD_TYPE.value in section_in_toml
    assert SequenceAlphabet.DNA.value in section_in_toml


def test_sequence_manifest_section_raises_validation_error_for_unsupported_format(
    tmp_path: Path,
) -> None:
    """The manifest section raises a validation error for unsupported formats."""
    path = tmp_path / "sequence.unsupported"
    path.touch()

    match = (
        "validation error for SequenceManifestSection\npath\n  Value error, "
        "Unsupported sequence format: unsupported"
    )
    with pytest.raises(ValidationError, match=match):
        SequenceManifestSection(type="wild_type", alphabet="DNA", path=path)


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


def test_sequence_from_manifest_section_multiple_seqs_in_file(tmp_path: Path) -> None:
    fasta_file = tmp_path / "sequences.fasta"
    fasta_file.write_text(">seq1\nATCG\n>seq2\nAUGC\n")

    section = SequenceManifestSection(
        type="wild_type",
        alphabet="DNA",
        path=fasta_file,
    )

    sequences = list(Sequence.from_manifest_section(section))
    assert len(sequences) == 2
    assert all(isinstance(seq, Sequence) for seq in sequences)


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


def test_dataset_dump_with_sequence(tmp_path: Path) -> None:
    """Test the zip file created by the Dataset dump with a sequence.

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


def test_dataset_dump_with_sequences_contains_archive_names(tmp_path: Path) -> None:
    """Same as `test_dataset_dump_with_sequences`, but with multiple sequences."""
    expected = {"sequences/sequence1.fasta", "sequences/sequence2.fasta"}
    sequence1 = Sequence(
        name="sequence1",
        value=Seq("CCCCCCCCCCCCC"),
        description="Test sequence 1",
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    sequence2 = Sequence(
        name="sequence2",
        value=Seq("AAAAAAAAAAAA"),
        description="Test sequence 2",
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    dataset = Dataset(name="test", sequences=[sequence1, sequence2])

    path = dataset.dump(path=tmp_path)

    archive_names = ZipFile(path).namelist()
    assert not expected - set(archive_names), (
        f"Expected the following archive names {expected}"
    )


def test_dataset_with_sequences_dump_from_path_unit(tmp_path: Path) -> None:
    """Dumping a dataset with sequences should return the same after reading"""
    sequence1 = Sequence(
        name="sequence1",
        value=Seq("CCCCCCCCCCCCC"),
        description="Test sequence 1",
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    sequence2 = Sequence(
        name="sequence2",
        value=Seq("AAAAAAAAAAAA"),
        description="Test sequence 2",
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    dataset = Dataset(name="test", sequences=[sequence1, sequence2])

    path = dataset.dump(path=tmp_path)

    loaded_dataset = Dataset.from_path(path)

    # TODO (#255): Implement Dataset.__eq__ and use it here instead of multiple asserts
    assert loaded_dataset.name == dataset.name
    assert len(loaded_dataset.sequences) == len(dataset.sequences)
    for loaded_sequence, sequence in zip(
        loaded_dataset.sequences, dataset.sequences, strict=True
    ):
        assert loaded_sequence.name == sequence.name
        assert loaded_sequence.value == sequence.value


def test_dataset_fails_with_duplicate_sequence_names() -> None:
    """A dataset with duplicate sequence names should raise a ValueError."""
    duplicate_names = ["duplicate1", "duplicate2"]
    sequence1 = Sequence(
        name=duplicate_names[0],
        value=Seq("CCCCCCCCCCCCC"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    sequence2 = Sequence(
        name=duplicate_names[0],
        value=Seq("AAAAAAAAAAAA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    sequence3 = Sequence(
        name=duplicate_names[1],
        value=Seq("GGGGGGGGGGGGG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    sequence4 = Sequence(
        name=duplicate_names[1],
        value=Seq("TTTTTTTTTTTTT"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )

    with pytest.raises(
        ValidationError,
        match=rf"Duplicate names found in:.*Sequences:.*{', '.join(duplicate_names)}",
    ):
        Dataset(name="test", sequences=[sequence1, sequence2, sequence3, sequence4])


def test_dataset_loads_multiple_sequences_from_file(tmp_path: Path) -> None:
    """Test loading multiple sequences from a file."""
    fasta_file = tmp_path / "sequences.fasta"
    fasta_file.write_text(">seq1\nATCG\n>seq2\nAUGC\n")

    dataset_manifest = Manifest(
        version=MANIFEST_LATEST_VERSION,
        name="test",
        sequences=[
            {
                "path": fasta_file,
                "type": "wild_type",
                "alphabet": "DNA",
            }
        ],
    )
    dataset = Dataset.from_manifest(dataset_manifest)
    assert len(dataset.sequences) == 2
    assert all(isinstance(seq, Sequence) for seq in dataset.sequences)
    assert dataset.sequences[0].name == "seq1"
    assert dataset.sequences[1].name == "seq2"
