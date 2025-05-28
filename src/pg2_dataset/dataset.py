from pathlib import Path
from typing import IO, Self

from pydantic import BaseModel

from pg2_dataset.backends import AssaysDataset, StructureDataset
from pg2_dataset.primitives.meta import DatasetMeta


class Dataset(BaseModel):
    """Container for different types of data.

    We do not store this in toml since may be large and/or difficult to serialize.
    """

    meta: DatasetMeta
    assays: AssaysDataset | None = None
    structure: StructureDataset | None = None

    @classmethod
    def from_zip(cls, zip_file: Path | str) -> None:
        raise NotImplementedError

    @classmethod
    def to_zip(cls, zip_file: Path | str) -> None:
        raise NotImplementedError

    @classmethod
    def from_toml(cls, toml_file: Path | str | IO["str"]) -> Self:
        meta = DatasetMeta.from_toml(toml_file)
        return cls(
            meta=meta,
            assays=AssaysDataset(meta=meta.assays_meta),
        )
