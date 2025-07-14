from typing import Literal

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

from pg2_dataset.io.files.base import DataFile


class SequenceDataFile(DataFile):
    file_type: Literal["fasta", "fastq"]

    def read(self) -> SeqRecord:
        self._exists()
        return SeqIO.read(self.path, self.file_type)

    def dump(self, record: SeqRecord) -> None:
        SeqIO.write(record, self.path, self.file_type)
