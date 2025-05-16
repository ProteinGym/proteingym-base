import io
import uuid
from typing import Self

import pandas as pd
import polars as pl
from pydantic import ConfigDict, Field, model_validator

from pg2_dataset.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes
from pg2_dataset.primitives.dataclasses import SplitKey
from pg2_dataset.primitives.record import Record
from pg2_dataset.splits.abstract_split_strategy import TrainTestValid


class RecordsDataset(Dataset):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    records_file_path: str | None = None

    sequence_feature: str | None = None
    engineering_round_feature: str | None = None

    # TODO: since we need both, combine them to dict[str, DataTypeClass] instead -
    #   and save some validators?
    columns: list[str] = Field(default_factory=list)
    schemas: list[pl.datatypes.classes.DataTypeClass] = Field(default_factory=list)

    @property
    def raw_data_frame(self) -> pl.DataFrame:
        if hasattr(self, "_cached_data_frame"):
            return self._cached_data_frame
        return self._from_csv()

    @raw_data_frame.setter
    def raw_data_frame(self, value):
        self._cached_data_frame = value

    def update_data_frame(self, data_frame) -> pl.DataFrame:
        self._cached_data_frame = data_frame

    @property
    def records(self) -> list[Record] | None:
        if self.include_records:
            if not hasattr(self, "raw_data_frame"):
                raise ValueError("No implementation of the raw_data_frame attribute")

            return self._to_records(self.raw_data_frame)

        else:
            raise ValueError(
                """Either no implementation of the records dataset,
                or include_records is False
                """
            )

    def data_frame(self) -> pd.DataFrame | None:
        if self.include_records:
            if not hasattr(self, "raw_data_frame"):
                raise ValueError("No implementation of the raw_data_frame attribute")

            valid_data_frame = self.raw_data_frame.filter(
                pl.col("sequence").is_not_null()
            )

            if self.columns:
                return valid_data_frame.select(self.columns).to_pandas()
            else:
                return valid_data_frame.to_pandas()

        else:
            return None

    def data_frame_by_target(self, target: str) -> pd.DataFrame | None:
        if self.include_records:
            if not hasattr(self, "raw_data_frame"):
                raise ValueError("No implementation of the raw_data_frame attribute")

            valid_data_frame = self.raw_data_frame.filter(
                pl.all_horizontal(
                    [pl.col(col).is_not_null() for col in ["sequence", target]]
                )
            )

            if self.columns:
                return valid_data_frame.select(self.columns).to_pandas()
            else:
                return valid_data_frame.to_pandas()

        else:
            return None

    @model_validator(mode="after")
    def configure_records_file_path(self) -> Self:
        if self.records_file_path:
            return self

        elif (
            self.settings
            and self.settings.artifacts
            and self.settings.artifacts.records
        ):
            self.records_file_path = self.settings.artifacts.records
            return self

        else:
            raise ValueError("No records file path provided.")

    @model_validator(mode="after")
    def configure_sequence_feature(self) -> Self:
        if self.sequence_feature:
            return self

        elif (
            self.settings
            and self.settings.records
            and self.settings.records.sequence_feature
        ):
            self.sequence_feature = self.settings.records.sequence_feature
            return self

        else:
            raise ValueError("No sequence feature provided.")

    @model_validator(mode="after")
    def configure_engineering_round_feature(self) -> Self:
        if self.engineering_round_feature:
            return self

        elif (
            self.settings
            and self.settings.records
            and self.settings.records.engineering_round_feature
        ):
            self.engineering_round_feature = (
                self.settings.records.engineering_round_feature
            )
            return self

        else:
            return self

    @model_validator(mode="after")
    def check_sequence_should_be_in_columns(self) -> Self:
        if (
            self.sequence_feature
            and self.columns
            and self.sequence_feature not in set(self.columns)
        ):
            raise ValueError(
                f"sequence {self.sequence_feature} should exist in {self.columns}."
            )
        else:
            return self

    @model_validator(mode="after")
    def check_engineering_round_should_be_in_columns(self) -> Self:
        if (
            self.engineering_round_feature
            and self.columns
            and self.engineering_round_feature not in set(self.columns)
        ):
            raise ValueError(
                f"engineering round {self.engineering_round_feature} should exist in"
                f" {self.columns}."
            )
        else:
            return self

    @model_validator(mode="after")
    def check_columns_should_be_unique(self) -> Self:
        if self.columns and len(list(set(self.columns))) != len(self.columns):
            raise ValueError(f"columns {self.columns} have duplicate column names.")
        else:
            return self

    @model_validator(mode="after")
    def check_columns_should_match_schemas(self) -> Self:
        if self.columns and self.schemas and len(self.columns) != len(self.schemas):
            raise ValueError(
                f"columns {self.columns} and schemas {self.schemas} "
                "should have the same length."
            )
        else:
            return self

    @model_validator(mode="after")
    def check_schemas_should_not_exist_without_columns(self) -> Self:
        if self.schemas and not self.columns:
            raise ValueError(
                f"schemas {self.schemas} should not exist without columns."
            )
        else:
            return self

    @model_validator(mode="after")
    def configure_columns_and_schemas(self) -> Self:
        if self.columns:
            return self

        elif self.settings and self.settings.records and self.settings.records.columns:
            self.columns = self.settings.records.columns
            self.schemas = [eval(schema) for schema in self.settings.records.schemas]
            return self

        else:
            return self

    @model_validator(mode="after")
    def configure_splits(self) -> Self:
        """Load splits from dataframe when dataset is initialized."""

        if self.include_records and hasattr(self, "raw_data_frame"):
            if "split" in self.raw_data_frame.columns:
                self._load_splits_from_dataframe()
        return self

    def _to_records(
        self,
        data: pl.DataFrame,
    ) -> list[Record]:
        records = []

        if self.columns:
            rows = data.select(self.columns).to_dicts()
        else:
            rows = data.to_dicts()

        for row in rows:
            # skip null sequence in the data frame
            if not row["sequence"]:
                continue

            record = Record(**row)

            # add metadata attributes for tracking
            record._uuid = str(uuid.uuid4())

            records.append(record)

        return records

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
            data = data.rename(
                {self.sequence_feature: self._rename_column(self.sequence_feature)}
            )

        if self.engineering_round_feature:
            data = data.rename(
                {
                    self.engineering_round_feature: self._rename_column(
                        self.engineering_round_feature
                    )
                }
            )

        return data

    def _load_splits_from_dataframe(self) -> None:
        """Load splits from the dataframe if a 'split' column exists."""
        if "split" not in self.raw_data_frame.columns:
            return

        strategy_name = "DefaultSplit"
        valid_split_values = {
            TrainTestValid.train,
            TrainTestValid.valid,
            TrainTestValid.test,
        }

        invalid_values = (
            set(self.raw_data_frame.select("split").unique().to_series())
            - valid_split_values
        )
        if invalid_values:
            raise ValueError(
                f"Invalid split values found: {invalid_values}. "
                f"Split values must be one of: {', '.join(valid_split_values)}"
            )

        for row in self.raw_data_frame.select(
            ["sequence", "engineering_round", "split"]
        ).to_dicts():
            self.splits[
                SplitKey(row["engineering_round"], row["sequence"], strategy_name)
            ] = row["split"]

    def _from_csv(self) -> pl.DataFrame:
        data_str = read_bytes(self.records_file_path).decode("utf-8")

        # Store original column names for reading CSV
        original_columns = getattr(
            self, "_original_columns", self.columns.copy() if self.columns else None
        )
        self._original_columns = original_columns  # Save for future calls

        if original_columns and self.schemas:
            data = pl.read_csv(
                io.StringIO(data_str),
                columns=original_columns,
                schema_overrides=self.schemas,
            )
        elif original_columns:
            data = pl.read_csv(io.StringIO(data_str), columns=original_columns)
        else:
            data = pl.read_csv(io.StringIO(data_str))

        data = self._rename_columns(data)

        if "engineering_round" not in data.columns:
            data = data.with_columns(pl.lit(1).alias("engineering_round"))

        if self.columns:
            self.columns = data.columns

        # Update self.columns with renamed columns if not already done
        if self.columns and not getattr(self, "_columns_renamed", False):
            self.columns = [self._rename_column(col) for col in self.columns]
            self._columns_renamed = True
            print(f"These are our self.columns: {self.columns}")
        return data
