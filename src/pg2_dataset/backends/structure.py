from functools import cached_property
from pydantic import computed_field, model_validator
from typing_extensions import Self
from pg2_dataset.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes


class StructureDataset(Dataset):
    structure_file_path: str | None = None

    @computed_field
    @cached_property
    def raw_lines(self) -> list[str]:
        return self._from_cif()

    @model_validator(mode="after")
    def configure_structure_file_path(self) -> Self:
        if self.structure_file_path:
            return self

        elif self.settings and self.settings.artifacts and self.settings.artifacts.structure:
            self.structure_file_path = self.settings.artifacts.structure
            return self

        else:
            raise ValueError("No structure file path provided.")

    def _from_cif(self) -> list[str]:
        data_str = read_bytes(self.structure_file_path).decode("utf-8")
        lines = [line.strip() for line in data_str.splitlines() if line.strip()]

        return lines
