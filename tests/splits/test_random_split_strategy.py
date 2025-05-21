import numpy as np
import pandas as pd
import pytest

from pg2_dataset.splits.abstract_split_strategy import TrainTestValid
from pg2_dataset.splits.random_split_strategy import RandomSplitStrategy


class TestRandomSplitStrategy:
    @pytest.fixture()
    def fake_dataset(self):
        """Create a fake dataset with sequence and task columns"""
        sequences = [f"seq_{i}" for i in range(200)]
        # repeat sequences to test overlap and uniqueness
        data = pd.DataFrame({"sequence": np.repeat(sequences, 3), "task": "DMS_score"})

        return data

    @pytest.fixture()
    def data_with_split(self, fake_dataset):
        data = fake_dataset
        strategy = RandomSplitStrategy(train_ratio=0.5, valid_ratio=0.3)
        split_map = strategy.split(data, target="task", round_num=0)
        data["split"] = data["sequence"].map(split_map)
        return data

    def test_train_valid_no_overlap(self, data_with_split):
        train_seq = data_with_split.query("split == 'train'").sequence.unique()
        valid_seq = data_with_split.query("split == 'valid'").sequence.unique()
        test_seq = data_with_split.query("split == 'test'").sequence.unique()
        assert len(set(train_seq).intersection(valid_seq)) == 0
        assert len(set(test_seq).intersection(valid_seq)) == 0
        assert len(set(train_seq).intersection(test_seq)) == 0

    def test_fixed_members_in_test_and_nowhere_else(self, fake_dataset):
        data = fake_dataset
        fixed_test = data.sequence.sample(100, random_state=42).unique()
        strategy = RandomSplitStrategy(
            train_ratio=0.5, valid_ratio=0.5, fixed_test_sequences=list(fixed_test)
        )
        split_map = strategy.split(data, target="task", round_num=0)
        for seq in data.sequence.unique():
            if seq in fixed_test:
                assert (
                    split_map[
                        strategy.split_key(
                            sequence=seq,
                            round_num=0,
                            target="task",
                        )
                    ]
                    == TrainTestValid.test.value
                )
            else:
                assert split_map[
                    strategy.split_key(
                        sequence=seq,
                        round_num=0,
                        target="task",
                    )
                ] in {
                    TrainTestValid.valid.value,
                    TrainTestValid.train.value,
                }

    def test_must_sum_to_one_if_fixed_members(self, fake_dataset):
        data = fake_dataset
        fixed_test = data.sequence.sample(100, random_state=42).unique()
        with pytest.raises(ValueError):
            RandomSplitStrategy(
                train_ratio=0.5, valid_ratio=0.2, fixed_test_sequences=list(fixed_test)
            )
