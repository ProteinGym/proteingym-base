import dataclasses
from enum import StrEnum
from pathlib import Path

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
)


class MSAFormat(StrEnum):
    """Enumeration for MSA file formats."""

    FASTA = "fasta"
    """MSAs following the fasta format, also for a2m files."""


class MSAManifestSection(BaseModel):
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

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the multiple sequence alignment."""

    @field_validator("path", mode="before", check_fields=True)
    def validate_path(cls, path: Path, info: ValidationInfo) -> Path:
        """Optionally, extend the path with the `relative_to_path` from the context."""
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
    def _serialize_str_enum(self, format: MSAFormat) -> str:
        """Serialize a StrEnum as a string."""
        return format.value


@dataclasses.dataclass
class MSA:
    """Multiple Sequence Alignment (MSA) model."""

    name: str
    """The name of the MSA."""

    value: MultipleSeqAlignment
    """The value of the MSA, typically a file path or binary data."""

    description: str | None = None
    """A brief description of the MSA."""

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
        alignment_str = "\n\t\t".join(str(self.value).splitlines()[:3])
        lines.append(f"\t\t{alignment_str},")
        lines.append(")")
        return "\n".join(lines)

    @classmethod
    def from_manifest_section(cls, section: MSAManifestSection) -> "MSA":
        """Create a MSA instance from a manifest section.

        Raises :
            NotImplementedError if the file type is not supported.
        """
        name = section.name or section.path.stem
        value = AlignIO.read(section.path, section.format.value)
        return MSA(name=name, value=value, description=section.description)

    def as_manifest_section(self, *, path: Path) -> MSAManifestSection:
        """Create a manifest section from the MSA instance.

        Args:
            path (Path): The path to the MSA file. As created by the dump method.

        Returns:
            MSAManifestSection: The manifest section for the MSA.
        """
        return MSAManifestSection(
            path=path,
            name=self.name,
            description=self.description,
        )

    def dump(
        self, *, path: Path | None = None, format: MSAFormat = MSAFormat.FASTA
    ) -> Path:
        """Dump the multiple sequence alignment to a file.

        Biopython is used for writing the MSA to a file, see
        :func:`Bio.AlignIO.write` for details.

        Args:
            path (Path | None): The directory path to save the MSA file in.
                Defaults to the current working directory.
            format (MSAFormat): The format to save the MSA in. Defaults to
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
        if format not in MSAFormat:
            raise ValueError(f"Format {format} is not supported for MSA dumping.")
        path = path or Path.cwd()
        if path.is_dir():
            path /= f"{self.name}.{format.value}"
        AlignIO.write(self.value, path, format=format.value)
        return path
