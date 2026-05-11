"""The protein structure of the dataset."""

import dataclasses
from enum import StrEnum
from pathlib import Path
from typing import Any

import biotite.structure.io.pdb as pdb
import biotite.structure.io.pdbx as pdbx
import numpy as np
from biotite.structure import AtomArray
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
    @classmethod
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

    value: AtomArray
    """The value of the protein structure, typically a file path or binary data."""

    description: str | None = None
    """The description of the protein structure."""

    metadata: dict[str, str] = dataclasses.field(default_factory=dict)
    """Additional metadata for the protein structure."""

    def __eq__(self, item: Any) -> bool:
        """Implements the equality (==) operator for Structure.

        For equality, we look at the structure coordinates and annotations.
        """
        if not isinstance(item, Structure):
            return False

        if self.value.array_length() != item.value.array_length():
            return False

        if not np.array_equal(self.value.coord, item.value.coord):
            return False

        if set(self.value.get_annotation_categories()) != set(
            item.value.get_annotation_categories()
        ):
            return False

        for category in self.value.get_annotation_categories():
            if not np.array_equal(
                self.value.get_annotation(category), item.value.get_annotation(category)
            ):
                return False

        return True

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

        Raises:
            NotImplementedError: If the file type is not supported.
        """
        match section.path.suffix.lower():
            case StructureFormat.PDB:
                parser = pdb.PDBFile.read(section.path)
                value = parser.get_structure(model=1)
            case StructureFormat.MMCIF:
                parser = pdbx.CIFFile.read(section.path)
                value = pdbx.get_structure(parser, model=1)
            case StructureFormat.BINARY_CIF:
                parser = pdbx.BinaryCIFFile.read(section.path)
                value = pdbx.get_structure(parser, model=1)
            case _:
                raise NotImplementedError(
                    f"Unsupported file type: {section.path.suffix}"
                )
        name = section.name or section.path.stem
        return Structure(
            name=name,
            value=value,
            description=section.description,
            metadata=section.metadata,
        )

    def as_manifest_section(self, *, path: Path) -> StructureManifestSection:
        """Convert the structure to a manifest section.

        Args:
            path: The path to the structure file (as created by
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

        Biotite is used for writing the structure to a file. The following
        formats are supported:
        - PDB (.pdb)
        - MMCIF (.cif)
        - Binary CIF (.bcif)

        Args:
            path: The output directory path to dump the structure to. If
                None, the current working directory is used.
            fmt: The format to dump the structure in.

        Raises:
            NotImplementedError: if the file type is not supported.
        """
        path = path or Path.cwd()
        structure_path = path / f"{self.name}{fmt.value}"
        match fmt:
            case StructureFormat.PDB:
                file = pdb.PDBFile()
                file.set_structure(self.value)
            case StructureFormat.MMCIF:
                file = pdbx.CIFFile()
                pdbx.set_structure(file, self.value)
            case StructureFormat.BINARY_CIF:
                file = pdbx.BinaryCIFFile()
                pdbx.set_structure(file, self.value)
            case _:
                raise NotImplementedError(f"Unsupported file type: {fmt.value}")

        file.write(structure_path)
        return structure_path
