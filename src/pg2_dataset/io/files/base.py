from typing import Annotated
from pathlib import Path
from pydantic import BaseModel

def assert_path_instance(v):
    if not isinstance(v, Path):
        raise TypeError(f"Expected Path instance, got {type(v)}")
    return v


class DataFile(BaseModel):
    path: Annotated[Path, assert_path_instance]
    file_type: str = None

    def _exists(self) -> bool:
        return self.path.exists() and self.path.is_file()

    def read(self):
        raise NotImplementedError()

    def dump(self):
        raise NotImplementedError()



