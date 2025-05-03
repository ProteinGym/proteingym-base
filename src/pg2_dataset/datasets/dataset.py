import uuid
import polars as pl
from pydantic import create_model


class Dataset:
    def __init__(
        self,
        features: list[str] = [],
        targets: list[str] = [],
    ):
        if bool(set(features) & set(targets)):
            raise ValueError(f"{features} and {targets} should share the same columns")

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

    def _has_all_targets(self, record: object) -> bool:
        return all([getattr(record, target) for target in self.targets])

    def _has_target(self, record: object, target: str) -> bool:
        return getattr(record, target)

    def _to_records(
        self,
        data: pl.DataFrame,
    ) -> list[object]:
        records = []

        for row in data.to_dicts():
            fields = {key: (type(value), value) for key, value in row.items() if key}

            Record = create_model("Record", **fields)
            record = Record(**row)

            record._features = self.features
            record._targets = self.targets
            record._uuid = str(uuid.uuid4())

            records.append(record)

        return records
