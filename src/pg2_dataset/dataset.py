from abc import ABC

from pydantic import BaseModel, computed_field

from pg2_dataset.primitives.setting import DatasetSettings


class Dataset(BaseModel, ABC):
    toml_file: str | None = None
    include_records: bool = False
    include_structure: bool = False
    include_msa: bool = False

    def to_zip(self) -> None:
        raise NotImplementedError

    @computed_field
    def settings(self) -> DatasetSettings | None:
        if self.toml_file:
            DatasetSettings._toml_file = self.toml_file
            return DatasetSettings()
        else:
            return None
