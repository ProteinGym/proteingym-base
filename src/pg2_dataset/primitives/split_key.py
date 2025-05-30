import hashlib
from collections.abc import Collection
from dataclasses import dataclass
from typing import Self

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