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
    def assays(self) -> AssaysDataset:
        if self._assays:
            return self._assays

        elif self.meta.assays_meta:
            self._assays = AssaysDataset(meta=self.meta.assays_meta)

            return self._assays

        else:
            return None
        
    @cached_property
    def structure(self) -> StructureDataset:
        if self._structure:
            return self._structure

        elif self.meta.structures_meta:
            self._structure = StructureDataset(meta=self.meta.structures_meta),

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
        meta = DatasetMeta.from_toml(toml_file)

        return cls(
            meta=meta,
        )
