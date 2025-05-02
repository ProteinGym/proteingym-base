import uuid
import polars as pl
from pg2_dataset.primitives.record import Record


class Dataset:
    def __init__(
        self,
        features: list[str] = [],
        targets: list[str] = [],
        train_size: int | None = None,
        test_size: int | None = None,
    ):
        self.features = features
        self.targets = targets

        self.train_size = train_size
        self.test_size = test_size

        self.name = self.__class__.__name__

    @property
    def data_frame(self):
        if not hasattr(self, "_data_frame_"):
            self._data_frame_ = self._to_records(self._data_frame)

        return self._data_frame_

    @property
    def train(self):
        if not hasattr(self, "_data_frame_"):
            self._data_frame_ = self._to_records(self._data_frame)

        if not hasattr(self, "_train_"):
            self._train_ = [self._assign("train", _record) for _record in self._data_frame_[: self.train_size]]

        return self._train_

    @property
    def test(self):
        if not hasattr(self, "_data_frame_"):
            self._data_frame_ = self._to_records(self._data_frame)

        if not hasattr(self, "_test_"):
            self._test_ = [self._assign("test", _record) for _record in self._data_frame_[self.train_size : self.train_size + self.test_size]]

        return self._test_

    def _assign(
        self,
        split: str,
        record: Record,
    ):
        record.split = split
        return record

    def _to_records(
        self,
        data: pl.DataFrame,
    ):
        records = []

        for record in data.to_dicts():
            record_obj = Record(**record, pg2_uuid=str(uuid.uuid4()))
            if self.features:
                record_obj.with_features(*self.features)

            if self.targets:
                record_obj.with_targets(*self.targets)

            records.append(record_obj)

        return records
