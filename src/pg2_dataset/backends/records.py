import io
import uuid
from functools import cached_property
from typing import Generator, Self

import pandas as pd
import polars as pl
from pydantic import (
    ConfigDict,
    Field,
    PrivateAttr,
    computed_field,
)

from pg2_dataset.backends.abstract_dataset import AbstractDataset
from pg2_dataset.io.bytes import read_bytes
from pg2_dataset.primitives.meta import ENGINEERING_ROUND, SEQUENCE, SPLIT, RecordsMeta
from pg2_dataset.primitives.record import Record
from pg2_dataset.primitives.split_key import SplitKey
from pg2_dataset.splits.abstract_split_strategy import (
    AbstractSplitStrategy,
    TrainTestValid,
)


class RecordsDataset(AbstractDataset):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    meta: RecordsMeta
    split_map: dict[SplitKey, str] = Field(default_factory=dict)

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

    def _get_split(
        self,
        split_name: TrainTestValid,
        target: str = "",
        round_num: int | None = None,
        strategy_name: str = "",
    ) -> pd.DataFrame:
        if not strategy_name:
            # the most recently added split
            strategy_name = list(self.split_map)[-1].strategy_name
        if not target:
            target = self.first_target
        if round_num is None:
            # the most recent round
            round_num = list(self.split_map)[-1].round_num
        sequences = [
            k.sequence
            for k, v in self.split_map.items()
            if v == split_name
            and k.target == target
            and k.round_num == round_num
            and k.strategy_name == strategy_name
        ]

        return self._internal_data_frame.filter(
            pl.col(SEQUENCE).is_in(sequences)
        ).to_pandas()

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

    @property
    def first_target(self) -> str:
        return list(self.meta.assays)[0]

    @property
    def split_cols(self) -> list[str]:
        return [
            ENGINEERING_ROUND,
            SEQUENCE,
            self.first_target,
        ]

    def add_split(
        self,
        split_strategy: AbstractSplitStrategy,
        target: str = "",
        round_num: int = 1,
    ):
        if not target:
            target = self.first_target

        self.split_map.update(split_strategy.split(self.data_frame, target, round_num))

    def _from_csv(self) -> pl.DataFrame:
        data_str = read_bytes(self.file_path).decode("utf-8")

        if self.meta.columns:
            data = pl.read_csv(io.StringIO(data_str), columns=self.meta.columns)
        else:
            data = pl.read_csv(io.StringIO(data_str))

        data = self._rename_columns(data)
        if ENGINEERING_ROUND not in data.columns:
            data = data.with_columns(pl.lit(1).alias(ENGINEERING_ROUND))

        self._internal_columns = data.columns

        if data[self.split_cols].n_unique() != data.height:
            raise ValueError(f"The column `{self.sequence_feature}` should be unique.")

        valid_split_values = [member for member in TrainTestValid]

        if self.meta.split_feature:
            if not data[SPLIT].is_in(valid_split_values).all():
                raise ValueError(
                    f"Split values must be one of: {', '.join(valid_split_values)}"
                )
            else:
                split_index = [ENGINEERING_ROUND, SEQUENCE]
                # FIXME: polars native..?
                dd = data.to_pandas().set_index(split_index)[SPLIT]
                for (round_num, sequence), value in dd.items():
                    self.split_map[
                        SplitKey(
                            round_num=round_num,
                            sequence=sequence,
                            strategy_name="source",
                            target=self.first_target,
                        )
                    ] = value
        return data
