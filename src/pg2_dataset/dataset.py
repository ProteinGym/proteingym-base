from abc import ABC

import polars as pl
from pydantic import BaseModel, Field, computed_field

from pg2_dataset.primitives.dataclasses import SplitKey
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
    splits: dict[SplitKey, str] = Field(default_factory=dict)

    def to_zip(self) -> None:
        raise NotImplementedError

    @computed_field
    def settings(self) -> DatasetSettings | None:
        if self.toml_file:
            DatasetSettings._toml_file = self.toml_file
            return DatasetSettings()
        else:
            return None

    def add_split(self, strategy: type[AbstractSplitStrategy], **kwargs) -> None:
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

        split_strategy = strategy(**kwargs)
        strategy_name = strategy.__name__

        # 'reverse inherit' from records. Cleaner way to do this?
        df = self.data_frame()
        split_map = split_strategy.split(df)

        for record in self.records:
            sequence = record.sequence
            round_num = record.engineering_round

            if sequence in split_map:
                self.splits[SplitKey(round_num, sequence, strategy_name)] = split_map[
                    sequence
                ]

        # Reset property cache if we load an empty split and add to it later
        if hasattr(self, "_train"):
            delattr(self, "_train")
        if hasattr(self, "_valid"):
            delattr(self, "_valid")
        if hasattr(self, "_test"):
            delattr(self, "_test")

    def _get_latest_strategy_name(self) -> str | None:
        """Get the most recent strategy name from available splits."""
        if not self.splits:
            return None
        strategy_names = set(key.strategy_name for key in self.splits.keys())
        if not strategy_names:
            return None
        # userdefined splits > default split
        if len(strategy_names) > 1 and "DefaultSplit" in strategy_names:
            strategy_names.remove("DefaultSplit")
        return list(strategy_names)[-1]

    # Do we move these and import?
    @property
    def train(self) -> "Dataset":
        """Get the training dataset split."""
        strategy_name = self._get_latest_strategy_name()
        if not strategy_name:
            return self._create_empty_subset()
        return self._create_subset_dataset(TrainTestValid.train.value, strategy_name)

    @property
    def valid(self) -> "Dataset":
        """Get the validation dataset split."""
        strategy_name = self._get_latest_strategy_name()
        if not strategy_name:
            return self._create_empty_subset()
        return self._create_subset_dataset(TrainTestValid.valid.value, strategy_name)

    @property
    def test(self) -> "Dataset":
        """Get the test dataset split."""
        strategy_name = self._get_latest_strategy_name()
        if not strategy_name:
            return self._create_empty_subset()
        return self._create_subset_dataset(TrainTestValid.test.value, strategy_name)

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
            empty = self._create_empty_subset()
            return empty, empty, empty

        # Idea is that we can store a DS with particular split, so take most
        # recent from split if no name added
        if strategy_name is None:
            strategy_name = self._get_latest_strategy_name()
            if not strategy_name:
                empty = self._create_empty_subset()
                return empty, empty, empty

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

    def _create_empty_subset(self) -> "Dataset":
        """
        Create an empty subset of the dataset.

        Returns:
            An empty Dataset
        """
        subset = self.model_copy(deep=True)

        if hasattr(subset, "raw_data_frame") and subset.raw_data_frame is not None:
            subset.raw_data_frame = subset.raw_data_frame.filter(pl.lit(False))

        return subset

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
                key.sequence
                for key, split in self.splits.items()
                if key.strategy_name == strategy_name and split == split_type
            ]

            subset.raw_data_frame = subset.raw_data_frame.filter(
                pl.col("sequence").is_in(sequences)
            )

        return subset
