from dataclasses import dataclass


@dataclass(frozen=True)
class SplitKey:
    round_num: int
    sequence: str
    strategy_name: str
    target: str
