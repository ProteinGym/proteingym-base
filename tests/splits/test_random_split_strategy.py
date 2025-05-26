import io

import numpy as np
import pandas as pd
import pytest

from pg2_dataset.backends.records import ENGINEERING_ROUND
from pg2_dataset.splits.abstract_split_strategy import TrainTestValid
from pg2_dataset.splits.random_split_strategy import RandomSplitStrategy


class TestRandomSplitStrategy:
    @pytest.fixture()
    def simple_dataset(self):
        """Create a fake dataset with sequence and task columns"""
        sequences = [f"seq_{i}" for i in range(200)]
        # repeat sequences to test overlap and uniqueness
        data = pd.DataFrame({"sequence": np.repeat(sequences, 3), "task": 0}).assign(
            **{ENGINEERING_ROUND: 1}
        )

        return data

    @pytest.fixture()
    def multi_target_dataset(self):
        csv = """sequence,task1,task2,engineering_round
        a,,0,1
        b,,0,1
        c,,0,1
        d,0,0,1
        e,0,0,1
        f,0,0,1
        g,0,0,1
        h,0,0,1
        i,0,0,1
        """.replace(" ", "")
        return pd.read_csv(io.StringIO(csv))

    @pytest.fixture()
    def data_with_split(self, simple_dataset):
        data = simple_dataset
        strategy = RandomSplitStrategy(train_ratio=0.5, valid_ratio=0.3)
        split_map = strategy.split(data, targets=("task",), round_num=1)
        return strategy.assign_split_map(
            df=data, split_map=split_map, round_num=1, targets=("task",)
        )

    def test_split_for_one_target_assigns_only_to_non_missing(
        self, multi_target_dataset
    ):
        data = multi_target_dataset
        strategy = RandomSplitStrategy(train_ratio=0.5, valid_ratio=0.3)
        split_map = strategy.split(data, targets=("task1",), round_num=1)
        assert len(split_map) == len(data.task1.dropna())
        df = strategy.assign_split_map(
            data, split_map=split_map, round_num=1, targets=("task1",)
        )
        # noinspection PyUnresolvedReferences
        assert (df.split.isna() == df.task1.isna()).all()

    def test_split_for_all_targets_assigns_all(self, multi_target_dataset):
        data = multi_target_dataset
        strategy = RandomSplitStrategy(train_ratio=0.5, valid_ratio=0.3)
        split_map = strategy.split(data, targets=("task1", "task2"), round_num=1)
        assert len(split_map) == len(data)
        df = strategy.assign_split_map(
            data, split_map=split_map, round_num=1, targets=("task1", "task2")
        )
        # noinspection PyUnresolvedReferences
        assert (~df.split.isna()).any()

    def test_train_valid_no_overlap(self, data_with_split):
        train_seq = data_with_split.query("split == 'train'").sequence.unique()
        valid_seq = data_with_split.query("split == 'valid'").sequence.unique()
        test_seq = data_with_split.query("split == 'test'").sequence.unique()
        assert len(set(train_seq).intersection(valid_seq)) == 0
        assert len(set(test_seq).intersection(valid_seq)) == 0
        assert len(set(train_seq).intersection(test_seq)) == 0

    def test_fixed_members_in_test_and_nowhere_else(self, simple_dataset):
        data = simple_dataset
        fixed_test = data.sequence.sample(100, random_state=42).unique()
        strategy = RandomSplitStrategy(
            train_ratio=0.5, valid_ratio=0.5, fixed_test_sequences=list(fixed_test)
        )
        split_map = strategy.split(data, targets=("task",), round_num=1)
        for seq in data.sequence.unique():
            if seq in fixed_test:
                assert (
                    split_map[
                        strategy.split_key(
                            sequence=seq,
                            round_num=1,
                            targets=("task",),
                        )
                    ]
                    == TrainTestValid.test.value
                )
            else:
                assert split_map[
                    strategy.split_key(
                        sequence=seq,
                        round_num=1,
                        targets=("task",),
                    )
                ] in {
                    TrainTestValid.valid.value,
                    TrainTestValid.train.value,
                }

    def test_must_sum_to_one_if_fixed_members(self, simple_dataset):
        data = simple_dataset
        fixed_test = data.sequence.sample(100, random_state=42).unique()
        with pytest.raises(ValueError):
            RandomSplitStrategy(
                train_ratio=0.5, valid_ratio=0.2, fixed_test_sequences=list(fixed_test)
            )
