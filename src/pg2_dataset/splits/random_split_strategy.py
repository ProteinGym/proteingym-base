import random
from collections.abc import Collection

import pandas as pd

from pg2_dataset.primitives.meta import SEQUENCE
from pg2_dataset.primitives.split_key import SplitKey
from pg2_dataset.primitives.constants import SEQUENCE
from pg2_dataset.splits.abstract_split_strategy import AbstractSplitStrategy, split_name


class RandomSplitStrategy(AbstractSplitStrategy):
    def create_split_map(
        self,
        data: pd.DataFrame,
        targets: Collection[str],
        round_num: int,
    ) -> dict[SplitKey, str]:
        sequences = list(data[SEQUENCE].unique())
        random.shuffle(sequences)
        sizes = self.n_train_valid_test(len(sequences))
        train, valid, test = (
            sequences[: sizes.n_train],
            sequences[sizes.n_train : sizes.n_train + sizes.n_valid],
            sequences[sizes.n_train + sizes.n_valid :],
        )
        return {
            self.split_key(
                sequence=s,
                round_num=round_num,
                targets=targets,
            ): split_name(s, train, valid, test)
            for s in sequences
        }
