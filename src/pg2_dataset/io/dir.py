from pathlib import Path
from typing import Annotated, List

from pydantic import AfterValidator, BaseModel

from pg2_dataset.constants import DirType
from pg2_dataset.io.files import DataFile, DataFileAdapter


def exists_ok(path: Path) -> str:
    if not path.is_dir():
        raise ValueError(f"Path {path} is not a directory.")
    if not path.exists():
        raise ValueError(f"Path {path} does not exist.")
    return path


class DataDir(BaseModel):
    path: Annotated[Path, AfterValidator(exists_ok)]
    dir_type: DirType
    files: List[DataFile] = []

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
