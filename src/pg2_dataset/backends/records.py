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

from pg2_dataset.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes
from pg2_dataset.primitives.record import Record
from pg2_dataset.splits.abstract_split_strategy import (
    AbstractSplitStrategy,
    TrainTestValid,
)


class RecordsDataset(Dataset):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file_path: str = ""
    meta: RecordsMeta

    split_strategy_kwargs: dict[str, Any] = Field(default_factory=dict)
    split_strategy: type[AbstractSplitStrategy] | None = None

    _strategy_name: str = PrivateAttr()
    _internal_columns: list[str] = PrivateAttr(default_factory=list)

    @cached_property
    def _internal_data_frame(self) -> pl.DataFrame:
        return self._from_csv()

    @computed_field
    @cached_property
    def records(self) -> list[Record]:
        return self._to_records(self._internal_data_frame)

    @computed_field
    @cached_property
    def data_frame(self) -> pd.DataFrame:
        valid_data_frame = self._internal_data_frame.filter(
            pl.col(SEQUENCE).is_not_null()
        )

        return valid_data_frame.to_pandas()

    def _get_split(self, split_name: TrainTestValid) -> pd.DataFrame:
        if self.split_strategy:
            return self._internal_data_frame.filter(
                pl.col(self._strategy_name) == split_name
            ).to_pandas()

        elif self.meta.split_feature:
            return self._internal_data_frame.filter(
                pl.col(SPLIT) == split_name
            ).to_pandas()

        else:
            logger.warning(
                "There is neither a split strategy nor a split column provided."
            )
            return self._internal_data_frame.head(0).to_pandas()

    @computed_field
    @cached_property
    def train(self) -> pd.DataFrame:
        return self._get_split(TrainTestValid.train)

    @computed_field
    @cached_property
    def valid(self) -> pd.DataFrame:
        return self._get_split(TrainTestValid.valid)

    @computed_field
    @cached_property
    def test(self) -> pd.DataFrame:
        return self._get_split(TrainTestValid.test)

    def data_frame_by_target(self, target: str) -> pd.DataFrame | None:
        valid_data_frame = self._internal_data_frame.filter(
            pl.all_horizontal([pl.col(col).is_not_null() for col in [SEQUENCE, target]])
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
            self._internal_data_frame[ENGINEERING_ROUND].unique().to_list()
        )

        if max_round:
            available_rounds = [r for r in available_rounds if r <= max_round]

        for current_round in available_rounds:
            yield self._internal_data_frame.filter(
                pl.col(ENGINEERING_ROUND) == current_round
            ).to_pandas()

    @classmethod
    @field_validator("split_strategy", mode="before")
    def initialise_split_strategy(cls, v, info):
        if isinstance(v, type) and issubclass(v, AbstractSplitStrategy):
            kwargs = info.data.get("split_strategy_kwargs")
            return v(**kwargs)

        return v

    @model_validator(mode="after")
    def check_sequence_should_be_in_columns(self) -> Self:
        if (
            self.meta.sequence_feature
            and self.meta.columns
            and self.meta.sequence_feature not in set(self.meta.columns)
        ):
            raise ValueError(
                f"sequence {self.meta.sequence_feature} should exist in "
                f"{self.meta.columns}."
            )
        else:
            return self

    @model_validator(mode="after")
    def check_engineering_round_should_be_in_columns(self) -> Self:
        if (
            self.meta.engineering_round_feature
            and self.meta.columns
            and self.meta.engineering_round_feature not in set(self.meta.columns)
        ):
            raise ValueError(
                f"engineering round {self.engineering_round_feature} should exist in"
                f" {self.columns}."
            )
        else:
            return self

    @model_validator(mode="after")
    def check_columns_should_be_unique(self) -> Self:
        if self.meta.columns and len(list(set(self.meta.columns))) != len(
            self.meta.columns
        ):
            raise ValueError(f"columns {self.columns} have duplicate column names.")
        else:
            return self

    @staticmethod
    def _to_records(data: pl.DataFrame) -> list[Record]:
        records = []

        for row in data.to_dicts():
            # skip null sequence in the data frame
            if not row[SEQUENCE]:
                continue

            record = Record(**row)

            # add metadata attributes for tracking
            record._uuid = str(uuid.uuid4())

            records.append(record)

        return records

    def _rename_column(self, feature: str) -> str:
        match feature:
            case self.meta.sequence_feature:
                return SEQUENCE

            case self.meta.engineering_round_feature:
                return ENGINEERING_ROUND

            case self.meta.split_feature:
                return SPLIT

            case _:
                return feature

    def _rename_columns(self, data: pl.DataFrame) -> pl.DataFrame:
        if self.meta.sequence_feature:
            data = data.rename(
                {
                    self.meta.sequence_feature: self._rename_column(
                        self.meta.sequence_feature
                    )
                }
            )

        if self.meta.engineering_round_feature:
            data = data.rename(
                {
                    self.meta.engineering_round_feature: self._rename_column(
                        self.meta.engineering_round_feature
                    )
                }
            )

        if self.meta.split_feature:
            data = data.rename(
                {self.meta.split_feature: self._rename_column(self.meta.split_feature)}
            )

        return data

    def _from_csv(self) -> pl.DataFrame:
        data_str = read_bytes(self.file_path).decode("utf-8")

        if self.meta.columns:
            data = pl.read_csv(io.StringIO(data_str), columns=self.meta.columns)
        else:
            data = pl.read_csv(io.StringIO(data_str))

        if data[self.meta.sequence_feature].n_unique() != data.height:
            raise ValueError(f"The column `{self.sequence_feature}` should be unique.")

        valid_split_values = [member for member in TrainTestValid]
        if (
            self.meta.split_feature
            and not data[self.meta.split_feature].is_in(valid_split_values).all()
        ):
            raise ValueError(
                f"Split values must be one of: {', '.join(valid_split_values)}"
            )

        data = self._rename_columns(data)

        if ENGINEERING_ROUND not in data.columns:
            data = data.with_columns(pl.lit(1).alias(ENGINEERING_ROUND))

        self._internal_columns = data.columns

        if self.split_strategy:
            self._strategy_name = self.split_strategy.__name__
            split_map = self.split_strategy(**self.split_strategy_kwargs).split(
                data.to_pandas()
            )

            data = data.with_columns(
                pl.col(SEQUENCE).replace_strict(split_map).alias(self._strategy_name)
            )

        return data
