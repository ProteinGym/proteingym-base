from typing import Union
from .sequence import SequenceDataFile
from pydantic import TypeAdapter
from .base import DataFile
DataFileUnion = Union[SequenceDataFile]
DataFileAdapter = TypeAdapter(DataFileUnion)

__all__ = [
    "DataFile",
    "DataFileAdapter",
]