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
        if values.get("path") and not values.get("dir_type"):
            if not values.get("path").lower().startswith("s3"):
                values["dir_type"] = DirType.LOCAL
        return values

    def get_files(self, file_types: list[str] = None) -> List[DataFile]:
        if file_types is None:
            file_names = self.path.rglob("*.*")
        else:
            file_types = [ft.lower() for ft in file_types]
            file_names = self.path.rglob(f"*.{'|'.join(file_types)}")

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
