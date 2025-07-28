from pathlib import Path

from Bio import AlignIO
from Bio.Align import MultipleSeqAlignment
from pydantic import BaseModel, ConfigDict, Field, FilePath, field_serializer


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

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the multiple sequence alignment."""

    @field_serializer("path")
    def serialize_path(self, path: Path) -> str:
        """Serialize the path as a Posix path."""
        return path.as_posix()


class MSA(BaseModel):
    """Multiple Sequence Alignment (MSA) model."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Allow Biopython alignments
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The name of the MSA."""

    value: MultipleSeqAlignment
    """The value of the MSA, typically a file path or binary data."""

    description: str | None = None
    """A brief description of the MSA."""

    @classmethod
    def from_manifest_section(cls, section: MSAManifestSection) -> "MSA":
        """Create a MSA instance from a manifest section.

        Raises :
            NotImplementedError if the file type is not supported.
        """
        name = section.name or section.path.stem
        value = AlignIO.read(section.path, section.path.suffix[1:].lower())
        return MSA(name=name, value=value, description=section.description)

    def dump(self, path: Path) -> None:
        """Dump the multiple sequence alignment to a file.

        Biopython is used for writing the MSA to a file, see
        :func:`Bio.AlignIO.write` for details.

        Args:
            path (Path): The path to the file where the MSA will be saved.

        Raises:
            ValueError: if the file type is not supported.
        """
        AlignIO.write(self.value, path, format=path.suffix[1:].lower())
