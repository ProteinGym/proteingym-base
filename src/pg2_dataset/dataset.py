import os
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Self

import toml
from pydantic import BaseModel

from pg2_dataset.backends import Assays, Structure
from pg2_dataset.logger import get_logger
from pg2_dataset.primitives.meta import AssaysMeta, StructuresMeta

logger = get_logger(__name__)

DEFAULT_ASSAYS_FILE = Path("assays.csv")
DEFAULT_STRUCTURE_DIR = Path("structure")
DEFAULT_MANIFEST_FILE = Path("manifest.toml")


class Dataset(BaseModel):
    name: str = ""
    assays: Assays | None = None
    structure: Structure | None = None

    @contextmanager
    def _change_dir(dest_dir: Path | str):
        curr_dir = os.getcwd()
        try:
            os.chdir(dest_dir)
            yield
        finally:
            os.chdir(curr_dir)

    @classmethod
    def from_path(cls, path: Path | str) -> Self:
        try:
            with zipfile.ZipFile(path, "r") as zipf:
                logger.info(f"Files in {path}: {zipf.namelist()}")

                with tempfile.TemporaryDirectory() as temp_dir:
                    with cls._change_dir(temp_dir):
                        zipf.extractall(temp_dir)

                        manifest = Manifest.from_path(DEFAULT_MANIFEST_FILE)

                        if manifest.assays_meta:
                            manifest.assays_meta.file_path = DEFAULT_ASSAYS_FILE

                        if manifest.structures_meta:
                            manifest.structures_meta.file_path = DEFAULT_STRUCTURE_DIR

                        return cls.model_validate(manifest.ingest())

        except FileNotFoundError as exc:
            logger.error(exc)
            raise (exc)

        except zipfile.BadZipFile as exc:
            logger.error(f"Invalid ZIP file: {path}")
            raise (exc)

    def _dump_assays(
        self, path: Path | str
    ) -> tuple[AssaysMeta, Path] | tuple[None, None]:
        """Write assays to a CSV file."""
        path = Path(path)

        if self.assays and self.assays.is_valid:
            self.assays.data_frame.to_csv(path, index=False)

            return AssaysMeta(
                file_path=path.name,
                split_strategy=self.assays.meta.split_strategy,
                assays=self.assays.meta.assays,
            ), path

        else:
            return None, None

    def _dump_structure(
        self, path: Path | str
    ) -> tuple[StructuresMeta, Path] | tuple[None, None]:
        """Write structure to a path."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        if self.structure and self.structure.is_valid:
            self.structure.dump(path)

            return StructuresMeta(file_path=path.name), path
        else:
            return None, None

    def _dump_manifest(
        self, path: Path | str, assays_meta: AssaysMeta, structures_meta: StructuresMeta
    ) -> Path:
        """Write manifest to a TOML file."""
        path = Path(path)

        manifest = Manifest(
            name=self.name,
            assays_meta=assays_meta,
            structures_meta=structures_meta,
        )

        with open(path, "w") as f:
            toml.dump(manifest.model_dump(), f)

        return path

    def persist(
        self, path: Path | str, compression: int = zipfile.ZIP_DEFLATED
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = []
            path = Path(path)
            temp_dir = Path(temp_dir)

            assays_meta, assays_path = self._dump_assays(
                path=temp_dir / DEFAULT_ASSAYS_FILE
            )
            file_paths.append(assays_path)

            structures_meta, structure_path = self._dump_structure(
                path=temp_dir / DEFAULT_STRUCTURE_DIR
            )
            file_paths.append(structure_path)

            manifest_path = self._dump_manifest(
                path=temp_dir / DEFAULT_MANIFEST_FILE,
                assays_meta=assays_meta,
                structures_meta=structures_meta,
            )
            file_paths.append(manifest_path)

            file_paths = [
                file_path for file_path in file_paths if file_path is not None
            ]

            with zipfile.ZipFile(path, "w", compression=compression) as zipf:
                for file_path in file_paths:
                    if file_path.is_file():
                        zipf.write(file_path, file_path.name)
                        logger.info(f"Added: {file_path} -> {path}")

                    elif file_path.is_dir():
                        for root, _, files in os.walk(file_path):
                            for file in files:
                                src_file = Path(root) / file
                                zipf.write(
                                    src_file, DEFAULT_STRUCTURE_DIR / src_file.name
                                )
                                logger.info(f"Added: {src_file} -> {path}")

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
