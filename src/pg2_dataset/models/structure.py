"""The protein structure of the dataset."""

from pathlib import Path

from Bio.PDB import MMCIFParser, PDBParser
from Bio.PDB.binary_cif import BinaryCIFParser
from Bio.PDB.Structure import Structure
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

    value: Structure
    """The value of the protein structure, typically a file path or binary data."""

    description: str | None = None
    """The description of the protein structure."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the protein structure."""

    @classmethod
    def from_manifest_section(cls, section: StructureManifestSection) -> "Structure":
        """Create a Structure instance from a manifest section."""
        match section.path.suffix.lower():
            case ".pdb":
                parser = PDBParser()
            case ".cif":
                parser = MMCIFParser()
            case ".bcif":
                parser = BinaryCIFParser()
        value = parser.get_structure(section.path.name, section.path)
        return Structure(
            name=section.name or section.path.stem,
            value=value,
            description=section.description,
            metadata=section.metadata,
        )
