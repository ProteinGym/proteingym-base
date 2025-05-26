import tempfile
from pathlib import Path
from typing import Self

from pydantic import BaseModel, computed_field

from pg2_dataset.backends import RecordsDataset, StructureDataset
from pg2_dataset.io.bytes import read_bytes, write_bytes
from pg2_dataset.io.utils import export_toml, zip_from_dir
from pg2_dataset.primitives.meta import DatasetMeta


class Dataset(BaseModel):
    # FIXME: seems more natural to me to include this here
    # dataset_meta: DatasetMeta
    toml_file: str | None = None  # FIXME: why this property?
    records: RecordsDataset | None = None
    structure: StructureDataset | None = None

    @property
    def structures(self):
        """Direct access to structures dictionary from the StructureDataset
        # -> dataset.structures instead of dataset.structure.structures
        # Although seeing the records implementation we do dataset.records.records
        # Is this really how we want it? Or maybe just naming differently?

        """
        if self.structure is None:
            return {}
        return self.structure.structures

    @classmethod
    def from_zip(cls, zip_file: Path | str) -> None:
        raise NotImplementedError

    @classmethod
    def from_toml(cls, toml_file: Path | str) -> Self:
        meta = DatasetMeta.parse_toml(toml_file)
        # from toml can assume: atleast some form of records
        # from toml cannot assume: atleast some form of struc / msa
        # but this creates if not None lines for each modality

        # structure = None
        # if meta.resources.structure:
        #     structure = StructureDataset(file_path=meta.resources.structure)
        return cls(
            toml_file=toml_file,
            records=RecordsDataset(file_path=meta.resources.records, meta=meta.records),
            structure=StructureDataset(file_path=meta.resources.structure),
        )

    @computed_field
    def dataset_meta(self) -> DatasetMeta | None:
        if self.toml_file:
            return DatasetMeta.parse_toml(self.toml_file)
        else:
            return None

    def to_zip(self, filename) -> None:
        with tempfile.TemporaryDirectory() as tmpdirname:
            # reading artifact file and placing in temp dir
            stream = read_bytes(self.file_path)
            path = Path(tmpdirname) / Path(self.file_path).name
            write_bytes(stream, path)

            #  loading settings and detecting which artifact
            # should have its path changed to local
            artifact_key = next(
                art
                for art, art_path in self.dataset_meta.resources
                if art_path == self.file_path
            )
            dataset_meta = self.settings.dict()
            dataset_meta["resources"][artifact_key] = Path(self.file_path).name

            path = Path(tmpdirname) / "dataset.toml"
            export_toml(dataset_meta, path)

            zip_from_dir(tmpdirname, filename)
