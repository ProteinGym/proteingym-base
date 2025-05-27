from abc import ABC

from pydantic import BaseModel


class AbstractDataset(BaseModel, ABC):
    def to_zip(self) -> None:
        raise NotImplementedError

    def from_zip(self) -> None:
        raise NotImplementedError
