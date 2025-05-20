import random

import pandas as pd

from pg2_dataset.primitives.meta import SEQUENCE
from pg2_dataset.splits.abstract_split_strategy import AbstractSplitStrategy, split_name


class RandomSplitStrategy(AbstractSplitStrategy):
    def create_split_map(self, data: pd.DataFrame, *_, **__) -> dict[str, str]:
        sequences = list(data[SEQUENCE].unique())
        random.shuffle(sequences)
        sizes = self.n_train_valid_test(len(sequences))
        train, valid, test = (
            sequences[: sizes.n_train],
            sequences[sizes.n_train : sizes.n_train + sizes.n_valid],
            sequences[sizes.n_train + sizes.n_valid :],
        )
        return {s: split_name(s, train, valid, test) for s in sequences}
