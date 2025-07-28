from pathlib import Path

from pydantic import BaseModel

from pg2_dataset.io import DataDir, DataFile


class Sources(BaseModel):
    path: conlist(Path, min_length=1)


class DataGetter(BaseModel):
    """Object to retrieve data from different sources.

    Data can be retrieved from:
    - local paths
    - TODO: crossrefs
    """

    data_dir: DataDir

    @classmethod
    def from_path(cls, path: Path) -> "DataGetter":
        """Create a `DataGetter` instance from a local directory path.

        Args:
            path (Path): The path to the local directory containing data files.

        Returns:
            DataGetter: An instance of `DataGetter`.
        """
        data_dir = DataDir(path=path)
        return cls(data_dir=data_dir)

    def get_data(self, *, file_types: list[str] = None) -> list:
        """Get data from for a specific file type.

        Args:
            file_types (list[str], optional): List of file extensions to filter files.
                Defaults to None, which retrieves all files.

        Returns:
            list: A list of data read from the files.
        """
        files = self.data_dir.get_files(file_types=file_types)
        data = []
        for file in files:
            content = file.read()
            data.append(content)
        return data
