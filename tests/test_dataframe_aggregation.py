import pytest
from Bio.Seq import Seq

from proteingym.base.assay import Assay, Field
from proteingym.base.dataset import Dataset
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType


@pytest.fixture
def dataset_with_duplicates() -> Dataset:
    """A dataset with duplicate sequence records for testing aggregation."""
    seq1 = Sequence(
        name="seq1",
        value=Seq("ACGT"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )
    seq2 = Sequence(
        name="seq2",
        value=Seq("TGCA"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )

    assay = Assay(
        name="test_assay",
        records=[
            (seq1, 1.0, "A"),
            (seq1, 2.0, "B"),  # Duplicate sequence
            (seq2, 3.0, "A"),
            (seq2, 4.0, "A"),  # Duplicate sequence
        ],
        variables={"condition": "test"},
        columns=["sequence", "numeric_target", "categorical_target"],
    )

    return Dataset(
        name="test_dataset",
        assay_targets=[
            Field(name="numeric_target"),
            Field(name="categorical_target"),
        ],
        assay_variables=[Field(name="condition")],
        assays=[assay],
    )


def test_agg_parameter_parsing(dataset_with_duplicates: Dataset):
    """Test that agg parameter accepts correct types."""
    # callable
    df1 = dataset_with_duplicates.to_df(agg=lambda col, dtype: col.first())
    assert df1.shape[0] > 0

    # dict
    df2 = dataset_with_duplicates.to_df(
        agg={"numeric_target": lambda col, dtype: col.first()}
    )
    assert df2.shape[0] > 0

    # None (default)
    df3 = dataset_with_duplicates.to_df(agg=None)
    assert df3.shape[0] > 0


def test_duplicate_handling_triggers_aggregation(dataset_with_duplicates: Dataset):
    """Test that duplicates are detected and handled.
    Should have fewer rows than original due to aggregation"""

    df = dataset_with_duplicates.to_df()
    assert df.shape[0] == 2
    assert "sequence" in df.columns
    assert "condition" in df.columns
