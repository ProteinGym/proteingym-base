from pathlib import Path
from typing import Annotated, List

from pydantic import AfterValidator, BaseModel, model_validator

from pg2_dataset.io.files import DataFile, DataFileAdapter
from pg2_dataset.models.constants import DirType


def exists_non_empty(path: Path) -> str:
    if not path.is_dir():
        raise ValueError(f"Path {path} is not a directory.")
    if not path.exists():
        raise ValueError(f"Path {path} does not exist.")
    if list(path.rglob("*")) == []:
        raise ValueError(f"Path {path} is empty.")
    return path


class DataDir(BaseModel):
    path: Annotated[Path, AfterValidator(exists_non_empty)]
    dir_type: DirType = None
    files: List[DataFile] = []

    @model_validator(mode="before")
    @classmethod
    def infer_dir_type(cls, values):
        if "dir_type" not in values or values["dir_type"] is None:
            path = values.get("path")
            if isinstance(path, str):
                path = Path(path)
            if not path.as_posix().lower().startswith("s3"):
                values["dir_type"] = DirType.LOCAL
            else:
                raise ValueError("Path must be local.")
        return values

    def get_files(self, file_type: list[str] = None) -> List[DataFile]:
        if file_type is None:
            file_names = self.path.rglob("*.*")
        else:
            file_type = [ft.lower() for ft in file_type]
            file_names = self.path.rglob(f"*.{'|'.join(file_type)}")

        all_files = []
        for file in file_names:
            data_file_instance = DataFileAdapter.validate_python(
                {
                    "path": file,
                }
            )
            all_files.append(data_file_instance)
        self.files = all_files
        return self.files
