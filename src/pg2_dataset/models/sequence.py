from pathlib import Path
from typing import Annotated
from enum import StrEnum
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    field_serializer,
    DirectoryPath,
    FilePath
)

from pg2_dataset.models.constants import SequenceAlphabet, SequenceType


def parse_sequence_value(value: str | Seq) -> Seq:
    """Convert a string value to a Seq object."""
    if len(value) < 1:
        raise ValueError("Sequence value must not be empty.")
    if isinstance(value, Seq):
        return value
    return Seq(value)


# Create manifest for sequence, currently supports only local and S3 directories.
# It can be extended to support xrefs.
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
        arbitrary_types_allowed=True, # Allow BioPython Seq Objects
    )

    name: str
    """The name of the sequence."""

    value: Annotated[Seq, BeforeValidator(lambda v: parse_sequence_value(v))]
    """The value of the sequence, a Seq object."""

    description: str
    """The description of the sequence."""

    type: SequenceType
    """The type of the sequence."""

    alphabet: SequenceAlphabet
    """The alphabet of the sequence."""
    

    @classmethod
    def from_manifest_section(cls, section: SequenceManifestSection) -> list["Sequence"]:
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
                alphabet=section.sequence_alphabet
            )
            for seq in sequences
        ]

    def dump(self, dir: Path) -> Path:
        dir.mkdir(parents=True, exist_ok=True)
        file_path = dir / f"{self.name}.{SequenceFormat.FASTA.value}"
        record = SeqRecord(
            seq=self.value, id=self.name, name=self.name, description=self.description
        )
        SeqIO.write(record, file_path, SequenceFormat.FASTA.value)
        return file_path