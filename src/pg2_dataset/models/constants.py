from enum import Enum


class SequenceType(str, Enum):
    """This class defines the types of sequences that are supported by PG2 Dataset.
    Any sequence that needs to be added to the dataset should be of one of these types.
    """

    WILD_TYPE = "wild_type"
    STARTING_SEQUENCE = "starting_sequence"
    ENGINEERED_SEQUENCE = "engineered_sequence"


class SequenceAlphabet(str, Enum):
    DNA = "DNA"
    RNA = "RNA"
    AA = "AA"


class DirType(str, Enum):
    LOCAL = "local"


class GenomeDataType(str, Enum):
    SEQUENCE = "sequence"
    STRUCTURE = "structure"
    MSA = "msa"
    ASSAY = "assay"


class SequenceFileType(str, Enum):
    FASTA = "fasta"
