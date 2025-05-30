from dataclasses import dataclass
from typing import Type
from enum import Enum
from pg2_dataset.splits.random_split_strategy import RandomSplitStrategy

class SplitStrategyEnum(str, Enum):
    random = "RandomSplitStrategy"


SPLIT_STRATEGY_MAPPING: dict[SplitStrategyEnum, Type] = {
    SplitStrategyEnum.random: RandomSplitStrategy,
}

@dataclass(frozen=True)
class SplitKey:
    round_num: int
    sequence: str
    strategy_name: str
