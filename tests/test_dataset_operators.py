"""
Module for testing dataset operators.
"""

import pytest
from Bio.Align import MultipleSeqAlignment
from Bio.PDB.Structure import Structure as BioStructure
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from pg2_dataset.assay import Assay
from pg2_dataset.dataset import Dataset
from pg2_dataset.msa import MSA
from pg2_dataset.sequence import Sequence, SequenceAlphabet, SequenceType
from pg2_dataset.structure import Structure


@pytest.fixture
def empty_dataset() -> Dataset:
    """An empty dataset."""
    dataset = Dataset(
        name="empty_dataset",
        description="An empty dataset for testing purposes.",
        assay_conditions=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assay() -> Dataset:
    """A dataset containing a single assay."""
    assay = Assay(name="assay1", records=[("SEQ1", 1.0)])
    dataset = Dataset(
        name="dataset_with_single_assay",
        description="A dataset containing a single assay.",
        assay_conditions=[],
        assays=[assay],
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
        assay_conditions=[],
        assays=[],
        sequences=[sequence],
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
        assay_conditions=[],
        assays=[],
        sequences=[],
        structures=[structure],
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
        assay_conditions=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[msa],
    )
    return dataset


@pytest.fixture
def datasets(
    empty_dataset: Dataset,
    dataset_with_assay: Dataset,
    dataset_with_sequence: Dataset,
    dataset_with_structure: Dataset,
    dataset_with_msa: Dataset,
) -> list[Dataset]:
    """All test datasets."""
    return [
        empty_dataset,
        dataset_with_assay,
        dataset_with_sequence,
        dataset_with_structure,
        dataset_with_msa,
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


ALL_DATASET_NAMES = [
    "empty_dataset",
    "dataset_with_single_assay",
    "dataset_with_single_sequence",
    "dataset_with_single_structure",
    "dataset_with_single_msa",
]


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_dataset_equals_itself(dataset: Dataset) -> None:
    """A dataset should equal itself."""
    assert dataset == dataset


@pytest.mark.parametrize("dataset", ALL_DATASET_NAMES, indirect=True)
def test_dataset_contains_itself(dataset: Dataset) -> None:
    """A dataset should contain itself."""
    assert dataset in dataset
