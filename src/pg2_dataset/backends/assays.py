import io
import uuid
from collections.abc import Collection
from enum import Enum
from functools import cached_property
from itertools import chain
from typing import Generator, Self, Type

import pandas as pd
import polars as pl
from pydantic import ConfigDict, Field, PrivateAttr, computed_field

from pg2_dataset.backends.base import Base
from pg2_dataset.io import read_bytes
from pg2_dataset.primitives.meta import ENGINEERING_ROUND, SEQUENCE, SPLIT, AssaysMeta
from pg2_dataset.primitives.record import Record
from pg2_dataset.primitives.split_key import SplitKey
from pg2_dataset.primitives.x_and_y import XAndY
from pg2_dataset.splits import (
    AbstractSplitStrategy,
    RandomSplitStrategy,
    TrainTestValid,
    assign_split_map,
)


class SplitStrategyEnum(str, Enum):
    random = "RandomSplitStrategy"


SPLIT_STRATEGY_MAPPING: dict[SplitStrategyEnum, Type] = {
    SplitStrategyEnum.random: RandomSplitStrategy,
}


class Assays(Base):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    meta: AssaysMeta
    split_map: dict[SplitKey, TrainTestValid] = Field(default_factory=dict)

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
        targets: Collection[str] = (),
        round_num: int | None = None,
        strategy_name: str = "",
    ) -> XAndY:
        if not self.split_map:
            raise ValueError("no split available / use add_split")
        if not targets:
            targets = self.targets
        if not strategy_name:
            # the most recently added split
            strategy_name = list(self.split_map)[-1].strategy_name
        if round_num is None:
            # the most recent round
            round_num = list(self.split_map)[-1].round_num
        sequences = (
            assign_split_map(
                self._internal_data_frame.to_pandas(),
                targets=targets,
                round_num=round_num,
                split_map=self.split_map,
                strategy_name=strategy_name,
            )
            .loc[lambda d: d[SPLIT] == split_name][SEQUENCE]
            .values
        )
        df = self._internal_data_frame.filter(
            pl.col(SEQUENCE).is_in(sequences)
        ).to_pandas()
        return XAndY(
            x=df[[SEQUENCE] + self.meta.features_for_targets(targets)],
            y=df[list(targets)],
        )

    def train(self, targets: Collection[str] = ()) -> XAndY:
        return self._get_split(TrainTestValid.train, targets=targets)

    def valid(self, targets: Collection[str] = ()) -> XAndY:
        return self._get_split(TrainTestValid.valid, targets=targets)

    def test(self, targets: Collection[str] = ()) -> XAndY:
        return self._get_split(TrainTestValid.test, targets=targets)

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
        for feature in [
            self.meta.sequence_feature,
            self.meta.engineering_round_feature,
            self.meta.split_feature,
        ]:
            if feature:
                data = data.rename({feature: self._rename_column(feature)})

        return data

    @property
    def features(self) -> list[str]:
        return list(chain.from_iterable(e.features for e in self.meta.assays.values()))

    @property
    def targets(self) -> list[str]:
        return list(self.meta.assays)

    @property
    def unique_cols(self) -> list[str]:
        return [
            ENGINEERING_ROUND,
            SEQUENCE,
        ] + self.features

    def add_split(
        self,
        split_strategy: AbstractSplitStrategy,
        targets: Collection[str] = (),
        round_num: int = 1,
    ):
        self.split_map.update(
            split_strategy.split(self.data_frame, targets or self.targets, round_num)
        )

    def _from_csv(self) -> pl.DataFrame:
        data_str = read_bytes(self.meta.file_path).decode("utf-8")

        if self.meta.columns:
            data = pl.read_csv(io.StringIO(data_str), columns=self.meta.columns)
        else:
            data = pl.read_csv(io.StringIO(data_str))

        data = self._rename_columns(data)
        if ENGINEERING_ROUND not in data.columns:
            data = data.with_columns(pl.lit(1).alias(ENGINEERING_ROUND))

        self._internal_columns = data.columns

        if data[self.unique_cols].n_unique() != data.height:
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
                        SplitKey.make(
                            round_num=round_num,
                            sequence=sequence,
                            strategy_name="source",
                            targets=self.targets,
                        )
                    ] = value
        return data
