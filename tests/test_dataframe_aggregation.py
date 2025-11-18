import warnings

import polars as pl
import polars.testing
import pytest
from Bio.Seq import Seq

from proteingym.base.assay import Assay, AssayTarget, AssayVariable
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
            AssayTarget(name="numeric_target"),
            AssayTarget(name="categorical_target"),
        ],
        assay_variables=[AssayVariable(name="condition")],
        assays=[assay],
    )


def test_default_aggregation_with_duplicates(dataset_with_duplicates: Dataset) -> None:
    """Test default aggregation behavior with duplicate records."""
    # Catch warnings to test warning behaviour of aggregation
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        df = dataset_with_duplicates.to_df()

        assert len(w) >= 1
        assert "duplicate" in str(w[0].message).lower()

    # Should have 2 rows (one per unique sequence)
    assert df.shape[0] == 2

    # Numeric should be aggregated by mean, categorical by first
    expected_df = pl.DataFrame({
        "sequence": ["ACGT", "TGCA"],
        "condition": ["test", "test"],
        "numeric_target": [1.5, 3.5],  # Mean of [1.0, 2.0] and [3.0, 4.0]
        "categorical_target": ["A", "A"],  # First values
    })

    pl.testing.assert_frame_equal(
        df, expected_df, check_dtypes=False, check_column_order=False
    )


def test_custom_aggregation_function(dataset_with_duplicates: Dataset) -> None:
    """Test custom aggregation function."""
    def max_last_agg(col, dtype):
        if dtype.is_numeric():
            return col.max()
        else:
            return col.last()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        df = dataset_with_duplicates.to_df(aggregation_fn=max_last_agg)

        assert len(w) >= 1

    expected_df = pl.DataFrame({
        "sequence": ["ACGT", "TGCA"],
        "condition": ["test", "test"],
        "numeric_target": [2.0, 4.0],  # Max values
        "categorical_target": ["B", "A"],  # Last values
    })

    pl.testing.assert_frame_equal(
        df, expected_df, check_dtypes=False, check_column_order=False
    )


def test_per_target_custom_aggregation(dataset_with_duplicates: Dataset) -> None:
    """Test per-target custom aggregation."""
    custom_agg = {
        "numeric_target": lambda col, dtype: col.min(),
        "categorical_target": lambda col, dtype: col.last(),
    }

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        df = dataset_with_duplicates.to_df(custom_aggregation=custom_agg)

        assert len(w) >= 1

    expected_df = pl.DataFrame({
        "sequence": ["ACGT", "TGCA"],
        "condition": ["test", "test"],
        "numeric_target": [1.0, 3.0],  # Min values
        "categorical_target": ["B", "A"],  # Last values
    })

    pl.testing.assert_frame_equal(
        df, expected_df, check_dtypes=False, check_column_order=False
    )


def test_aggregation_error_handling(dataset_with_duplicates: Dataset) -> None:
    """Test error handling in aggregation functions."""
    def broken_agg(col, dtype):
        if dtype.is_numeric():
            return col.invalid_method()  # This will fail
        else:
            return col.first()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        df = dataset_with_duplicates.to_df(aggregation_fn=broken_agg)

        # Should warn about aggregation failure and fallback
        warning_messages = [str(warning.message) for warning in w]
        assert any("failed" in msg.lower() for msg in warning_messages)

    # Should fallback to first() for all columns
    expected_df = pl.DataFrame({
        "sequence": ["ACGT", "TGCA"],
        "condition": ["test", "test"],
        "numeric_target": [1.0, 3.0],  # First values (fallback)
        "categorical_target": ["A", "A"],  # First values
    })

    pl.testing.assert_frame_equal(
        df, expected_df, check_dtypes=False, check_column_order=False
    )


def test_custom_aggregation_with_error_fallback(
        dataset_with_duplicates: Dataset
    ) -> None:
    """Test custom aggregation with error in specific target."""
    custom_agg = {
        "numeric_target": lambda col, dtype: col.invalid_method(),  # Fails
        "categorical_target": lambda col, dtype: col.last(),  # Works
    }

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        df = dataset_with_duplicates.to_df(custom_aggregation=custom_agg)

        # Should warn about custom aggregation failure
        warning_messages = [str(warning.message) for warning in w]
        assert any(
            "custom aggregation failed" in msg.lower()
            for msg in warning_messages
        )

    # Should use default for failed target, custom for successful target
    expected_df = pl.DataFrame({
        "sequence": ["ACGT", "TGCA"],
        "condition": ["test", "test"],
        "numeric_target": [1.5, 3.5],  # Default (mean)
        "categorical_target": ["B", "A"],  # Custom (last)
    })

    pl.testing.assert_frame_equal(
        df, expected_df, check_dtypes=False, check_column_order=False
    )
