from abc import ABC

from pydantic import BaseModel, computed_field

from pg2_dataset.primitives.setting import DatasetSettings


class AbstractDataset(BaseModel, ABC):
    toml_file: str | None = None

    def to_zip(self) -> None:
        raise NotImplementedError

    @computed_field
    def settings(self) -> DatasetSettings | None:
        if self.toml_file:
            return DatasetSettings(toml_file=self.toml_file)
        else:
            return None
