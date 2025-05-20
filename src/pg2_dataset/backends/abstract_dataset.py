from abc import ABC

from pydantic import BaseModel


class AbstractDataset(BaseModel, ABC):
    file_path: str | None = None

    def to_zip(self) -> None:
        raise NotImplementedError

    def from_zip(self) -> None:
        raise NotImplementedError
