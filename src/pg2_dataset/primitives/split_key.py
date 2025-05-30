import hashlib
from collections.abc import Collection
from dataclasses import dataclass
from typing import Self, Type
from enum import Enum
from pg2_dataset.splits.random_split_strategy import RandomSplitStrategy

@dataclass(frozen=True)
class SplitKey:
    round_num: int
    sequence_hash: str
    strategy_name: str
    targets: str

    @classmethod
    def make(
        cls,
        round_num: int,
        sequence: str,
        strategy_name: str,
        targets: Collection[str],
    ) -> Self:
        return SplitKey(
            round_num=round_num,
            sequence_hash=hashlib.sha1(sequence.encode("ascii")).hexdigest(),
            strategy_name=strategy_name,
            targets="-".join(sorted(targets)),
        )
    
class SplitStrategyEnum(str, Enum):
    random = "RandomSplitStrategy"


SPLIT_STRATEGY_MAPPING: dict[SplitStrategyEnum, Type] = {
    SplitStrategyEnum.random: RandomSplitStrategy,
}