"""The protein structure of the dataset."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, FilePath, field_serializer


class StructureManifestSection(BaseModel):
    """The protein structure section of the manifest."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    path: FilePath
    """The path to the protein structure file."""

    name: str | None = None
    """The name of the protein structure. If None, the file stem will be used."""

    description: str | None = None
    """The description of the protein structure."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the protein structure."""

    @field_serializer("path")
    def serialize_path(self, path: Path) -> str:
        """Serialize the path as a Posix path."""
        return path.as_posix()


class Structure(BaseModel):
    """A protein structure in the dataset."""

    name: str
    """The name of the protein structure."""

    value: object
    """The value of the protein structure, typically a file path or binary data."""

    description: str | None = None
    """The description of the protein structure."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the protein structure."""
