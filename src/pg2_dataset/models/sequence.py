from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import (
    BaseModel,
    ConfigDict,
    FilePath,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
)


class SequenceFormat(StrEnum):
    """Enumeration for sequence file formats."""

    FASTA = "fasta"
    FASTQ = "fastq"


class SequenceType(StrEnum):
    """The sequence types."""

    WILD_TYPE = "wild_type"
    STARTING_SEQUENCE = "starting_sequence"
    ENGINEERED_SEQUENCE = "engineered_sequence"


class SequenceAlphabet(StrEnum):
    """The sequence alphabets."""

    DNA = "DNA"
    RNA = "RNA"
    AA = "AA"


class SequenceManifestSection(BaseModel):
    """This is the manifest section for Sequences.

    They can be loaded from multiple directories.  This object is used to
    validate the sequence manifest.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    type: SequenceType
    """The type of the sequence."""

    alphabet: SequenceAlphabet
    """The alphabet of the sequence."""

    path: FilePath
    """The path to the sequence file."""

    @field_validator("path", mode="before", check_fields=True)
    def validate_path(cls, path: Path, info: ValidationInfo) -> Path:
        """Optionally, extend the path with the `relative_to_path` from the context."""
        if info.context and info.context.get("relative_to_path"):
            path = info.context["relative_to_path"] / path
        format = path.suffix[1:].lower()
        if format not in SequenceFormat:
            raise ValueError(f"Unsupported sequence format: {format}")
        return path

    @field_serializer("path", check_fields=True)
    def serialize_path(self, path: Path, info: SerializationInfo) -> str:
        """Serialize the path as a Posix path."""
        if info.context and info.context.get("relative_to_path"):
            path = path.relative_to(info.context["relative_to_path"])
        return path.as_posix()

    @field_serializer("type", "alphabet", check_fields=True)
    def _serialize_str_enum(self, str_enum: StrEnum) -> str:
        """Serialize a StrEnum as a string."""
        return str_enum.value


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
    ) -> Iterator["Sequence"]:
        """Create Sequence(s) from a sequence manifest section.

        Args:
            section (SequenceManifestSection): The sequence manifest section to create
                the Sequence from.

        Yields:
            Sequence: The created Sequence object.
        """
        sequences = SeqIO.parse(section.path, format=section.path.suffix[1:].lower())
        for seq in sequences:
            yield cls(
                name=seq.name,
                value=seq.seq,
                description=seq.description,
                type=section.type,
                alphabet=section.alphabet,
            )

    def as_manifest_section(self, *, path: Path) -> SequenceManifestSection:
        """Convert the sequence to a manifest section.

        Args:
            path (Path): The path to the sequence file (as created by
                `method:dump`).

        Returns:
            SequenceManifestSection: The manifest section for the sequence.
        """
        return SequenceManifestSection(
            path=path, alphabet=self.alphabet, type=self.type
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
