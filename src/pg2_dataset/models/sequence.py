from pathlib import Path
from typing import Annotated

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import BaseModel, BeforeValidator, ConfigDict

from pg2_dataset.models.constants import SequenceAlphabet, SequenceType


def parse_sequence_value(value: str | Seq) -> Seq:
    """Convert a string value to a Seq object."""
    if len(value) < 1:
        raise ValueError("Sequence value must not be empty.")
    if isinstance(value, Seq):
        return value
    return Seq(value)


class Sequence(BaseModel):
    name: str
    value: Annotated[Seq, BeforeValidator(lambda v: parse_sequence_value(v))]
    description: str
    type: SequenceType
    alphabet: SequenceAlphabet
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def dump(self, dir: Path) -> None:
        dir.mkdir(parents=True, exist_ok=True)
        file_path = dir / f"{self.name}.fasta"
        record = SeqRecord(
            seq=self.value, id=self.name, name=self.name, description=self.description
        )
        SeqIO.write(record, file_path, "fasta")
