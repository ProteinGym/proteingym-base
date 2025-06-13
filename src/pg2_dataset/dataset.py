from pathlib import Path
from pydantic import BaseModel
from pg2_dataset.backends import Assays, Structure


class Dataset(BaseModel):
    assays: Assays | None
    structure: Structure | None

    @classmethod
    def from_path(cls, path: Path | str) -> None:
        raise NotImplementedError

    @classmethod
    def persist(cls, path: Path | str) -> None:
        raise NotImplementedError

