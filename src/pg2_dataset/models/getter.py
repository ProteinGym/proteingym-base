from pathlib import Path
from typing import List
from pydantic import BaseModel
from pg2_dataset.io import DataDir, DataFile
from pg2_dataset.models.constants import DirType
from pg2_dataset.models.manifest import Sources


class DataGetter(BaseModel):
    data_dirs: List[DataDir]

    @classmethod
    def from_sources(cls, data: List[Sources]) -> "DataGetter":
        local_dirs = data.local

        data_dirs = []
        for dir in local_dirs:
            data_dir = DataDir(path=Path(dir), dir_type=DirType.LOCAL)
            data_dirs.append(data_dir)

        return cls(
            data_dirs=data_dirs,
        )

    def get_files(self, file_type: list[str] = None) -> List[DataFile]:
        all_files = []
        for data_dir in self.data_dirs:
            files = data_dir.get_files(file_type=file_type)
            all_files = all_files + files
        return all_files

    def get_data(self, file_type: list[str] = None) -> list:
        files = self.get_files(file_type=file_type)
        data = []
        for file in files:
            content = file.read()
            data.append(content)
        return data
