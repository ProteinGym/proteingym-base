from typing import Union

from pydantic import TypeAdapter

from pg2_dataset.io.bytes import exists, read_bytes

from .base import DataFile
from .sequence import SequenceDataFile

DataFileUnion = Union[SequenceDataFile]
DataFileAdapter = TypeAdapter(DataFileUnion)

__all__ = [
    "exists",
    "read_bytes",
    "DataFile",
    "DataFileAdapter",
]
