from typing import Annotated

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import BaseModel, Field

from pg2_dataset.models.constants import SequenceAlphabet, SequenceType
from pg2_dataset.models.getter import DataDir


class Sequence(BaseModel):
    name: str
    value: Annotated[Seq, lambda v: v if isinstance(v, Seq) else Seq(v)]
    description: str = Field(required=True)
    sequence_type: SequenceType = Field(required=True)
    sequence_alphabet: SequenceAlphabet = Field(required=True)

    class Config:
        arbitrary_types_allowed = True

    def dump(self, dir: DataDir) -> None:
        dir.path.mkdir(parents=True, exist_ok=True)
        file_path = dir.path / f"{self.name}.fasta"
        record = SeqRecord(
            seq=self.value, id=self.name, name=self.name, description=self.description
        )
        SeqIO.write(record, file_path, "fasta")
