from enum import StrEnum
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import (
    BaseModel,
    ConfigDict,
    DirectoryPath,
    FilePath,
    SerializationInfo,
    field_serializer,
)

from pg2_dataset.models.constants import SequenceAlphabet, SequenceType


class SequenceManifestSection(BaseModel):
    """This is the manifest section for Sequences.

    They can be loaded from multiple directories.  This object is used to
    validate the sequence manifest.

    TODO:
        Discuss if this should be part of the manifest or of the dataset.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    sequence_type: str
    sequence_alphabet: str

    path: FilePath | DirectoryPath
    """The path to the sequence file."""

    @field_serializer("path", check_fields=True)
    def serialize_path(self, path: Path, info: SerializationInfo) -> str:
        """Serialize the path as a Posix path."""
        if info.context and info.context.get("relative_to_path"):
            path = path.relative_to(info.context["relative_to_path"])
        return path.as_posix()


class SequenceFormat(StrEnum):
    """Enumeration for sequence file formats."""

    FASTA = "fasta"
    FASTQ = "fastq"


class Sequence(BaseModel):
    """A sequence in the dataset."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )

    name: str | None = None
    """The name of the sequence."""

    value: Seq
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

        files = [f for f in files if f.suffix[1:] in SequenceFormat]
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

    def dump(
        self, *, path: Path | None = None, format: SequenceFormat = SequenceFormat.FASTA
    ) -> Path:
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
        if format not in SequenceFormat:
            raise ValueError(f"Unsupported sequence format: {format}")
        path = path or Path.cwd()
        if path.is_dir():
            path = path / f"{self.name}.{format.value}"
        record = SeqRecord(
            seq=self.value, id=self.name, name=self.name, description=self.description
        )
        SeqIO.write(record, path, format.value)
        return path
