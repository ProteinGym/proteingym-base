from abc import ABC

from pydantic import BaseModel, computed_field

from pg2_dataset.primitives.setting import DatasetSettings
from pg2_dataset.io.bytes import read_bytes, write_bytes
from pg2_dataset.io.utils import export_toml, zip_from_dir
from pathlib import Path

import tempfile


class Dataset(BaseModel, ABC):
    toml_file: str | None = None
    file_path: str | None = None

    def to_zip(self) -> None:
        raise NotImplementedError

    def from_zip(self) -> None:
        raise NotImplementedError

    @computed_field
    def settings(self) -> DatasetSettings | None:
        if self.toml_file:
            DatasetSettings._toml_file = self.toml_file
            return DatasetSettings()
        else:
            return None

    def to_zip(self, filename) -> None:

        with tempfile.TemporaryDirectory() as tmpdirname:
            # reading artifact file and placing in temp dir
            stream = read_bytes(self.file_path)
            path = Path(tmpdirname)/Path(self.file_path).name
            write_bytes(stream, path)


            # loading settings and detecting which artifact should have its path changed to local
            artifact_key = next(art for art,art_path in self.settings.artifacts if art_path==self.file_path)
            settings = self.settings.dict()
            settings["artifacts"][artifact_key] = Path(self.file_path).name

            path = Path(tmpdirname)/"dataset.toml"
            export_toml(settings, path)

            zip_from_dir(tmpdirname, filename)
