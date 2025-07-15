import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import IO, Self

import toml
from pydantic import BaseModel, Field

from pg2_dataset.backends import MSA, Assays, Structure
from pg2_dataset.primitives.meta import AssaysMeta, MSAMeta, StructuresMeta

logger = logging.getLogger(__name__)

_DEFAULT_ASSAYS_FILE = Path("assays.csv")
_DEFAULT_STRUCTURE_DIR = Path("structure")
_DEFAULT_MANIFEST_FILE = Path("manifest.toml")


class Dataset(BaseModel):
    name: str = ""
    assays: Assays | None = None
    structure: Structure | None = None
    msa: MSA | None = None

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """Create dataset from a zip file path.

        Extracts the contents of a zip file to the current directory and creates
        the dataset by reading the manifest file and ingesting its contents.

        Args:
            path: Path to the zip file to extract and process.

        Returns:
            Self: Dataset created from the manifest found in the extracted zip.
        """
        with zipfile.ZipFile(path, "r") as zipf:
            logger.info(f"Files in {path}: {zipf.namelist()}")

            zipf.extractall()

            manifest = Manifest.from_path(_DEFAULT_MANIFEST_FILE)

            return manifest.ingest()

    def _dump_assays(self, path: Path) -> None:
        """Write assays to a CSV file."""
        if self.assays:
            self.assays.data_frame.to_csv(path, index=False)

    def _dump_structure(self, path: Path) -> None:
        """Write structure to a path."""
        path.mkdir(parents=True, exist_ok=True)

        if self.structure:
            self.structure.dump(path)

    def _dump_manifest(self, path: Path) -> None:
        """Write manifest to a TOML file."""

        if self.assays:
            assays_meta = AssaysMeta(
                file_path=str(path.parent / _DEFAULT_ASSAYS_FILE),
                split_strategy=self.assays.meta.split_strategy,
                assays=self.assays.meta.assays,
            )

            assays_meta.file_path = str(_DEFAULT_ASSAYS_FILE)

        else:
            assays_meta = None

        if self.structure:
            structures_meta = StructuresMeta(
                file_path=str(path.parent / _DEFAULT_STRUCTURE_DIR)
            )

            structures_meta.file_path = str(_DEFAULT_STRUCTURE_DIR)

        else:
            structures_meta = None

        manifest = Manifest(
            name=self.name,
            assays_meta=assays_meta,
            structures_meta=structures_meta,
        )

        with path.open("w") as f:
            toml.dump(manifest.model_dump(), f)

    def _zip_all(self, from_dir: Path, path: Path, compression) -> None:
        with zipfile.ZipFile(path, "w", compression=compression) as zipf:
            file_paths = list(from_dir.iterdir())

            for file_path in file_paths:
                if file_path.is_file():
                    zipf.write(file_path, file_path.name)
                    logger.debug(f"Added: {file_path} -> {path}")

                elif file_path.is_dir():
                    for root, _, files in os.walk(file_path):
                        for file in files:
                            src_file = Path(root) / file
                            zipf.write(src_file, _DEFAULT_STRUCTURE_DIR / src_file.name)
                            logger.debug(f"Added: {src_file} -> {path}")

    def persist(self, path: Path, compression: int = zipfile.ZIP_DEFLATED) -> None:
        """Persist the dataset to a compressed archive at the specified path.

        This method serializes internal dataset components: assays, structure, manifest,
        into a temporary directory and compresses them into a single ZIP archive.

        Args:
            path: The target file path where the ZIP archive will be saved.
            compression: Compression method to use when creating the ZIP archive.

        Returns:
            None
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)

            self._dump_assays(temp_dir / _DEFAULT_ASSAYS_FILE)
            self._dump_structure(temp_dir / _DEFAULT_STRUCTURE_DIR)
            self._dump_manifest(temp_dir / _DEFAULT_MANIFEST_FILE)

            self._zip_all(from_dir=temp_dir, path=path, compression=compression)

            logger.info(f"Dataset persisted to: {path}")


class Manifest(BaseModel):
    """Dataset manifest representing a dataset's metadata and resources.

    A programmatic representation of a dataset's manifest used for validation
    and loading data. The fields have Python built-in data types, the Protein
    Gym data types are constructed while loading the dataset.
    """
    version: str = "1.0"
    """Version of the manifest data model."""

    name: str
    """Name of the dataset."""

    description: str
    """Description of the dataset."""

    assay_conditions: dict[str, dict[str, str]] = Field(default_factory=dict)
    """Conditions for assays in the dataset."""
    
    sequences: list[dict[str, str]] = Field(default_factory=list)
    """List of sequences in the dataset."""

    structures: list[dict[str, str]] = Field(default_factory=list)
    """List of structures in the dataset."""

    msas: list[dict[str, str]] = Field(default_factory=list)
    """List of multiple sequence alignments in the dataset."""

    assays: list[dict[str, str]] = Field(default_factory=list)
    """List of assays in the dataset."""

    @classmethod
    def from_path(cls, path: Path | IO["str"]) -> 'Manifest':
        """Create a Manifest instance from a TOML file or string."""
        return cls(**toml.load(path))

    def ingest(self) -> Dataset:
        """TODO: Move this to the Dataset.from_manifest method."""
        if self.assays_meta and self.assays_meta.file_path:
            assays = Assays(meta=self.assays_meta)
        else:
            assays = None

        if self.structures_meta and self.structures_meta.file_path:
            structure = Structure(meta=self.structures_meta)
        else:
            structure = None

        if self.msa_meta and self.msa_meta.file_path:
            msa = MSA(meta=self.msa_meta)
        else:
            msa = None

        dataset = Dataset(
            name=self.name,
            assays=assays,
            structure=structure,
            msa=msa,
        )

        return dataset
