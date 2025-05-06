import uuid
import polars as pl
from pg2_dataset.primitives import Record


class Dataset:
    def __init__(
        self,
        features: list[str] = [],
        targets: list[str] = [],
    ):
        if bool(set(features) & set(targets)):
            raise ValueError(f"{features} and {targets} should not share the same columns")

        self.features = list(set(features))
        self.targets = list(set(targets))

        self.name = self.__class__.__name__

    @property
    def data_frame(self):
        if not hasattr(self, "_data_frame_"):
            self._data_frame_ = [record for record in self._to_records(self._data_frame) if self._has_all_targets(record)]

        return self._data_frame_

    def data_frame_by_target(self, target: str):
        if not hasattr(self, f"_data_frame_by_target_{target}_"):
            setattr(
                self,
                f"_data_frame_by_target_{target}_",
                [record for record in self._to_records(self._data_frame) if self._has_target(record, target)],
            )

        return getattr(self, f"_data_frame_by_target_{target}_")

    def _has_all_targets(self, record: Record) -> bool:
        return all([getattr(record, target) for target in self.targets])

    def _has_target(self, record: Record, target: str) -> bool:
        return getattr(record, target)

    def _to_records(
        self,
        data: pl.DataFrame,
    ) -> list[Record]:
        records = []

        for row in data.to_dicts():
            # skip null sequence in the data frame
            if not row["sequence"]:
                continue

            row["targets"] = self.targets
            record = Record(**row)

            # add metadata attributes for tracking
            record._features = self.features
            record._targets = self.targets
            record._uuid = str(uuid.uuid4())

            records.append(record)

        return records
