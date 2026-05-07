import dataclasses
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
from evedesign.sequence import Sequences
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
)


class MSAFormat(StrEnum):
    """Enumeration for MSA file formats."""

    A3M = "a3m"
    """MSAs following the a3m format."""


class MSAWeightFormat(StrEnum):
    """Enumeration for MSA weight file formats."""

    NPY = "npy"
    """NumPy binary file format."""


class MSAWeightsManifestSection(BaseModel):
    """The manifest section for MSA weights."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )

    name: str
    """The name of the weights (should match an MSA name)."""

    path: FilePath
    """The path to the weights file."""

    @field_validator("path", mode="before", check_fields=True)
    @classmethod
    def validate_path(cls, path: Path, info: ValidationInfo) -> Path:
        """Extend the path with the `relative_to_path` from the context."""
        if info.context and info.context.get("relative_to_path"):
            path = info.context["relative_to_path"] / path
        weights_format = path.suffix[1:].lower()
        if weights_format not in MSAWeightFormat:
            raise ValueError(f"Unsupported MSA weight file format: {weights_format}")
        return path

    @field_serializer("path", check_fields=True)
    def serialize_path(self, path: Path, info: SerializationInfo) -> str:
        """Serialize the path as a Posix path."""
        if info.context and info.context.get("relative_to_path"):
            path = path.relative_to(info.context["relative_to_path"])
        return path.as_posix()


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

    format: MSAFormat = MSAFormat.A3M
    """The format of the multiple sequence alignment file."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the multiple sequence alignment."""

    @field_validator("path", mode="before", check_fields=True)
    @classmethod
    def validate_path(cls, path: Path, info: ValidationInfo) -> Path:
        """Extend the path with the `relative_to_path` from the context."""

        if info.context and info.context.get("relative_to_path"):
            path = info.context["relative_to_path"] / path
        return path

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


@dataclasses.dataclass
class MSAWeights:
    """MSA weights model."""

    name: str
    """The name of the weights (should match an MSA name)."""

    value: list[np.array]
    """The weight values."""

    @classmethod
    def from_manifest_section(cls, section: MSAWeightsManifestSection) -> "MSAWeights":
        """Create an MSAWeights instance from a manifest section."""
        weights = np.load(section.path).tolist()
        return cls(name=section.name, value=weights)

    def as_manifest_section(self, *, path: Path) -> MSAWeightsManifestSection:
        """Create a manifest section from the MSAWeights instance."""
        return MSAWeightsManifestSection(name=self.name, path=path)

    def dump(self, *, path: Path | None = None) -> Path:
        """Dump the MSA weights to a file."""
        path = path or Path.cwd()
        if path.is_dir():
            path /= f"{self.name}_weights.npy"
        np.save(path, np.array(self.value))
        return path


@dataclasses.dataclass
class MSA:
    """Multiple Sequence Alignment (MSA) model."""

    name: str
    """The name of the MSA."""

    value: Sequences
    """The value of the MSA."""

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
            if len(self.value.seqs) != len(item.value.seqs):
                return False
            return all(
                s1.id_ == s2.id_ and s1.seq == s2.seq
                for s1, s2 in zip(self.value.seqs, item.value.seqs, strict=True)
            )
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
        for seq_obj in self.value.seqs[:3]:
            lines.append(f"\t\t{seq_obj.id_} {seq_obj.seq[:50]}")
        if len(self.value.seqs) > 3:
            lines.append("\t\t...")
        lines.append(")")
        return "\n".join(lines)

    @classmethod
    def from_manifest_section(
        cls,
        section: MSAManifestSection,
        weights_section: MSAWeightsManifestSection | None = None,
    ) -> "MSA":
        """Create an MSA instance from a manifest section.

        Args:
            section: The MSA manifest section.
            weights_section: Optional weights manifest section.

        Raises:
            NotImplementedError if the file type is not supported.
        """
        name = section.name or section.path.stem
        value = Sequences.from_file(section.path, format=section.format.value)
        weights = np.load(weights_section.path).tolist() if weights_section else None
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
        )

    def dump(
        self, *, path: Path | None = None, fmt: MSAFormat = MSAFormat.A3M
    ) -> Path:
        """Dump the multiple sequence alignment to a file.

        Args:
            path: The directory path to save the MSA file in.
                Defaults to the current working directory.
            fmt: The format to save the MSA in. Defaults to
                MSAFormat.A3M.

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
        with open(path, "w") as f:
            for s in self.value.seqs:
                f.write(f">{s.id_}\n{s.seq}\n")
        return path
