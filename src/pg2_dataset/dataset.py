from abc import ABC
from typing import Type

import polars as pl
from pydantic import BaseModel, computed_field

from pg2_dataset.primitives.setting import DatasetSettings
from pg2_dataset.splits.abstract_split_strategy import (
    AbstractSplitStrategy,
    TrainTestValid,
)


class Dataset(BaseModel, ABC):
    toml_file: str | None = None
    include_records: bool = False
    include_structure: bool = False
    include_msa: bool = False
    splits: dict[tuple[int, str, str], str] = {}

    def to_zip(self) -> None:
        raise NotImplementedError

    @computed_field
    def settings(self) -> DatasetSettings | None:
        if self.toml_file:
            DatasetSettings._toml_file = self.toml_file
            return DatasetSettings()
        else:
            return None

    def add_split(self, strategy: Type[AbstractSplitStrategy], **kwargs) -> None:
        """
        Add split information to the dataset using the specified strategy.

        Args:
            strategy: A class that implements AbstractSplitStrategy
            **kwargs: Arguments to pass to the strategy constructor

        Returns:
            None
        """
        if not self.include_records:
            raise ValueError("Cannot add split to dataset without records")

        if not hasattr(self, "raw_data_frame"):
            raise ValueError("No implementation of the raw_data_frame attribute")

        split_strategy = strategy(**kwargs)
        strategy_name = strategy.__name__

        # 'reverse inherit' from records. Cleaner way to do this?
        df = self.data_frame()
        split_map = split_strategy.split(df)

        for record in self.records:
            sequence = record.sequence
            round_num = record.engineering_round

            if sequence in split_map:
                self.splits[(round_num, sequence, strategy_name)] = split_map[sequence]

    def split(
        self, strategy_name: str | None = None
    ) -> tuple["Dataset", "Dataset", "Dataset"]:
        """
        Split the dataset into train, validation, and test datasets based on
        the specified strategy.

        Args:
            strategy_name: Name of the strategy to use for splitting. If None,
            uses the most recent strategy.

        Returns:
            Tuple of (train_dataset, validation_dataset, test_dataset)
        """
        if not self.include_records:
            raise ValueError("Cannot split dataset without records")

        if not self.splits:
            raise ValueError("No splits available. Call add_split() first.")

        # Idea is that we can store a DS with particular split, so take most
        # recent from split if no name added
        if strategy_name is None:
            strategy_names = set(key[2] for key in self.splits.keys())
            if not strategy_names:
                raise ValueError("No split strategies found")
            strategy_name = list(strategy_names)[-1]

        train_dataset = self._create_subset_dataset(
            TrainTestValid.train.value, strategy_name
        )
        valid_dataset = self._create_subset_dataset(
            TrainTestValid.valid.value, strategy_name
        )
        test_dataset = self._create_subset_dataset(
            TrainTestValid.test.value, strategy_name
        )

        return train_dataset, valid_dataset, test_dataset

    def _create_subset_dataset(self, split_type: str, strategy_name: str) -> "Dataset":
        """
        Create a subset of the dataset based on the split type and strategy.

        Args:
            split_type: One of 'train', 'valid', 'test'
            strategy_name: Name of the strategy to use

        Returns:
            A new Dataset containing only the records for the specified split
        """
        subset = self.model_copy(deep=True)

        if hasattr(subset, "raw_data_frame") and subset.raw_data_frame is not None:
            sequences = [
                seq
                for (round_num, seq, strat), split in self.splits.items()
                if strat == strategy_name and split == split_type
            ]

            subset.raw_data_frame = subset.raw_data_frame.filter(
                pl.col("sequence").is_in(sequences)
            )

        return subset
