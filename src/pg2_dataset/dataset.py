import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import IO, Self

import toml
from pydantic import BaseModel

from pg2_dataset.backends import Assays, Structure
from pg2_dataset.primitives.meta import AssaysMeta, StructuresMeta

logger = logging.getLogger(__name__)

DEFAULT_ASSAYS_FILE = Path("assays.csv")
DEFAULT_STRUCTURE_DIR = Path("structure")
DEFAULT_MANIFEST_FILE = Path("manifest.toml")


class Dataset(BaseModel):
    name: str = ""
    assays: Assays | None = None
    structure: Structure | None = None

    @classmethod
    def from_path(cls, path: Path) -> Self:
        try:
            with zipfile.ZipFile(path, "r") as zipf:
                logger.info(f"Files in {path}: {zipf.namelist()}")

                zipf.extractall()

                manifest = Manifest.from_path(DEFAULT_MANIFEST_FILE)

                return manifest.ingest()

        except FileNotFoundError as exc:
            logger.error(exc)
            raise (exc)

        except zipfile.BadZipFile as exc:
            logger.error(f"Invalid ZIP file: {path}")
            raise (exc)

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
        manifest = Manifest(
            name=self.name,
            assays_meta=AssaysMeta(
                file_path=str(path.parent / DEFAULT_ASSAYS_FILE),
                split_strategy=self.assays.meta.split_strategy,
                assays=self.assays.meta.assays,
            )
            if self.assays
            else None,
            structures_meta=StructuresMeta(
                file_path=str(path.parent / DEFAULT_STRUCTURE_DIR)
            )
            if self.structure
            else None,
        )

        if self.assays:
            manifest.assays_meta.file_path = str(DEFAULT_ASSAYS_FILE)

        if self.structure:
            manifest.structures_meta.file_path = str(DEFAULT_STRUCTURE_DIR)

        with open(path, "w") as f:
            toml.dump(manifest.model_dump(), f)

    def _zip_all(self, from_dir: Path, path: Path, compression) -> None:
        with zipfile.ZipFile(path, "w", compression=compression) as zipf:
            file_paths = list(from_dir.iterdir())

            for file_path in file_paths:
                if file_path.is_file():
                    zipf.write(file_path, file_path.name)
                    logger.info(f"Added: {file_path} -> {path}")

                elif file_path.is_dir():
                    for root, _, files in os.walk(file_path):
                        for file in files:
                            src_file = Path(root) / file
                            zipf.write(src_file, DEFAULT_STRUCTURE_DIR / src_file.name)
                            logger.info(f"Added: {src_file} -> {path}")

    def persist(self, path: Path, compression: int = zipfile.ZIP_DEFLATED) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)

            self._dump_assays(path=temp_dir / DEFAULT_ASSAYS_FILE)
            self._dump_structure(path=temp_dir / DEFAULT_STRUCTURE_DIR)
            self._dump_manifest(path=temp_dir / DEFAULT_MANIFEST_FILE)

            self._zip_all(from_dir=temp_dir, path=path, compression=compression)

            logger.info(f"Dataset persisted to: {path}")


class Manifest(BaseModel):
    name: str = ""
    description: str = ""
    doi: str = ""
    source: str = ""
    xref: str = ""
    assays_meta: AssaysMeta | None = None
    structures_meta: StructuresMeta | None = None

    @classmethod
    def from_path(cls, path: Path | str | IO["str"]) -> Self:
        if isinstance(path, str):
            path = Path(path)
        return cls.model_validate(toml.load(path))

    def ingest(self) -> Dataset:
        dataset = Dataset(
            name=self.name,
            assays=Assays(meta=self.assays_meta)
            if self.assays_meta and self.assays_meta.file_path
            else None,
            structure=Structure(meta=self.structures_meta)
            if self.structures_meta and self.structures_meta.file_path
            else None,
        )

        return dataset
