import random
import uuid
from typing import Any
import pandas as pd

from pg2_dataset.primitives.example import Example


class Dataset:
    def __init__(
        self,
        input_keys: list[str] = [],
        label: str | None = None,
        train_size: int | None = None,
        test_size: int | None = None,
    ):
        
        self.train_size = train_size        
        self.test_size = test_size

        self.input_keys = input_keys
        self.label = label

        self.name = self.__class__.__name__        
    
    @property
    def dataset(self):
        if not hasattr(self, "_dataset_"):
            self._dataset_ = self._dataset

        return self._dataset_


    @property
    def train(self):
        if not hasattr(self, "_train_"):
            self._train_ = self._enrich(self._train, "train")

        return self._train_


    @property
    def test(self):
        if not hasattr(self, "_test_"):
            self._test_ = self._enrich(self._test, "test")

        return self._test_

    def _enrich(
        self, data: list[dict[str, Any]], split: str | None = None
    ):  
        output = []

        for example in data:
            example_obj = Example(
                **example, pg2_uuid=str(uuid.uuid4()), pg2_split=split
            )
            if self.input_keys:
                example_obj.with_inputs(*self.input_keys)

            if self.label:
                example_obj.with_label(self.label)

            output.append(example_obj)

        # NOTE: we use these uuids for dedup internally, for internal train/test splits.

        return output
