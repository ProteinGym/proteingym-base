"""The protein structure of the dataset."""

import dataclasses
from enum import StrEnum
from pathlib import Path
from typing import Any

from Bio.PDB import MMCIFIO, PDBIO, MMCIFParser, PDBParser
from Bio.PDB.binary_cif import BinaryCIFParser
from Bio.PDB.Structure import Structure as BioStructure
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


class StructureFormat(StrEnum):
    """Supported structure file formats."""

    PDB = ".pdb"
    """Protein Data Bank format"""

    MMCIF = ".cif"
    """Macromolecular Crystallographic Information File format.

    This is the new default format used by the Protein Data Bank
    """

    BINARY_CIF = ".bcif"
    """Binary encoding of the mmCIF format """


@dataclasses.dataclass
class Structure:
    """A protein structure in the dataset."""

    name: str
    """The name of the protein structure."""

    value: BioStructure
    """The value of the protein structure, typically a file path or binary data."""

    description: str | None = None
    """The description of the protein structure."""

    metadata: dict[str, str] = dataclasses.field(default_factory=dict)
    """Additional metadata for the protein structure."""

    def __eq__(self, item: Any) -> bool:
        """Implements the equality (==) operator for Structure.

        For equality, we only look at the structure value.
        """
        if isinstance(item, Structure):
            return self.value == item.value
        return False

    def __repr__(self) -> str:
        """Return a string representation of the Structure object."""
        lines = [f"Structure(\n\tname='{self.name}',"]
        if self.description:
            desc = (
                self.description[:60] + "..."
                if len(self.description) > 60
                else self.description
            )
            lines.append(f"\tdescription: {desc},")
        else:
            lines.append("\tdescription: None,")
        lines.append(f"\tvalue: Type[{type(self.value).__name__}],")
        if self.metadata:
            lines.append("\tmetadata:")
            for key, value in self.metadata.items():
                if len(value) > 60:
                    value = value[:60] + "..."
                lines.append(f"\t\t{key}: {value},")
        else:
            lines.append("\tmetadata: 0,")
        lines.append(")")
        return "\n".join(lines)

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
        self, *, path: Path | None = None, fmt: StructureFormat = StructureFormat.PDB
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
            fmt (StructureFormat): The format to dump the structure in.

        Raises:
            NotImplementedError if the file type is not supported.
        """
        path = path or Path.cwd()
        structure_path = path / f"{self.name}{fmt.value}"
        match fmt:
            case StructureFormat.PDB:
                io = PDBIO()
            case StructureFormat.MMCIF:
                io = MMCIFIO()
            case _:
                raise NotImplementedError(f"Unsupported file type: {fmt.value}")
        io.set_structure(self.value)
        with structure_path.open("w", encoding="utf-8") as file:
            io.save(file)
        return structure_path
