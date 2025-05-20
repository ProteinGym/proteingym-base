from abc import ABC

from pydantic import BaseModel, computed_field

from pg2_dataset.primitives.meta import DatasetSettings


class AbstractDataset(BaseModel, ABC):
    toml_file: str = ""

    def to_zip(self) -> None:
        raise NotImplementedError

    @computed_field
    def meta_data(self) -> DatasetSettings | None:
        if self.toml_file:
            return DatasetSettings.parse_toml(self.toml_file)
        else:
            return None
