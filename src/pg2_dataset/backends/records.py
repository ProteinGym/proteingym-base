import io
import polars as pl
from functools import cached_property
from pydantic import ConfigDict, computed_field, model_validator
from pg2_dataset.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes


class RecordsDataset(Dataset):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    sequence_feature: str
    engineering_round_feature: str | None = None

    columns: list[str] = []
    schemas: list[pl.datatypes.classes.DataTypeClass] = []

    records_file_path: str | None = None

    @computed_field
    def file_path(self) -> str:
        if self.settings and self.settings.artifacts and self.settings.artifacts.records:
            return self.settings.artifacts.records
        elif self.records_file_path:
            return self.records_file_path
        else:
            raise ValueError("No records file path provided.")

    @computed_field
    @cached_property
    def raw_data_frame(self) -> pl.DataFrame:
        return self._read_data_frame()

    @model_validator(mode="after")
    def check_sequence_should_be_in_columns(self):
        if self.sequence_feature and self.columns and self.sequence_feature not in set(self.columns):
            raise ValueError(f"sequence {self.sequence_feature} should exist in {self.columns}.")
        else:
            return self

    @model_validator(mode="after")
    def check_engineering_round_should_be_in_columns(self):
        if self.engineering_round_feature and self.columns and self.engineering_round_feature not in set(self.columns):
            raise ValueError(f"engineering round {self.engineering_round_feature} should exist in {self.columns}.")
        else:
            return self

    @model_validator(mode="after")
    def check_columns_should_be_unique(self):
        if self.columns and len(list(set(self.columns))) != len(self.columns):
            raise ValueError(f"columns {self.columns} should all have unique column names.")
        else:
            return self

    @model_validator(mode="after")
    def check_columns_should_match_schemas(self):
        if self.columns and self.schemas and len(self.columns) != len(self.schemas):
            raise ValueError(f"columns {self.columns} and schemas {self.schemas} should have the same length.")
        else:
            return self

    def _rename_column(self, feature: str) -> str:
        match feature:
            case self.sequence_feature:
                return "sequence"

            case self.engineering_round_feature:
                return "engineering_round"

            case _:
                return feature

    def _rename_columns(self, data: pl.DataFrame) -> pl.DataFrame:
        if self.sequence_feature:
            data = data.rename({self.sequence_feature: self._rename_column(self.sequence_feature)})

        if self.engineering_round_feature:
            data = data.rename({self.engineering_round_feature: self._rename_column(self.engineering_round_feature)})

        return data

    def _read_data_frame(self) -> pl.DataFrame:
        # load data from file
        data_str = read_bytes(self.file_path).decode("utf-8")

        if self.columns and self.schemas:
            data = pl.read_csv(io.StringIO(data_str), columns=self.columns, schema_overrides=self.schemas)
            self.columns = [self._rename_column(col) for col in self.columns]

        elif self.columns:
            data = pl.read_csv(io.StringIO(data_str), columns=self.columns)
            self.columns = [self._rename_column(col) for col in self.columns]

        else:
            data = pl.read_csv(io.StringIO(data_str))

        # rename columns
        data = self._rename_columns(data)

        # add columns
        if "engineering_round" not in data.columns:
            data = data.with_columns(pl.lit(1).alias("engineering_round"))

        # update columns
        if self.columns:
            self.columns = data.columns

        return data
