import pytest
from Bio.Align import MultipleSeqAlignment
from Bio.PDB.Structure import Structure as BioStructure
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from proteingym.base.assay import Assay, AssayTarget, AssayVariable
from proteingym.base.dataset import Dataset
from proteingym.base.msa import MSA
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType
from proteingym.base.structure import Structure


@pytest.fixture
def dataset_empty() -> Dataset:
    """An empty dataset."""
    dataset = Dataset(
        name="dataset_empty",
        description="An empty dataset for testing purposes.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assay() -> Dataset:
    """A dataset containing a single assay."""
    sequence1 = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="seq2",
        value=Seq("GFEDCA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assay = Assay(
        name="assay1",
        records=[
            (sequence1, 1.0),
            (sequence2, 2.0),
        ],
        columns=["sequence", "DMS Score"],
    )
    dataset = Dataset(
        name="dataset_with_single_assay",
        description="A dataset containing a single assay.",
        assay_variables=[AssayVariable(name="var1", description="A test variable")],
        assay_targets=[AssayTarget(name="DMS Score", description="The DMS score")],
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assays() -> Dataset:
    """A dataset containing multiple assays."""
    sequence1 = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="seq2",
        value=Seq("GFEDCA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assay1 = Assay(
        name="assay2",
        records=[
            (sequence1, 1.0),
        ],
        columns=["sequence", "DMS Score"],
    )
    assay2 = Assay(
        name="assay3",
        records=[
            (sequence2, 2.0),
        ],
        columns=["sequence", "DMS Score"],
    )
    dataset = Dataset(
        name="dataset_with_multiple_assays",
        description="A dataset containing multiple assays.",
        assay_variables=[AssayVariable(name="var1", description="A test variable")],
        assay_targets=[AssayTarget(name="DMS Score", description="The DMS score")],
        assays=[assay1, assay2],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_sequence() -> Dataset:
    """A dataset containing a single sequence."""
    sequence = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    dataset = Dataset(
        name="dataset_with_single_sequence",
        description="A dataset containing a single sequence.",
        assay_variables=[],
        assays=[],
        sequences=[sequence],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_sequences() -> Dataset:
    """A dataset containing multiple sequences."""
    sequence1 = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="seq2",
        value=Seq("GFEDCA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    dataset = Dataset(
        name="dataset_with_multiple_sequences",
        description="A dataset containing multiple sequences.",
        assay_variables=[],
        assays=[],
        sequences=[sequence1, sequence2],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_structure() -> Dataset:
    """A dataset containing a single structure."""
    structure = Structure(
        name="structure1",
        value=BioStructure("structure1"),
        description="A test structure",
        metadata={"source": "test"},
    )
    dataset = Dataset(
        name="dataset_with_single_structure",
        description="A dataset containing a single structure.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[structure],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_structures() -> Dataset:
    """A dataset containing multiple structures."""
    structure1 = Structure(
        name="structure1",
        value=BioStructure("structure1"),
        description="A test structure",
        metadata={"source": "test"},
    )
    structure2 = Structure(
        name="structure2",
        value=BioStructure("structure2"),
        description="A test structure",
        metadata={"source": "test"},
    )
    dataset = Dataset(
        name="dataset_with_multiple_structures",
        description="A dataset containing multiple structures.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[structure1, structure2],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_msa() -> Dataset:
    """A dataset containing a single MSA."""
    alignment = MultipleSeqAlignment(
        [
            SeqRecord(Seq("ACDEFG"), id="seq1"),
            SeqRecord(Seq("GFEDCA"), id="seq2"),
        ]
    )
    msa = MSA(
        name="msa1",
        value=alignment,
        description="A test MSA",
    )
    dataset = Dataset(
        name="dataset_with_single_msa",
        description="A dataset containing a single MSA.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[msa],
    )
    return dataset


@pytest.fixture
def dataset_with_msas() -> Dataset:
    """A dataset containing multiple MSAs."""
    alignment1 = MultipleSeqAlignment(
        [
            SeqRecord(Seq("ACDEFG"), id="seq1"),
            SeqRecord(Seq("GFEDCA"), id="seq2"),
        ]
    )
    alignment2 = MultipleSeqAlignment(
        [
            SeqRecord(Seq("ADCGFE"), id="seq3"),
            SeqRecord(Seq("FEDCBA"), id="seq4"),
        ]
    )
    msa1 = MSA(name="msa1", value=alignment1, description="A test MSA")
    msa2 = MSA(name="msa2", value=alignment2, description="A test MSA")
    dataset = Dataset(
        name="dataset_with_multiple_msas",
        description="A dataset containing multiple MSAs.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[msa1, msa2],
    )
    return dataset


@pytest.fixture
def dataset_with_everything(
    dataset_with_assays: Dataset,
    dataset_with_sequences: Dataset,
    dataset_with_structures: Dataset,
    dataset_with_msas: Dataset,
) -> Dataset:
    """A dataset containing everything."""
    # Tightly coupled with datasets fixture
    dataset = (
        dataset_with_assays
        | dataset_with_sequences
        | dataset_with_structures
        | dataset_with_msas
    ).model_copy(update={"name": "dataset_with_everything"})
    return dataset


@pytest.fixture
def datasets(
    dataset_empty: Dataset,
    dataset_with_assay: Dataset,
    dataset_with_assays: Dataset,
    dataset_with_sequence: Dataset,
    dataset_with_sequences: Dataset,
    dataset_with_structure: Dataset,
    dataset_with_structures: Dataset,
    dataset_with_msa: Dataset,
    dataset_with_msas: Dataset,
    dataset_with_everything: Dataset,
) -> list[Dataset]:
    """All test datasets."""
    return [
        dataset_empty,
        dataset_with_assay,
        dataset_with_assays,
        dataset_with_sequence,
        dataset_with_sequences,
        dataset_with_structure,
        dataset_with_structures,
        dataset_with_msa,
        dataset_with_msas,
        dataset_with_everything,
    ]


@pytest.fixture
def dataset(request: pytest.FixtureRequest, datasets: list[Dataset]) -> Dataset:
    """A generic dataset for testing.

    Args:
        request (pytest.FixtureRequest): The pytest request object.
            Expecting to contain the dataset name in `request.param`.

    Returns:
        Dataset: The dataset with the requested name.
    """
    param = getattr(request, "param", "UNKNOWN")
    dataset = next((d for d in datasets if d.name == param), None)
    if dataset is None:
        raise ValueError(f"Unknown dataset: {param}")
    return dataset


dataset2 = dataset  # A second fixture for tests using two datasets
