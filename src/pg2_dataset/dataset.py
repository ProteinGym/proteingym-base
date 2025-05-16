from pg2_dataset.backends.records import RecordsDataset
from pg2_dataset.backends.structure import StructureDataset


class Dataset(RecordsDataset, StructureDataset):
    pass
