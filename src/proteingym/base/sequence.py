import dataclasses
from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path
from typing import Any

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
    """Fasta file format for biological sequences (usually amino acid sequences)"""

    FASTQ = "fastq"
    """FASTQ file format for biological sequences (usually nucleotide sequences)"""


class SequenceType(StrEnum):
    """The sequence types."""

    WILD_TYPE = "wild_type"
    """Prevalent form of the gene as found from natural populations"""

    STARTING_SEQUENCE = "starting_sequence"
    """A non-wild-type reference sequence for the design campaign"""

    ENGINEERED_SEQUENCE = "engineered_sequence"
    """A sequence with engineered mutations in them.

    For example, non-WT and not the reference sequence
    """

    CONTROL = "control_sequence"
    """Control sequences with know properties similar to the tested samples"""

    STANDARD = "standard_sequence"
    """Standard sequences used to calibrate and benchmark measurements"""


class SequenceAlphabet(StrEnum):
    """The sequence alphabets."""

    DNA = "DNA"
    """DNA sequences containing ACGT nucleotides"""

    RNA = "RNA"
    """RNA sequence containing ACGU nucleotides"""

    AA = "AA"
    """Amino acid sequence containing the twenty natural occuring nucleotides"""


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

    type: SequenceType | None = None
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


@dataclasses.dataclass
class Sequence:
    """A sequence in the dataset."""

    name: str
    """The name of the sequence."""

    value: Seq
    """The value of the sequence, a Seq object."""

    type: SequenceType
    """The type of the sequence."""

    alphabet: SequenceAlphabet
    """The alphabet of the sequence."""

    description: str | None = None
    """The description of the sequence."""

    def __eq__(self, item: Any) -> bool:
        """Implements the equality (==) operator for Sequence.
        
        For equality, we only look at the sequence value.
        """
        if isinstance(item, Sequence):
            return self.value == item.value
        return False

    def __repr__(self) -> str:
        """Return a string representation of the Sequence object."""
        lines = [f"Sequence(\n\tname='{self.name}',"]
        if self.description:
            desc = (
                self.description[:60] + "..."
                if len(self.description) > 60
                else self.description
            )
            lines.append(f"\tdescription: {desc},")
        else:
            lines.append("\tdescription: None,")

        lines.append(f"\ttype: {self.type},")
        lines.append(f"\talphabet: {self.alphabet},")
        value_str = str(self.value)
        if len(value_str) > 60:
            value_str = value_str[:60] + "..."
        lines.append(f"\tvalue: {value_str},")
        lines.append(")")
        return "\n".join(lines)

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
        for i, seq in enumerate(sequences):
            yield cls(
                name=seq.name if seq.name else f"{section.path.stem}_{i}",
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
