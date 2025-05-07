import uuid
import polars as pl
import pandas as pd
from pydantic import BaseModel, computed_field
from pg2_dataset.primitives.record import Record
from pg2_dataset.primitives.structure import MMcifFile
from pg2_dataset.primitives.setting import DatasetSettings


class Dataset(BaseModel):
    toml_file: str | None = None
    include_records: bool = True
    include_structure: bool = False
    include_msa: bool = False

    @computed_field
    def settings(self) -> DatasetSettings:
        if self.toml_file:
            DatasetSettings._toml_file = self.toml_file
            return DatasetSettings()
        else:
            return None

    @computed_field
    # @cached_property
    def records(self) -> list[Record] | None:
        if self.include_records:
            if not self.raw_data_frame.is_empty():
                return [record for record in self._to_records(self.raw_data_frame)]
            else:
                raise ValueError("Either no raw data frame is provided or raw data frame is empty.")
        else:
            return None

    def data_frame(self) -> pd.DataFrame | None:
        if self.include_records:
            if not self.raw_data_frame.is_empty():
                return self.raw_data_frame.filter(pl.all_horizontal([~pl.col(col).is_null() for col in self.targets])).to_pandas()
        else:
            raise None

    def data_frame_by_target(self, target: str):
        if self.include_records:
            if not self.raw_data_frame.is_empty():
                return self.raw_data_frame.filter(pl.all_horizontal([~pl.col(col).is_null() for col in ["sequence", target]])).to_pandas()
        else:
            raise None

    def _to_records(
        self,
        data: pl.DataFrame,
    ) -> list[Record]:
        records = []

        for row in data.to_dicts():
            row["targets"] = self.targets
            record = Record(**row)

            # add metadata attributes for tracking
            record._uuid = str(uuid.uuid4())

            records.append(record)

        return records

    @computed_field
    # @cached_property
    def structure(self) -> None:
        if self.include_structure:
            if self.settings.artifacts.structure:
                mmcif = MMcifFile()
                return mmcif.from_mmcif(self.settings.artifacts.structure)
            else:
                raise ValueError("No structure file provided in toml file.")

        else:
            return None
