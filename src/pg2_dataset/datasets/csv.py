import io
import random
import polars as pl
from pg2_dataset.datasets.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes


class CSVDataset(Dataset):
    def __init__(
        self,
        file_path: str,
        features: list[str],
        targets: list[str],
        columns: list[str] | None = None,
        schemas: list[pl.datatypes.classes.DataTypeClass] | None = None,
        seed: int = 0,
        train_size: int = 0,
        test_size: int = 0,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.file_path = file_path

        self.features = features
        self.targets = targets

        self.columns = columns
        self.schemas = schemas

        self.seed = seed

        self.train_size = train_size
        self.test_size = test_size

        if bool(set(features) & set(targets)):
            raise ValueError(f"{features} should not be part of {targets}")

        # 1. load data
        data = self._load_data()

        # 2. shuffle data
        random.seed(seed)

        groups = [df for _, df in data.group_by(features)]
        random.shuffle(groups)

        # 3. set data frame
        self._data_frame = pl.concat(groups)

    def _load_data(self) -> pl.DataFrame:
        data_str = read_bytes(self.file_path).decode("utf-8")

        if self.columns and self.schemas:
            data = pl.read_csv(io.StringIO(data_str), columns=self.columns, schema_overrides=self.schemas)

        else:
            data = pl.read_csv(io.StringIO(data_str))

        if not set(self.features).issubset(set(data.columns)):
            raise ValueError(f"expected features {self.features} missing from {self.columns}.")

        if not set(self.targets).issubset(set(data.columns)):
            raise ValueError(f"expected targets {self.targets} missing from {self.columns}.")

        return data
