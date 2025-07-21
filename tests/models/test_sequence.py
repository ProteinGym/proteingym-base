from pathlib import Path

import pytest
from Bio import Seq, SeqIO, SeqRecord
from pydantic import ValidationError

from pg2_dataset.models.constants import SequenceAlphabet, SequenceType
from pg2_dataset.models.getter import Sources
from pg2_dataset.models.sequence import Sequence, SequenceManifestSection


@pytest.mark.parametrize(
    "name, value, description, type, alphabet",
    [
        ("seq1", Seq.Seq("ATCG"), "Test sequence 1", SequenceType("wild_type"), "DNA"),
        ("seq2", Seq.Seq("AUGC"), "Test sequence 2", "starting_sequence", "RNA"),
        (
            "seq3",
            Seq.Seq("MKTAYIAKQRQISF"),
            "Test sequence 3",
            "engineered_sequence",
            SequenceAlphabet("AA"),
        ),
    ],
)
def test_sequence(name, value, description, type, alphabet):
    seq = Sequence(
        name=name,
        value=value,
        description=description,
        type=SequenceType(type),
        alphabet=SequenceAlphabet(alphabet),
    )
    assert isinstance(seq.value, Seq.Seq)
    assert isinstance(seq.type, SequenceType)
    assert isinstance(seq.alphabet, SequenceAlphabet)


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
    seq = Sequence(
        name=name,
        value=value,
        description=description,
        type=SequenceType(type),
        alphabet=SequenceAlphabet(alphabet),
    )
    assert isinstance(seq.value, Seq.Seq)
    assert isinstance(seq.type, SequenceType)
    assert isinstance(seq.alphabet, SequenceAlphabet)


def test_sequence_dump(tmp_path):
    seq = Sequence(
        name="test_seq",
        value=Seq.Seq("ATCG"),
        description="Test sequence for dumping",
        type=SequenceType("wild_type"),
        alphabet=SequenceAlphabet("DNA"),
    )
    dir = Path(tmp_path)
    seq.dump(dir)
    file_path = tmp_path / "test_seq.fasta"
    assert file_path.exists()
    with open(file_path, "r") as f:
        content = f.read()
        assert ">test_seq" in content
        assert "ATCG" in content

    seq = SeqIO.read(file_path, "fasta")
    assert isinstance(seq, SeqRecord.SeqRecord)


@pytest.mark.parametrize(
    "sequence_type, sequence_alphabet, local, s3",
    [
        (
            "wild_type",
            "DNA",
            ["path/"],
            [],
        ),
        (
            "wild_type",
            "DNA",
            ["path/"],
            [],
        ),
    ],
)
def test_sequence_manifest(sequence_type, sequence_alphabet, local, s3):
    sources = Sources(local=local, s3=s3)

    manifest = SequenceManifestSection(
        sequence_type=sequence_type,
        sequence_alphabet=sequence_alphabet,
        sources=sources,
    )
    assert manifest.sequence_type == sequence_type
    assert manifest.sequence_alphabet == sequence_alphabet


@pytest.mark.parametrize(
    "sequence_type, sequence_alphabet, local, s3",
    [
        ("wild_type", None, ["path/"], []),
        (None, "DNA", ["path/"], []),
    ],
)
@pytest.mark.xfail(raises=ValidationError)
def test_sequence_manifest_missing_data(sequence_type, sequence_alphabet, local, s3):
    manifest = SequenceManifestSection(
        sequence_type=sequence_type,
        sequence_alphabet=sequence_alphabet,
        sources=Sources(dirs=Sources(local=local, s3=s3)),
    )
    assert len(manifest.sequence_type) > 0
    assert len(manifest.sequence_alphabet) > 0
