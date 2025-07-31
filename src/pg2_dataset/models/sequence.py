from pathlib import Path
from typing import Annotated

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    field_serializer,
)

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


# Create manifest for sequence, currently supports only local and S3 directories.
# It can be extended to support xrefs.
class SequenceManifestSection(BaseModel):
    """This is the manifest section for Sequences.

    They can be loaded from multiple directories.  This object is used to
    validate the sequence manifest.

    TODO:
        Discuss if this should be part of the manifest or of the dataset.
    """

    sequence_type: str
    sequence_alphabet: str
    path: Path

    @field_serializer("path")
    def serialize_path(self, path: Path) -> str:
        """Serialize the path to a string."""
        return str(path)
