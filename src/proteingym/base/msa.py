import dataclasses
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
from Bio import AlignIO
from Bio.Align import MultipleSeqAlignment
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)


class MSAFormat(StrEnum):
    """Enumeration for MSA file formats."""

    FASTA = "fasta"
    """MSAs following the fasta format, also for a2m files."""


class MSAWeightFormat(StrEnum):
    """Enumeration for MSA weight file formats."""

    NPY = "npy"
    """NumPy binary file format."""


class MSAMetadataManifestSection(BaseModel):
    """Metadata for the multiple sequence alignment."""

    model_config = ConfigDict(
        extra="allow",
        frozen=True,
        use_attribute_docstrings=True,
    )
    """Configuration for the Pydantic model."""

    num_significant: int | None = None
    """Number of evolutionary couplings that are considered significant."""

    bit_score: float | None = None
    """Bitscore threshold.

    Used to generate the alignment divided by the length of the target protein.
    """

    theta: float | None = None
    """Hamming distance cutoff for sequence re-weighting."""

    reference_sequence_name: str | None = None
    """The name of the reference sequence of MSA present in Dataset."""

    sequence_start: int | None = None
    """The starting position of the reference sequence in the MSA."""

    sequence_end: int | None = None
    """The ending position of the reference sequence in the MSA."""


class MSAManifestSection(MSAMetadataManifestSection):
    """The multiple sequence alignment section of the manifest."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    path: FilePath
    """The path to the multiple sequence alignment file."""

    name: str | None = None
    """The name of the multiple sequence alignment.

    If None, the file stem will be used.
    """

    description: str | None = None
    """The description of the multiple sequence alignment."""

    format: MSAFormat = MSAFormat.FASTA
    """The format of the multiple sequence alignment file."""

    weights_path: FilePath | None = Field(default=None, exclude=True)
    """The weight file for each sequence in the MSA."""

    weights: list[float] | None = None
    """The weights for each sequence in the MSA (for internal manifest)."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the multiple sequence alignment."""

    @field_validator("path", mode="before", check_fields=True)
    @classmethod
    def validate_path(cls, path: Path, info: ValidationInfo) -> Path:
        """Extend the path with the `relative_to_path` from the context."""

        if info.context and info.context.get("relative_to_path"):
            path = info.context["relative_to_path"] / path
        return path

    @field_validator("weights_path", mode="before", check_fields=True)
    @classmethod
    def validate_weights_path(
        cls, weights_path: Path | None, info: ValidationInfo
    ) -> Path | None:
        """Extend the weights_path with the `relative_to_path` from the context."""

        if (
            weights_path is not None
            and info.context
            and info.context.get("relative_to_path")
        ):
            weights_path = info.context["relative_to_path"] / weights_path

        weights_format = weights_path.suffix[1:].lower()
        if weights_format not in MSAWeightFormat:
            raise ValueError(f"Unsupported MSA weight file format: {weights_format}")
        return weights_path

    @model_validator(mode="after")
    def check_weights_and_weights_path(self) -> "MSAManifestSection":
        """Ensure that both weights and weights_path are not provided together."""

        if self.weights and self.weights_path:
            raise ValueError(
                "Only one of weights and weights_path can be provided in the manifest"
                " section."
            )
        return self

    @field_serializer("path", check_fields=True)
    def serialize_path(self, path: Path, info: SerializationInfo) -> str:
        """Serialize the path as a Posix path."""
        if info.context and info.context.get("relative_to_path"):
            path = path.relative_to(info.context["relative_to_path"])
        return path.as_posix()

    @field_serializer("format", check_fields=True)
    def _serialize_str_enum(self, fmt: MSAFormat) -> str:
        """Serialize a StrEnum as a string."""
        return fmt.value

    def __eq__(self, other: Any) -> bool:
        """Custom equality that excludes `weights_path` from comparison.

        `weights_path` is an input-only field used to load weights from a file.
        """

        if not isinstance(other, MSAManifestSection):
            return False

        # Compare all fields except weights_path
        return (
            self.path == other.path
            and self.name == other.name
            and self.description == other.description
            and self.format == other.format
            and self.num_significant == other.num_significant
            and self.bit_score == other.bit_score
            and self.theta == other.theta
            and self.reference_sequence == other.reference_sequence
            and self.sequence_start == other.sequence_start
            and self.sequence_end == other.sequence_end
            and self.weights == other.weights
            and self.metadata == other.metadata
        )


@dataclasses.dataclass
class MSA:
    """Multiple Sequence Alignment (MSA) model."""

    name: str
    """The name of the MSA."""

    value: MultipleSeqAlignment
    """The value of the MSA, typically a file path or binary data."""

    description: str | None = None
    """A brief description of the MSA."""

    num_significant: int | None = None
    """Number of evolutionary couplings that are considered significant."""

    bit_score: float | None = None
    """Bitscore threshold

    It is used to generate the alignment divided by the length of the target protein.
    """

    theta: float | None = None
    """Hamming distance cutoff for sequence re-weighting."""

    reference_sequence_name: str | None = None
    """The name of the reference sequence of MSA present in Dataset."""

    sequence_start: int | None = None
    """The starting position of the reference sequence in the MSA."""

    sequence_end: int | None = None
    """The ending position of the reference sequence in the MSA."""

    weights: list[float] | None = None
    """The weights for each sequence in the MSA."""

    def __eq__(self, item: Any) -> bool:
        """Implements the equality (==) operator for MSA.

        For equality, we only look at the msa value.
        """
        if isinstance(item, MSA):
            return self.value.alignment == item.value.alignment
        return False

    def __repr__(self) -> str:
        """A concise representation of the MSA object."""
        lines = [f"MSA(\n\tname='{self.name}',"]
        if self.description:
            desc = (
                self.description[:60] + "..."
                if len(self.description) > 60
                else self.description
            )
            lines.append(f"\tdescription: {desc},")
        else:
            lines.append("\tdescription: None,")

        lines.append("\tvalue:")
        alignment_lines = str(self.value).splitlines()
        preview = alignment_lines[:3]
        lines.extend([f"\t\t{line}" for line in preview])
        if len(alignment_lines) > 3:
            lines.append("\t\t...")
        lines.append(")")
        return "\n".join(lines)

    @classmethod
    def from_manifest_section(cls, section: MSAManifestSection) -> "MSA":
        """Create an MSA instance from a manifest section.

        Raises :
            NotImplementedError if the file type is not supported.
            ValueError if both weights and weights_path are provided.
        """
        name = section.name or section.path.stem
        value = AlignIO.read(section.path, section.format.value)
        if section.weights_path:
            weights = np.load(section.weights_path).tolist()
        elif section.weights:
            weights = section.weights
        else:
            weights = None
        return MSA(
            name=name,
            value=value,
            description=section.description,
            num_significant=section.num_significant,
            bit_score=section.bit_score,
            theta=section.theta,
            reference_sequence_name=section.reference_sequence_name,
            sequence_start=section.sequence_start,
            sequence_end=section.sequence_end,
            weights=weights,
        )

    def as_manifest_section(self, *, path: Path) -> MSAManifestSection:
        """Create a manifest section from the MSA instance.

        Args:
            path: The path to the MSA file. As created by the dump method.

        Returns:
            MSAManifestSection: The manifest section for the MSA.
        """
        return MSAManifestSection(
            path=path,
            name=self.name,
            description=self.description,
            num_significant=self.num_significant,
            bit_score=self.bit_score,
            theta=self.theta,
            reference_sequence_name=self.reference_sequence_name,
            sequence_start=self.sequence_start,
            sequence_end=self.sequence_end,
            weights=self.weights,
        )

    def dump(
        self, *, path: Path | None = None, fmt: MSAFormat = MSAFormat.FASTA
    ) -> Path:
        """Dump the multiple sequence alignment to a file.

        Biopython is used for writing the MSA to a file, see
        :func:`Bio.AlignIO.write` for details.

        Args:
            path: The directory path to save the MSA file in.
                Defaults to the current working directory.
            fmt: The format to save the MSA in. Defaults to
                MSAFormat.FASTA.

        Raises:
            ValueError: If the format is not supported.

        Returns:
            Path: The path to the saved MSA file.

        Note:
            This dump implementation looses the metadata besides the multiple
            sequence alignment. This metadata should be stored with dumping the
            dataset.
        """
        if fmt not in MSAFormat:
            raise ValueError(f"Format {fmt} is not supported for MSA dumping.")
        path = path or Path.cwd()
        if path.is_dir():
            path /= f"{self.name}.{fmt.value}"
        AlignIO.write(self.value, path, format=fmt.value)
        return path
