from typing import Union

from pydantic import TypeAdapter

from .base import DataFile
from .sequence import SequenceDataFile

DataFileUnion = Union[SequenceDataFile]
DataFileAdapter = TypeAdapter(DataFileUnion)

__all__ = [
    "DataFile",
    "DataFileAdapter",
]
