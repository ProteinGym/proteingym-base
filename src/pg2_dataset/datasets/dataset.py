import random
import uuid
from typing import Any

from pg2_dataset.primitives.example import Example


class Dataset:
    def __init__(
        self,
        train_seed: int = 0,
        train_size: int | None = None,
        val_seed=0,
        val_size: int | None = None,
        test_size: int | None = None,
        input_keys: list[str] = [],
        label: str | None = None,
    ):
        self.train_seed = train_seed
        self.train_size = train_size

        self.val_seed = val_seed
        self.val_size = val_size
        
        self.test_seed = val_seed
        self.test_size = test_size

        self.input_keys = input_keys
        self.label = label

        self.do_shuffle = True

        self.name = self.__class__.__name__

    @property
    def train(self):
        if not hasattr(self, "_train_"):
            self._train_ = self._shuffle_and_sample(
                "train", self._train, self.train_size, self.train_seed
            )

        return self._train_

    @property
    def dev(self):
        if not hasattr(self, "_val_"):
            self._val_ = self._shuffle_and_sample(
                "val", self._val, self.val_size, self.val_seed
            )

        return self._val_

    @property
    def test(self):
        if not hasattr(self, "_test_"):
            self._test_ = self._shuffle_and_sample(
                "test", self._test, self.test_size, self.test_seed
            )

        return self._test_

    def _shuffle_and_sample(
        self, split: str, data: list[dict[str, Any]], size: int, seed: int = 0
    ):
        data = list(data)

        # Shuffle the data irrespective of the requested size.
        base_rng = random.Random(seed)

        if self.do_shuffle:
            base_rng.shuffle(data)

        data = data[:size]
        output = []

        for example in data:
            example_obj = Example(
                **example, pg2_uuid=str(uuid.uuid4()), pg2_split=split
            )
            if self.input_keys:
                example_obj = example_obj.with_inputs(*self.input_keys)

            if self.label:
                example_obj = example_obj.with_label(self.label)

            output.append(example_obj)

        # TODO: NOTE: Ideally we use these uuids for dedup internally, for internal train/val splits.

        return output
