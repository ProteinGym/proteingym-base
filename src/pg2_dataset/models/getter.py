from pathlib import Path
from typing import Annotated, Dict, List

from pydantic import AfterValidator, BaseModel

from pg2_dataset.io import DataFile, DataFileAdapter
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
    dir_type: DirType
    files: List[DataFile] = []

    @classmethod
    def from_dict(cls, data: Dict) -> "DataDir":
        print(f"Creating DataDir from dict: {data}")
        return cls(
            path=data.get("path", None), dir_type=DirType[data.get("dir_type", None)]
        )

    def get_files(self) -> List[DataFile]:
        file_names = self.path.rglob("*.*")
        all_files = []
        for file in file_names:
            data_file_instance = DataFileAdapter.validate_python(
                {
                    "path": file,
                    "file_type": file.suffix.lstrip(".").lower(),
                }
            )
            all_files.append(data_file_instance)
        self.files = all_files
        return self.files


class DataGetter(BaseModel):
    data_dirs: List[DataDir]

    @classmethod
    def from_sources(cls, data: List[Dict]) -> "DataGetter":
        print(f"Creating DataGetter from sources: {data}")
        dirs = data.get("dirs", [])

        data_dirs = []
        for dir_type, dir_list in dirs.items():
            for dir in dir_list:
                data_dir = DataDir(path=Path(dir), dir_type=dir_type)
                data_dirs.append(data_dir)

        return cls(
            data_dirs=data_dirs,
        )

    def get_files(self) -> List[Path]:
        all_files = []
        for data_dir in self.data_dirs:
            print(f"Getting data from directory: {data_dir.path}")
            files = data_dir.get_files()
            all_files = all_files + files
        return all_files

    def get_data(self) -> list:
        files = self.get_files()
        data = []
        for file in files:
            content = file.read()
            data.append(content)
        return data
