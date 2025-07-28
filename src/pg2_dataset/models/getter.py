from pathlib import Path

from pydantic import BaseModel

from pg2_dataset.io import DataDir


class DataGetter(BaseModel):
    """DataGetter is responsible for retrieving data from local directories
    or crossrefs (todo).
    """

    data_dir: DataDir

    @classmethod
    def from_path(cls, data: Path) -> "DataGetter":
        """Create a `DataGetter` instance from a local directory path.

        Args:
            data (Path): The path to the local directory containing data files.

        Returns:
            DataGetter: An instance of `DataGetter`.
        """
        data_dir = DataDir(path=data)
        return cls(
            data_dir=data_dir,
        )

    def get_data(self, file_type: list[str] = None) -> list:
        """Get data from for a specific file type.

        Args:
            file_type (list[str], optional): List of file extensions to filter files.
                Defaults to None, which retrieves all files.
        Returns:
            list: A list of data read from the files.
        """
        files = self.data_dir.get_files(file_type=file_type)
        data = []
        for file in files:
            content = file.read()
            data.append(content)
        return data
