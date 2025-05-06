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
        sequence_feature: str,
        engineering_round_feature: str | None = None,
        columns: list[str] | None = None,
        schemas: list[pl.datatypes.classes.DataTypeClass] | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.file_path = file_path

        self.features = list(set(features))
        self.targets = list(set(targets))

        self.sequence_feature = sequence_feature
        self.engineering_round_feature = engineering_round_feature

        self.columns = columns
        self.schemas = schemas

        # sanity check
        if self.sequence_feature and self.sequence_feature not in set(self.features):
            raise ValueError(f"expected sequence feature {self.sequence_feature} missing from {self.features}.")

        if self.engineering_round_feature and self.engineering_round_feature not in set(self.features):
            raise ValueError(f"expected engineering round feature {self.engineering_round_feature} missing from {self.features}.")

        self._data_frame = self._read_data_frame()

    def _rename_feature(self, feature: str) -> str:
        match feature:
            case self.sequence_feature:
                return "sequence"

            case self.engineering_round_feature:
                return "engineering_round"

            case _:
                return feature

    def _rename_features(self, data: pl.DataFrame) -> pl.DataFrame:
        if self.sequence_feature:
            data = data.rename({self.sequence_feature: self._rename_feature(self.sequence_feature)})

        if self.engineering_round_feature:
            data = data.rename({self.engineering_round_feature: self._rename_feature(self.engineering_round_feature)})

        return data

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

        # rename features
        self.features = [self._rename_feature(feature) for feature in self.features]

        data = self._rename_features(data)

        return data
