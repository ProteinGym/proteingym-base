import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import IO, TYPE_CHECKING, Self

import toml
from loguru import logger
from pydantic import BaseModel

from pg2_dataset.backends import Assays, Structure
from pg2_dataset.primitives.meta import AssaysMeta, StructuresMeta

if TYPE_CHECKING:
    from pg2_dataset.dataset import Dataset, Manifest


class Dataset(BaseModel):
    name: str = ""
    assays: Assays | None = None
    structure: Structure | None = None

    @classmethod
    def from_path(cls, path: Path | str) -> None:
        raise NotImplementedError

    def persist(
        self, path: Path | str, compression: int = zipfile.ZIP_DEFLATED
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = []

            # 1. Write manifest
            manifest_path = os.path.join(temp_dir, "manifest.toml")

            manifest = Manifest(
                name=self.name,
                assays_meta=self.assays.meta,
                structures_meta=self.structure.meta,
            )

            with open(manifest_path, "w") as f:
                toml.dump(manifest.model_dump(), f)

            file_paths.append(manifest_path)

            # 2. Write assays
            if self.assays and not self.assays._internal_data_frame.is_empty():
                assays_path = os.path.join(temp_dir, "assays.csv")
                self.assays._internal_data_frame.write_csv(assays_path)

                file_paths.append(assays_path)

            # 3. Write structures
            if self.structure and self.structure.meta.file_path:
                source = self.structure.meta.file_path
                structure_path = os.path.join(temp_dir, os.path.basename(source))

                if os.path.isfile(source):
                    shutil.copy2(source, structure_path)
                    logger.info(f"Copied file: {source} -> {structure_path}")

                    file_paths.append(structure_path)

                elif os.path.isdir(source):
                    shutil.copytree(source, structure_path)
                    logger.info(f"Copied directory: {source} -> {structure_path}")

                    file_paths.append(structure_path)

                else:
                    logger.error(f"Path does not exist: {source}")

            # 4. Create zip file
            with zipfile.ZipFile(path, "w", compression=compression) as zipf:
                for file_path in file_paths:
                    archive_name = os.path.basename(file_path)

                    zipf.write(file_path, archive_name)
                    logger.info(f"Added: {file_path} -> {archive_name}")

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
            assays=Assays(meta=self.assays_meta) if self.assays_meta else None,
            structure=Structure(meta=self.structures_meta)
            if self.structures_meta
            else None,
        )

        return dataset
