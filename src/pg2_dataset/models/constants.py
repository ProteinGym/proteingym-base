from pydantic import BaseModel, Field
from enum import Enum

class SequenceType(str, Enum):
    WILD_TYPE = "wild_type"
    STARTING_SEQUENCE = "starting_sequence"
    ENGINEERED_SEQUENCE = "engineered_sequence"

class SequenceAlphabet(str, Enum):
    DNA = "DNA"
    RNA = "RNA"
    AA = "AA"

class DirType(str, Enum):
    LOCAL = "local"
    S3 = "s3"

class DataType(str, Enum):
    SEQUENCE = "sequence"
    STRUCTURE = "structure"
    MSA = "msa"
    ASSAY = "assay"

class SequenceFileTypes(str, Enum):
    FASTA = "fasta"
    @classmethod
    def get_all_values(cls):
        return [item.value for item in cls]