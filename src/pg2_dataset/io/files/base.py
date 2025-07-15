from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, model_validator


def assert_path_instance(v):
    if not isinstance(v, Path):
        v = Path(v)
    return v


class DataFile(BaseModel):
    path: Annotated[Path, AfterValidator(assert_path_instance)]
    file_type: str = None

    @model_validator(mode="before")
    @classmethod
    def infer_file_type(cls, values):
        if "file_type" not in values or values["file_type"] is None:
            path = values.get("path")
            if path:
                ext = Path(path).suffix.lstrip(".").lower()
                values["file_type"] = ext
        return values

    def _exists(self):
        return self.path.exists()

    def read(self):
        raise NotImplementedError()

    def dump(self):
        raise NotImplementedError()
