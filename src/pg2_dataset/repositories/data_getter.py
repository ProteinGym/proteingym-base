from pathlib import Path
import glob
import io
from Bio import SeqIO
from pydantic import BaseModel, Field, AfterValidator, computed_field
from typing import Annotated, List, Dict

from pg2_dataset.models.constants import DirType, DataType

def exists_non_empty(path: Path) -> str:
    if not path.is_dir():
        raise ValueError(f"Path {path} is not a directory.")
    if not path.exists():
        raise ValueError(f"Path {path} does not exist.")
    if list(path.rglob("*")) == []:
        raise ValueError(f"Path {path} is empty.")
    return path

class DataFile(BaseModel):
    path: Annotated[Path, AfterValidator(lambda p: p if p.exists() and p.is_file() else ValueError(f"File {p} does not exist or is not a file."))]
    
    @property
    def file_type(self) -> str:
        """Returns the file type based on the file extension."""
        if not self.path.suffix:
            raise ValueError(f"File {self.path} has no extension.")
        return self.path.suffix.lstrip('.').lower()

    def read(self) -> str:
        return SeqIO.read(self.path, self.file_type)


class DataDir(BaseModel):
    path: Annotated[Path, AfterValidator(exists_non_empty)]
    dir_type: DirType
    files: List[DataFile] = []

    @classmethod
    def from_dict(cls, data: Dict) -> 'DataDir':
        print(f"Creating DataDir from dict: {data}")
        return cls(
            path=data.get("path", None),
            dir_type=DirType[data.get("dir_type", None)]
        )

    def get_files(self, file_types: List[str] = None) -> List[Path]:
        if self.files == []:
            if file_types:
                file_names = []
                for f in file_types:
                    file_names.extend(self.path.rglob(f"*.{f}"))
            else:
                file_names = self.path.rglob("*.*")

            all_files = []
            for file in file_names:
                all_files.append(DataFile(path=file))
            self.files = all_files
        return self.files


class DataGetter(BaseModel):
    data_dirs: List[DataDir]

    @classmethod
    def from_sources(cls, data: List[Dict]) -> 'DataGetter':

        print(f"Creating DataGetter from sources: {data}")
        dirs, xrefs = data.get('dirs', []), data.get('xrefs', [])

        data_dirs = []
        for dir_type, dir_list in dirs.items():
            for dir in dir_list:
                data_dir = DataDir(path = Path(dir), dir_type = dir_type)
                data_dirs.append(data_dir)
        
        return cls(
            data_dirs=data_dirs,
        )

    def get_files(self, file_types: List[str] = None) -> List[Path]:
        all_files = []
        for data_dir in self.data_dirs:
            print(f"Getting data from directory: {data_dir.path}")
            files = data_dir.get_files(file_types)
            all_files = all_files + files
        return all_files

    def get_data(self, file_types: List[str] = None) -> str:
        files = self.get_files(file_types)
        data = []
        for file in files:
            content = file.read()
        data.append(content)
        return data