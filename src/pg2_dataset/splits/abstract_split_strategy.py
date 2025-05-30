from abc import ABC, abstractmethod
from collections.abc import Collection
from enum import StrEnum
from math import ceil, floor
from typing import NamedTuple

import pandas as pd

from pg2_dataset.primitives.meta import ENGINEERING_ROUND, SEQUENCE, SPLIT
from pg2_dataset.primitives.split_key import SplitKey
from pg2_dataset.primitives.constants import SEQUENCE


class TrainTestValid(StrEnum):
    train = "train"
    valid = "valid"
    test = "test"


def split_name(s: str, train: Collection, valid: Collection, test: Collection):
    if s in train:
        return TrainTestValid.train.value
    elif s in valid:
        return TrainTestValid.valid.value
    elif s in test:
        return TrainTestValid.test.value
    else:
        raise ValueError("Sequence missing from all sets")


class SplitSizes(NamedTuple):
    n_train: int
    n_valid: int
    n_test: int


def assign_split_map(
    df: pd.DataFrame,
    targets: Collection[str],
    round_num: int,
    split_map: dict[SplitKey, TrainTestValid],
    strategy_name: str = "",
) -> pd.DataFrame:
    splits = []
    for _, row in df.iterrows():
        key = SplitKey.make(
            strategy_name=strategy_name,
            sequence=row[SEQUENCE],
            round_num=round_num,
            targets=targets,
        )
        if key in split_map:
            splits.append(split_map[key])
        else:
            splits.append(None)
    return df.assign(**{SPLIT: splits})


class AbstractSplitStrategy(ABC):
    def __init__(
        self,
        train_ratio: float = 0.8,
        valid_ratio: float = 0.2,
        fixed_test_sequences: Collection = None,
    ):
        if train_ratio + valid_ratio > 1:
            raise ValueError("Sum of train and validation ratios greater than 1!")
        if fixed_test_sequences and train_ratio + valid_ratio < 1:
            raise ValueError("With given fixed test set, train and valid must sum to 1")
        self.train_ratio = train_ratio
        self.valid_ratio = valid_ratio
        self.test_ratio = 1 - train_ratio - valid_ratio
        self.fixed_test_sequences = fixed_test_sequences or []

    def n_train_valid_test(self, n: int) -> SplitSizes:
        n_train, n_valid = floor(n * self.train_ratio), ceil(n * self.valid_ratio)
        return SplitSizes(n_train, n_valid, n - n_train - n_valid)

    @abstractmethod
    def create_split_map(
        self, data: pd.DataFrame, targets: Collection[str], round_num: int
    ) -> dict[SplitKey, str]: ...

    def split_key(
        self, sequence: str, targets: Collection[str], round_num: int
    ) -> SplitKey:
        return SplitKey.make(
            sequence=sequence,
            targets=targets,
            round_num=round_num,
            strategy_name=self.__class__.__name__,
        )

    def assign_split_map(
        self,
        df: pd.DataFrame,
        targets: Collection[str],
        round_num: int,
        split_map: dict[SplitKey, TrainTestValid],
    ) -> pd.DataFrame:
        return assign_split_map(
            df, targets, round_num, split_map, strategy_name=self.__class__.__name__
        )

    def split(
        self, data: pd.DataFrame, targets: Collection[str], round_num: int
    ) -> dict[SplitKey, TrainTestValid]:
        test = {
            self.split_key(
                sequence=s, targets=targets, round_num=round_num
            ): TrainTestValid.test
            for s in self.fixed_test_sequences
        }
        data_in_scope = (
            data.loc[lambda d: d[ENGINEERING_ROUND] <= round_num]
            .dropna(subset=targets, how="all")
            .loc[lambda d: ~d[SEQUENCE].isin(self.fixed_test_sequences)]
        )
        return {
            **test,
            **self.create_split_map(
                data_in_scope,
                targets,
                round_num,
            ),
        }
