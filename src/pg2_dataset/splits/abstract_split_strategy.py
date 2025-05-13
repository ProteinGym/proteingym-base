import random
from abc import ABC, abstractmethod
from enum import Enum
from math import ceil, floor
from typing import Collection, NamedTuple

import pandas as pd


class TrainTestValid(Enum):
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


class AbstractSplitStrategy(ABC):
    def __init__(
        self,
        train_ratio: float = 0.8,
        valid_ratio: float = 0.2,
        fixed_test_sequences: Collection = None,
        random_seed: int = None,
    ):
        if train_ratio + valid_ratio > 1:
            raise ValueError("Sum of train and validation ratios greater than 1!")
        if fixed_test_sequences and train_ratio + valid_ratio < 1:
            raise ValueError("With given fixed test set, train and valid must sum to 1")
        self.train_ratio = train_ratio
        self.valid_ratio = valid_ratio
        self.test_ratio = 1 - train_ratio - valid_ratio
        self.fixed_test_sequences = fixed_test_sequences or []
        self.random_seed = random_seed

    def n_train_valid_test(self, n: int) -> SplitSizes:
        n_train, n_valid = floor(n * self.train_ratio), ceil(n * self.valid_ratio)
        return SplitSizes(n_train, n_valid, n - n_train - n_valid)

    @abstractmethod
    def create_split_map(self, data: pd.DataFrame, target: str) -> dict[str, str]: ...

    def split(self, data: pd.DataFrame, target: str | None = None) -> dict[str, str]:
        if self.random_seed:
            random.seed(self.random_seed)
        if not target:
            target = next(c for c in data.columns if c != "sequence")
        test = dict.fromkeys(self.fixed_test_sequences, TrainTestValid.test.value)
        return {
            **test,
            **self.create_split_map(
                data.loc[lambda d: ~d.sequence.isin(self.fixed_test_sequences)], target
            ),
        }
