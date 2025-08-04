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
    parse_sequence_value,
)


def test_parse_sequence_value():
    assert isinstance(parse_sequence_value("ATCG"), Seq)
    assert isinstance(parse_sequence_value(Seq("ATCG")), Seq)
    with pytest.raises(ValueError):
        parse_sequence_value("")


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
    sequence.dump(Path(tmp_path))
    file_path = Path(tmp_path) / f"test_seq.{SequenceFormat.FASTA.value}"
    assert file_path.exists()
    with open(file_path, "r") as f:
        content = f.read()
        assert ">test_seq" in content
        assert "ATCG" in content

    sequence_record = SeqIO.read(file_path, "fasta")
    assert isinstance(sequence_record, SeqRecord)


@pytest.mark.parametrize(
    "sequence_type, sequence_alphabet, path",
    [
        (
            "wild_type",
            "DNA",
            "tests/test_data/io/files",
        ),
    ],
)
def test_sequence_manifest(sequence_type, sequence_alphabet, path):
    manifest = SequenceManifestSection(
        sequence_type=sequence_type,
        sequence_alphabet=sequence_alphabet,
        path=path,
    )
    assert manifest.sequence_type == sequence_type
    assert manifest.sequence_alphabet == sequence_alphabet


@pytest.mark.parametrize(
    "sequence_type, sequence_alphabet, path",
    [
        ("wild_type", None, "path/"),
        (None, "DNA", "path/"),
    ],
)
@pytest.mark.xfail(raises=ValidationError)
def test_sequence_manifest_missing_data(sequence_type, sequence_alphabet, path):
    manifest = SequenceManifestSection(
        sequence_type=sequence_type,
        sequence_alphabet=sequence_alphabet,
        path=Path(path),
    )
    assert len(manifest.sequence_type) > 0
    assert len(manifest.sequence_alphabet) > 0


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
