import io
import uuid
from functools import cached_property
from typing import Any, Generator, Self

import pandas as pd
import polars as pl
from loguru import logger
from pydantic import (
    ConfigDict,
    Field,
    PrivateAttr,
    computed_field,
    field_validator,
    model_validator,
)

from pg2_dataset.backends.abstract_dataset import AbstractDataset
from pg2_dataset.io.bytes import read_bytes
from pg2_dataset.primitives.record import Record
from pg2_dataset.splits.abstract_split_strategy import (
    AbstractSplitStrategy,
    TrainTestValid,
)


class RecordsDataset(AbstractDataset):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    records_file_path: str | None = None

    sequence_feature: str | None = None
    engineering_round_feature: str | None = None
    split_feature: str | None = None

    columns: list[str] = Field(default_factory=list)

    split_strategy_kwargs: dict[str, Any] = Field(default_factory=dict)
    split_strategy: AbstractSplitStrategy | None = None

    _strategy_name: str = PrivateAttr()
    _renamed_columns: list[str] = PrivateAttr(default_factory=list)

    @computed_field()
    @cached_property
    def renamed_data_frame(self) -> pl.DataFrame:
        return self._from_csv()

    @computed_field
    @cached_property
    def records(self) -> list[Record]:
        return self._to_records(self.renamed_data_frame)

    @computed_field
    @cached_property
    def data_frame(self) -> pd.DataFrame:
        valid_data_frame = self.renamed_data_frame.filter(
            pl.col("sequence").is_not_null()
        )

        return valid_data_frame.to_pandas()

    @computed_field
    @cached_property
    def train(self) -> pd.DataFrame:
        if self.split_strategy:
            return self.renamed_data_frame.filter(
                pl.col(self._strategy_name) == TrainTestValid.train
            ).to_pandas()

        elif self.split_feature:
            return self.renamed_data_frame.filter(
                pl.col("split") == TrainTestValid.train
            ).to_pandas()

        else:
            logger.warn(
                "There is neither a split strategy nor a split column provided."
            )
            return self.renamed_data_frame.head(0).to_pandas()

    @computed_field
    @cached_property
    def valid(self) -> pd.DataFrame:
        if self.split_strategy:
            return self.renamed_data_frame.filter(
                pl.col(self._strategy_name) == TrainTestValid.valid
            ).to_pandas()

        elif self.split_feature:
            return self.renamed_data_frame.filter(
                pl.col("split") == TrainTestValid.valid
            ).to_pandas()

        else:
            logger.warn(
                "There is neither a split strategy nor a split column provided."
            )
            return self.renamed_data_frame.head(0).to_pandas()

    @computed_field
    @cached_property
    def test(self) -> pd.DataFrame:
        if self.split_strategy:
            return self.renamed_data_frame.filter(
                pl.col(self._strategy_name) == TrainTestValid.test
            ).to_pandas()

        elif self.split_feature:
            return self.renamed_data_frame.filter(
                pl.col("split") == TrainTestValid.test
            ).to_pandas()

        else:
            logger.warn(
                "There is neither a split strategy nor a split column provided."
            )
            return self.renamed_data_frame.head(0).to_pandas()

    def data_frame_by_target(self, target: str) -> pd.DataFrame | None:
        valid_data_frame = self.renamed_data_frame.filter(
            pl.all_horizontal(
                [pl.col(col).is_not_null() for col in ["sequence", target]]
            )
        )

        return valid_data_frame.to_pandas()

    def iter_by_rounds(
        self, max_round: int | None = None
    ) -> Generator[Self, None, None]:
        """
        Generate datasets by engineering rounds.

        Args:
            max_round: Optional maximum round to include.
                If None, includes all rounds.

        Yields:
            Dataset objects filtered to include records from the specified rounds.
        """

        available_rounds = sorted(
            self.renamed_data_frame["engineering_round"].unique().to_list()
        )

        if max_round:
            available_rounds = [r for r in available_rounds if r <= max_round]

        for current_round in available_rounds:
            yield self.renamed_data_frame.filter(
                pl.col("engineering_round") == current_round
            ).to_pandas()

    @field_validator("split_strategy", mode="before")
    def initialise_split_strategy(cls, v, info):
        if isinstance(v, type) and issubclass(v, AbstractSplitStrategy):
            kwargs = info.data.get("split_strategy_kwargs")
            return v(**kwargs)

        return v

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
    def configure_split_feature(self) -> Self:
        if self.split_feature:
            return self

        elif (
            self.settings
            and self.settings.records
            and self.settings.records.split_feature
        ):
            self.split_feature = self.settings.records.split_feature
            return self

        else:
            return self

    @model_validator(mode="after")
    def configure_columns(self) -> Self:
        if self.columns:
            return self

        elif self.settings and self.settings.records and self.settings.records.columns:
            self.columns = self.settings.records.columns
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

    def _to_records(
        self,
        data: pl.DataFrame,
    ) -> list[Record]:
        records = []

        for row in data.to_dicts():
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

            case self.split_feature:
                return "split"

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

        if self.split_feature:
            data = data.rename(
                {self.split_feature: self._rename_column(self.split_feature)}
            )

        return data

    def _from_csv(self) -> pl.DataFrame:
        data_str = read_bytes(self.records_file_path).decode("utf-8")

        if self.columns:
            data = pl.read_csv(io.StringIO(data_str), columns=self.columns)
        else:
            data = pl.read_csv(io.StringIO(data_str))

        if data[self.sequence_feature].n_unique() != data.height:
            raise ValueError(f"The column `{self.sequence_feature}` should be unique.")

        valid_split_values = [member.value for member in TrainTestValid]
        if (
            self.split_feature
            and not data[self.split_feature].is_in(valid_split_values).all()
        ):
            raise ValueError(
                f"Split values must be one of: {', '.join(valid_split_values)}"
            )

        data = self._rename_columns(data)

        if "engineering_round" not in data.columns:
            data = data.with_columns(pl.lit(1).alias("engineering_round"))

        self._renamed_columns = data.columns

        if self.split_strategy:
            self._strategy_name = self.split_strategy.__class__.__name__
            split_map = self.split_strategy.split(data.to_pandas())

            data = data.with_columns(
                pl.col("sequence").replace_strict(split_map).alias(self._strategy_name)
            )

        return data
