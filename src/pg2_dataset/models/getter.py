from pathlib import Path
from typing import Annotated, List

from pydantic import AfterValidator, BaseModel

from pg2_dataset.io import DataDir, DataFile


def assert_non_empty_sources_list(sources: List[str]) -> List[str]:
    """Ensure that the sources list is not empty."""
    if len(sources) == 0:
        raise ValueError("Sources list cannot be empty.")
    return sources


class Sources(BaseModel):
    path: Annotated[
        List[str], AfterValidator(lambda v: assert_non_empty_sources_list(v))
    ]


class DataGetter(BaseModel):
    data_dirs: List[DataDir]

    @classmethod
    def from_sources(cls, data: Sources) -> "DataGetter":
        data_dirs = []
        for dir in data.path:
            data_dir = DataDir(path=Path(dir))
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
