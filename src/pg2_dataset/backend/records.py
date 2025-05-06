import io
import polars as pl
from pg2_dataset.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes


class RecordsDataset(Dataset):
    def __init__(
        self,
        file_path: str,
        features: list[str],
        targets: list[str],
        sequence_feature_name: str,
        engineering_round_feature_name: str | None = None,
        columns: list[str] | None = None,
        schemas: list[pl.datatypes.classes.DataTypeClass] | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.file_path = file_path

        self.features = list(set(features))
        self.targets = list(set(targets))

        self.sequence_feature_name = sequence_feature_name
        self.engineering_round_feature_name = engineering_round_feature_name

        self.columns = columns
        self.schemas = schemas

        # sanity check
        if self.sequence_feature_name not in set(self.features):
            raise ValueError(f"expected sequence feature {self.sequence_feature_name} missing from {self.features}.")

        self._data_frame = self._read_data_frame()

    def _read_data_frame(self) -> pl.DataFrame:
        # load data from file
        data_str = read_bytes(self.file_path).decode("utf-8")

        if self.columns and self.schemas:
            data = pl.read_csv(io.StringIO(data_str), columns=self.columns, schema_overrides=self.schemas)

        else:
            data = pl.read_csv(io.StringIO(data_str))

        # sanity check
        if not set(self.features).issubset(set(data.columns)):
            raise ValueError(f"expected features {self.features} missing from {self.columns}.")

        if not set(self.targets).issubset(set(data.columns)):
            raise ValueError(f"expected targets {self.targets} missing from {self.columns}.")

        # rename columns
        if self.sequence_feature_name:
            data = data.rename({self.sequence_feature_name: "sequence"})

        if self.engineering_round_feature_name:
            data = data.rename({self.engineering_round_feature_name: "engineering_round"})

        return data
