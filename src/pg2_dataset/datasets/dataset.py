import random
import uuid
from typing import Any
import pandas as pd

from pg2_dataset.primitives.record import Record


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
            self._dataset_ = self._enrich(self._dataset)

        if not hasattr(self, "_train_"):
            self._train_ = [record:=self._assign("train", _record) for _record in self._dataset_[:self.train_size]]

        if not hasattr(self, "_test_"):
            self._test_ =[record:=self._assign("test", _record) for _record in self._dataset_[self.train_size: self.train_size+self.test_size]]

        return self._dataset_


    @property
    def train(self):
        return self._train_


    @property
    def test(self):
        return self._test_

    def _assign(
        self, split: str, record: Record,
    ):
        record.split = split
        return record

    def _enrich(
        self, data: list[dict[str, Any]],
    ):  
        output = []

        for record in data:
            record_obj = Record(
                **record, uuid=str(uuid.uuid4())
            )
            if self.input_keys:
                record_obj.with_inputs(*self.input_keys)

            if self.label:
                record_obj.with_label(self.label)

            output.append(record_obj)

        # NOTE: we use these uuids for dedup internally, for internal train/test splits.

        return output
