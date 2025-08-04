from enum import StrEnum
from pathlib import Path
from typing import Annotated

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    DirectoryPath,
    FilePath,
    field_serializer,
)

from pg2_dataset.models.constants import SequenceAlphabet, SequenceType


def parse_sequence_value(value: str | Seq) -> Seq:
    """Convert a string value to a Seq object."""
    if len(value) < 1:
        raise ValueError("Sequence value must not be empty.")
    if isinstance(value, Seq):
        return value
    return Seq(value)


class SequenceManifestSection(BaseModel):
    """This is the manifest section for Sequences.

    They can be loaded from multiple directories.  This object is used to
    validate the sequence manifest.

    TODO:
        Discuss if this should be part of the manifest or of the dataset.
    """

    sequence_type: str
    sequence_alphabet: str
    path: FilePath | DirectoryPath

    @field_serializer("path")
    def serialize_path(self, path: Path) -> str:
        """Serialize the path to a string."""
        return path.as_posix()


class SequenceFormat(StrEnum):
    """Enumeration for sequence file formats."""

    FASTA = "fasta"
    FASTQ = "fastq"


class Sequence(BaseModel):
    """A sequence in the dataset."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Allow BioPython Seq Objects
    )

    name: str | None = None
    """The name of the sequence."""

    value: Annotated[Seq, BeforeValidator(lambda v: parse_sequence_value(v))]
    """The value of the sequence, a Seq object."""

    description: str | None = None
    """The description of the sequence."""

    type: SequenceType
    """The type of the sequence."""

    alphabet: SequenceAlphabet
    """The alphabet of the sequence."""

    @classmethod
    def from_manifest_section(
        cls, section: SequenceManifestSection
    ) -> list["Sequence"]:
        """Create a list of Sequence from a manifest section."""

        if section.path.is_dir():
            files = list(section.path.glob("*.*"))
        elif section.path.is_file():
            files = [section.path]
        else:
            raise ValueError("Path must be a directory or a file.")

        files = [f for f in files if f.suffix in [ft.value for ft in SequenceFormat]]
        sequences = [SeqIO.read(file, format=file.suffix[1:]) for file in files]

        return [
            cls(
                name=seq.name,
                value=seq.seq,
                description=seq.description,
                type=section.sequence_type,
                alphabet=section.sequence_alphabet,
            )
            for seq in sequences
        ]

    def as_manifest_section(self, *, path: Path) -> SequenceManifestSection:
        """Convert the sequence to a manifest section.

        Args:
            path (Path): The path to the sequence file (as created by
                `method:dump`).

        Returns:
            SequenceManifestSection: The manifest section for the sequence.
        """
        return SequenceManifestSection(
            path=path, sequence_alphabet=self.alphabet, sequence_type=self.type
        )

    def dump(self, path: Path, format: SequenceFormat = SequenceFormat.FASTA) -> Path:
        """Dump the sequence to a file in `path` directory.

        Biopython is used for writing the sequence to a file. The following
        formats are supported:
        - FASTA (.fasta)
        - FASTQ (.fastq)

        Args:
            path (Path): The output directory path to dump the sequence to. If
                None, the current working directory is used.
            format (SequenceFormat): The format to dump the sequence in.

        Raises:
            ValueError: If the path does not have a valid sequence file extension.
        """
        file_path = path / f"{self.name}.{format.value}"
        assert file_path.suffix[1:] in [
            SequenceFormat.FASTA.value,
            SequenceFormat.FASTQ.value,
        ]
        record = SeqRecord(
            seq=self.value, id=self.name, name=self.name, description=self.description
        )
        SeqIO.write(record, file_path, SequenceFormat.FASTA.value)
        return file_path
