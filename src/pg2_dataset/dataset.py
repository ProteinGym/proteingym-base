from pathlib import Path
from typing import Self

from pydantic import BaseModel, PrivateAttr
from functools import cached_property

from pg2_dataset.backends import AssaysDataset, StructureDataset
from pg2_dataset.primitives.meta import DatasetMeta


class Dataset(BaseModel):
    meta: DatasetMeta
    _assays: AssaysDataset | None = PrivateAttr(default=None)
    _structure: StructureDataset | None = PrivateAttr(default=None)

    @cached_property
    def records(self) -> AssaysDataset:
        if self._assays:
            return self._assays

        elif self.meta.resources and self.meta.resources.records and self.meta.records:
            self._assays = AssaysDataset(
                file_path=self.meta.resources.records, meta=self.meta.records
            )

            return self._assays

        else:
            return None
        
    @cached_property
    def structure(self) -> StructureDataset:
        if self._structure:
            return self._structure

        elif self.meta.resources and self.meta.resources.structure:
            self._structure = StructureDataset(
                file_path=self.meta.resources.structure,
            )

            return self._structure

        else:
            return None

    @classmethod
    def from_zip(cls, zip_file: Path | str) -> None:
        raise NotImplementedError

    @classmethod
    def to_zip(cls, zip_file: Path | str) -> None:
        raise NotImplementedError
    
    @classmethod
    def from_toml(cls, toml_file: Path | str) -> Self:
        meta = DatasetMeta.parse_toml(toml_file)

        return cls(
            toml_file=toml_file,
            meta=meta,
        )
