from pathlib import Path
from typing import IO, Self

import toml
from pydantic import BaseModel
from pg2_dataset.dataset import Dataset
from pg2_dataset.backends import Assays, Structure
from pg2_dataset.primitives.meta import AssaysMeta, StructuresMeta


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
            assays=Assays(meta=self.assays_meta) if self.assays_meta else None,
            structure=Structure(meta=self.structures_meta) if self.structures_meta else None
        )
         
        return dataset