import tempfile
from pathlib import Path
from typing import Self

from pydantic import BaseModel

from pg2_dataset.backends import RecordsDataset, StructureDataset
from pg2_dataset.io.bytes import read_bytes, write_bytes
from pg2_dataset.io.utils import export_toml, zip_from_dir
from pg2_dataset.primitives.meta import DatasetMeta


class Dataset(BaseModel):
    meta: DatasetMeta
    records: RecordsDataset | None = None
    structure: StructureDataset | None = None

    @classmethod
    def from_zip(cls, zip_file: Path | str) -> None:
        raise NotImplementedError

    @classmethod
    def from_toml(cls, toml_file: Path | str) -> Self:
        meta = DatasetMeta.parse_toml(toml_file)
        return cls(
            meta=meta,
            records=RecordsDataset(file_path=meta.resources.records, meta=meta.records),
        )

    def to_zip(self, filename) -> None:
        with tempfile.TemporaryDirectory() as tmpdirname:
            # reading artifact file and placing in temp dir
            stream = read_bytes(self.file_path)
            path = Path(tmpdirname) / Path(self.file_path).name
            write_bytes(stream, path)

            #  loading settings and detecting which artifact
            # should have its path changed to local
            artifact_key = next(
                art
                for art, art_path in self.dataset_meta.resources
                if art_path == self.file_path
            )
            dataset_meta = self.settings.dict()
            dataset_meta["resources"][artifact_key] = Path(self.file_path).name

            path = Path(tmpdirname) / "dataset.toml"
            export_toml(dataset_meta, path)

            zip_from_dir(tmpdirname, filename)
