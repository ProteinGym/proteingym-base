import io
import polars as pl
from pydantic import ConfigDict, computed_field, field_validator, model_validator
from pg2_dataset.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes


class RecordsDataset(Dataset):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    features: list[str]
    targets: list[str]

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
    # @cached_property
    def raw_data_frame(self) -> pl.DataFrame:
        return self._read_data_frame()

    @field_validator("features", "targets", "columns", mode="after")
    @classmethod
    def unique(cls, items: list[str]) -> list[str]:
        return list(set(items))

    @model_validator(mode="after")
    def check_features_and_targets_should_not_overlap(self):
        if bool(set(self.features) & set(self.targets)):
            raise ValueError(f"{self.features} and {self.targets} should not overlap")
        else:
            return self

    @model_validator(mode="after")
    def check_sequence_should_be_in_features(self):
        if self.sequence_feature and self.sequence_feature not in set(self.features):
            raise ValueError(f"sequence {self.sequence_feature} should exist in {self.features}.")
        else:
            return self

    @model_validator(mode="after")
    def check_engineering_round_should_be_in_features(self):
        if self.engineering_round_feature and self.engineering_round_feature not in set(self.features):
            raise ValueError(f"engineering round {self.engineering_round_feature} should exist in {self.features}.")
        else:
            return self

    @model_validator(mode="after")
    def check_features_should_be_in_columns(self):
        if self.columns and not set(self.features).issubset(set(self.columns)):
            raise ValueError(f"features {self.features} should exist in {self.columns}.")
        else:
            return self

    @model_validator(mode="after")
    def check_targets_should_be_in_columns(self):
        if self.columns and not set(self.targets).issubset(set(self.columns)):
            raise ValueError(f"targets {self.targets} should exist in {self.columns}.")
        else:
            return self

    @model_validator(mode="after")
    def check_columns_should_match_schemas(self):
        if self.columns and self.schemas and len(self.columns) != len(self.schemas):
            raise ValueError(f"columns {self.columns} and schemas {self.schemas} should have the same length.")
        else:
            return self

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

        # rename features
        data = self._rename_features(data)
        self.features = [self._rename_feature(feature) for feature in self.features]

        return data
