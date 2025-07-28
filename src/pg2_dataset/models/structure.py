"""The protein structure of the dataset."""

from enum import StrEnum
from pathlib import Path

from Bio.PDB import MMCIFIO, PDBIO, MMCIFParser, PDBParser
from Bio.PDB.binary_cif import BinaryCIFParser
from Bio.PDB.Structure import Structure as BioStructure
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


class StructureFormat(StrEnum):
    """Supported structure file formats."""

    PDB = ".pdb"
    MMCIF = ".cif"
    BINARY_CIF = ".bcif"


class Structure(BaseModel):
    """A protein structure in the dataset."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Allow BioPython structures
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    name: str
    """The name of the protein structure."""

    value: BioStructure
    """The value of the protein structure, typically a file path or binary data."""

    description: str | None = None
    """The description of the protein structure."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Additional metadata for the protein structure."""

    @classmethod
    def from_manifest_section(cls, section: StructureManifestSection) -> "Structure":
        """Create a Structure instance from a manifest section.

        Raises :
            NotImplementedError if the file type is not supported.
        """
        match section.path.suffix.lower():
            case StructureFormat.PDB:
                parser = PDBParser()
            case StructureFormat.MMCIF:
                parser = MMCIFParser()
            case StructureFormat.BINARY_CIF:
                parser = BinaryCIFParser()
            case _:
                raise NotImplementedError(
                    f"Unsupported file type: {section.path.suffix}"
                )
        name = section.name or section.path.stem
        value = parser.get_structure(name, section.path)
        return Structure(
            name=name,
            value=value,
            description=section.description,
            metadata=section.metadata,
        )

    def as_manifest_section(self, *, path: Path) -> StructureManifestSection:
        """Convert the structure to a manifest section.

        Args:
            path (Path): The path to the structure file (as created by
                `method:dump`).

        Returns:
            StructureManifestSection: The manifest section for the structure.
        """
        return StructureManifestSection(
            path=path,
            name=self.name,
            description=self.description,
            metadata=self.metadata,
        )

    def dump(
        self, *, path: Path | None = None, format: StructureFormat = StructureFormat.PDB
    ) -> Path:
        """Dump the structure to a file.

        Biopython is used for writing the structure to a file. The following
        formats are supported:
        - PDB (.pdb)
        - MMCIF (.cif)
        Note that binary CIF files (.bcif) are not supported for writing.

        Args:
            path (Path): The output directory path to dump the structure to. If
                None, the current working directory is used.
            format (_StructureFormat): The format to dump the structure in.

        Raises:
            NotImplementedError if the file type is not supported.
        """
        path = path or Path.cwd()
        structure_path = path / f"{self.name}{format.value}"
        match format:
            case StructureFormat.PDB:
                io = PDBIO()
            case StructureFormat.MMCIF:
                io = MMCIFIO()
            case _:
                raise NotImplementedError(f"Unsupported file type: {format.value}")
        io.set_structure(self.value)
        with structure_path.open("w", encoding="utf-8") as file:
            io.save(file)
        return structure_path
