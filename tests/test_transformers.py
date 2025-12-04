"""Tests for sklearn transformers."""
# Ignore argument and variable `X` in function should be lowercase
# ruff: noqa: N803, N806

# PyCharm: Suppress PEP 8 naming warnings for sklearn transformer methods
# noinspection PyPep8Naming

import numpy as np
import pandas as pd
import polars as pl
import pytest
from Bio.Seq import Seq
from numpy.testing import assert_array_equal

from proteingym.base.assay import Assay, AssayTarget, AssayVariable
from proteingym.base.dataset import Dataset
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType
from proteingym.base.transformers import AssayTransformer, SequenceOneHotEncoder


@pytest.fixture
def seq1() -> Sequence:
    return Sequence(
        name="seq1",
        value=Seq("ABC"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )


@pytest.fixture
def seq2() -> Sequence:
    return Sequence(
        name="seq2",
        value=Seq("DEF"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )


@pytest.fixture
def seq3() -> Sequence:
    return Sequence(
        name="seq3",
        value=Seq("ACE"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )


@pytest.fixture
def simple_assay(seq1: Sequence, seq2: Sequence) -> Assay:
    """Create a simple assay for testing."""
    return Assay(
        name="test_assay",
        records=[
            (seq1, 1.5),
            (seq2, 2.0),
        ],
        columns=["sequence", "DMS Score"],
    )


@pytest.fixture
def assay_with_variables(seq1: Sequence, seq2: Sequence, seq3: Sequence) -> Assay:
    """Create an assay with both categorical and numerical variables."""
    return Assay(
        name="test_assay",
        records=[
            (seq1, 1.5),
            (seq2, 2.0),
            (seq3, 1.8),
        ],
        columns=["sequence", "DMS Score"],
        variables={"pH": 7.0, "temperature": 37, "condition": "A"},
    )


@pytest.fixture
def assay_with_multiple_targets(seq1: Sequence, seq2: Sequence) -> Assay:
    """Create an assay with multiple target columns."""
    return Assay(
        name="test_assay",
        records=[
            (seq1, 1.5, 0.8),
            (seq2, 2.0, 0.9),
        ],
        columns=["sequence", "DMS Score", "Binding Affinity"],
        variables={"pH": 7.0},
    )


@pytest.fixture
def simple_dataset(seq1: Sequence, seq2: Sequence, simple_assay: Assay) -> Dataset:
    """Create a simple dataset from simple_assay fixture."""
    return Dataset(
        name="test_dataset",
        sequences=[seq1, seq2],
        assays=[simple_assay],
        assay_targets=[AssayTarget(name="DMS Score")],
    )


@pytest.fixture
def dataset_with_variables(
    seq1: Sequence, seq2: Sequence, seq3: Sequence, assay_with_variables: Assay
) -> Dataset:
    """Create a dataset with variables from assay_with_variables fixture."""
    return Dataset(
        name="test_dataset",
        sequences=[seq1, seq2, seq3],
        assays=[assay_with_variables],
        assay_targets=[AssayTarget(name="DMS Score")],
        assay_variables=[
            AssayVariable(name="pH", value=7.0),
            AssayVariable(name="temperature", value=37),
            AssayVariable(name="condition", value="A"),
        ],
    )


def test_sequence_one_hot_encoder_basic() -> None:
    """Test basic functionality of SequenceOneHotEncoder."""
    encoder = SequenceOneHotEncoder()

    X = pl.DataFrame({"sequence": ["ABC", "DEF"]})

    encoder.fit(X)
    transformed = encoder.transform(X)

    assert encoder.alphabet_ == ["A", "B", "C", "D", "E", "F"]
    assert encoder.max_length_ == 3

    # Only variant columns are kept: 2 chars per position × 3 positions = 6 features
    assert transformed.shape == (2, 6)

    # Each sequence should still have 3 one-hot encoded positions
    assert np.sum(transformed[0, :]) == 3.0  # Has 3 characters
    assert np.sum(transformed[1, :]) == 3.0  # Has 3 characters

    # Position 0: A=1 or D=1, Position 1: B=1 or E=1, Position 2: C=1 or F=1
    assert transformed[0, 0] == 1.0  # A at position 0
    assert transformed[0, 2] == 1.0  # B at position 1
    assert transformed[0, 4] == 1.0  # C at position 2

    assert transformed[1, 1] == 1.0  # D at position 0
    assert transformed[1, 3] == 1.0  # E at position 1
    assert transformed[1, 5] == 1.0  # F at position 2


def test_sequence_one_hot_encoder_different_lengths_raises_error() -> None:
    """SequenceOneHotEncoder raises error for sequences of different lengths."""
    encoder = SequenceOneHotEncoder()

    X = pl.DataFrame({"sequence": ["AB", "ABCD"]})

    with pytest.raises(ValueError, match="All sequences must have the same length"):
        encoder.fit(X)

    # Test error during transform when sequences don't match training length
    encoder = SequenceOneHotEncoder()
    X_train = pl.DataFrame({"sequence": ["ABC", "DEF"]})
    encoder.fit(X_train)

    X_test = pl.DataFrame({"sequence": ["AB", "CD"]})
    with pytest.raises(
        ValueError,
        match="Expected sequences of length 3 .* but got sequences of length 2",
    ):
        encoder.transform(X_test)

    # Test error during transform when test sequences have varying lengths
    X_test_varying = pl.DataFrame({"sequence": ["AB", "ABCD"]})
    with pytest.raises(ValueError, match="All sequences must have the same length"):
        encoder.transform(X_test_varying)


def test_sequence_one_hot_encoder_unknown_char() -> None:
    """Test SequenceOneHotEncoder with unknown characters in transform."""
    encoder = SequenceOneHotEncoder()

    X_train = pl.DataFrame({"sequence": ["ABC", "DEF"]})
    encoder.fit(X_train)

    # Transform with unknown character 'G' at position 2
    X_test = pl.DataFrame({"sequence": ["ABG"]})
    transformed = encoder.transform(X_test)

    assert transformed.shape == (1, 6)

    assert np.sum(transformed[0, :]) == 2.0
    assert transformed[0, 0] == 1.0  # A at position 0
    assert transformed[0, 2] == 1.0  # B at position 1

    # Position 2 should be all zeros (G is unknown)
    assert transformed[0, 4] == 0.0  # C at position 2 (not present)
    assert transformed[0, 5] == 0.0  # F at position 2 (not present)


def test_sequence_one_hot_encoder_get_feature_names_out() -> None:
    """Test SequenceOneHotEncoder.get_feature_names_out()."""
    encoder = SequenceOneHotEncoder()

    X = pl.DataFrame({"sequence": ["ABC", "DEF"]})
    encoder.fit(X)

    feature_names = encoder.get_feature_names_out(["sequence"])

    assert len(feature_names) == 6
    assert feature_names[0] == "sequence_pos0_A"
    assert feature_names[1] == "sequence_pos0_D"
    assert feature_names[2] == "sequence_pos1_B"
    assert feature_names[3] == "sequence_pos1_E"
    assert feature_names[4] == "sequence_pos2_C"
    assert feature_names[5] == "sequence_pos2_F"


def test_sequence_one_hot_encoder_pandas_support() -> None:
    """Test SequenceOneHotEncoder with pandas DataFrame and Series."""
    encoder = SequenceOneHotEncoder()

    X_df = pd.DataFrame({"sequence": ["ABC", "DEF"]})
    encoder.fit(X_df)
    transformed_df = encoder.transform(X_df)

    assert encoder.alphabet_ == ["A", "B", "C", "D", "E", "F"]
    assert encoder.max_length_ == 3

    assert transformed_df.shape == (2, 6)

    encoder2 = SequenceOneHotEncoder()
    X_series = pd.Series(["ABC", "DEF"])
    encoder2.fit(X_series)
    transformed_series = encoder2.transform(X_series)

    assert encoder2.alphabet_ == ["A", "B", "C", "D", "E", "F"]
    assert encoder2.max_length_ == 3
    assert transformed_series.shape == (2, 6)

    assert_array_equal(transformed_df, transformed_series)


def test_sequence_one_hot_encoder_dataset_support(simple_dataset: Dataset) -> None:
    """Test SequenceOneHotEncoder with Dataset."""
    encoder = SequenceOneHotEncoder()

    encoder.fit(simple_dataset)
    transformed = encoder.transform(simple_dataset)

    assert encoder.alphabet_ == ["A", "B", "C", "D", "E", "F"]
    assert encoder.max_length_ == 3

    assert transformed.shape == (2, 6)

    assert np.sum(transformed[0, :]) == 3.0  # Has 3 characters
    assert transformed[0, 0] == 1.0  # A at position 0
    assert transformed[0, 2] == 1.0  # B at position 1
    assert transformed[0, 4] == 1.0  # C at position 2

    assert np.sum(transformed[1, :]) == 3.0  # Has 3 characters
    assert transformed[1, 1] == 1.0  # D at position 0
    assert transformed[1, 3] == 1.0  # E at position 1
    assert transformed[1, 5] == 1.0  # F at position 2


def test_assay_transformer_simple(simple_assay: Assay) -> None:
    """Test AssayTransformer with a simple assay (sequence + single target)."""
    df = simple_assay.to_df()

    transformer = AssayTransformer(
        sequence_column="sequence",
        target_columns=["DMS Score"],
    )

    X, y = transformer.fit_transform(df)

    assert X.shape[0] == 2  # 2 samples
    assert X.shape[1] == 6  # Only variant features: 2 per position × 3
    assert_array_equal(
        X[0],
        [
            1.0,  # A at position 0
            0.0,  # D at position 0 (not present)
            1.0,  # B at position 1
            0.0,  # E at position 1 (not present)
            1.0,  # C at position 2
            0.0,  # F at position 2 (not present)
        ],
    )
    assert_array_equal(
        X[1],
        [
            0.0,  # A at position 0 (not present)
            1.0,  # D at position 0
            0.0,  # B at position 1 (not present)
            1.0,  # E at position 1
            0.0,  # C at position 2 (not present)
            1.0,  # F at position 2
        ],
    )

    assert y.shape == (2,)  # 2 targets
    assert y[0] == 1.5
    assert y[1] == 2.0


def test_assay_transformer_with_variables(assay_with_variables: Assay) -> None:
    """Test AssayTransformer with categorical and numerical variables."""
    df = assay_with_variables.to_df()

    transformer = AssayTransformer(
        sequence_column="sequence",
        target_columns=["DMS Score"],
        categorical_columns=["condition"],
        numerical_columns=["pH", "temperature"],
    )

    X, y = transformer.fit_transform(df)

    # Check that features include sequence + categorical + numerical
    # Sequence variant features: pos0(A,D) + pos1(B,C,E) + pos2(C,E,F) = 8
    # Categorical: 1 (condition_A)
    # Numerical: 2 (pH, temperature)
    assert X.shape[0] == 3  # 3 samples
    assert X.shape[1] == 8 + 1 + 2  # 11 total features

    categorical_features = X[:, 8:9]

    assert categorical_features[0, 0] == 1.0
    assert categorical_features[1, 0] == 1.0
    assert categorical_features[2, 0] == 1.0

    assert y.shape == (3,)  # 3 samples × 1 target
    assert y[0] == 1.5
    assert y[1] == 2.0
    assert y[2] == 1.8


def test_assay_transformer_multiple_targets(assay_with_multiple_targets: Assay) -> None:
    """Test AssayTransformer with multiple target columns."""
    df = assay_with_multiple_targets.to_df()

    transformer = AssayTransformer(
        sequence_column="sequence",
        target_columns=["DMS Score", "Binding Affinity"],
        numerical_columns=["pH"],
    )

    X, y = transformer.fit_transform(df)

    # Check that features include sequence + numerical
    # Sequence variant features: 2 per position × 3 positions = 6
    # Numerical: 1 (pH)
    assert X.shape[0] == 2  # 2 samples
    assert X.shape[1] == 6 + 1  # 7 total features

    assert y.shape == (2, 2)  # 2 samples × 2 targets
    assert y[0, 0] == 1.5  # DMS Score for sample 1
    assert y[0, 1] == 0.8  # Binding Affinity for sample 1
    assert y[1, 0] == 2.0  # DMS Score for sample 2
    assert y[1, 1] == 0.9  # Binding Affinity for sample 2


def test_assay_transformer_transform_without_fit(simple_assay: Assay) -> None:
    """Test that transform raises error if called before fit."""
    df = simple_assay.to_df()

    transformer = AssayTransformer(
        sequence_column="sequence",
        target_columns=["DMS Score"],
    )

    with pytest.raises(ValueError, match="has not been fitted"):
        transformer.transform(df)


def test_assay_transformer_get_feature_names_out(assay_with_variables: Assay) -> None:
    """Test getting feature names from the transformer."""
    df = assay_with_variables.to_df()

    transformer = AssayTransformer(
        sequence_column="sequence",
        target_columns=["DMS Score"],
        categorical_columns=["condition"],
        numerical_columns=["pH", "temperature"],
    )

    transformer.fit(df)

    feature_names = transformer.get_feature_names_out()

    assert len(feature_names) == 11  # 8 variant sequence + 1 categorical + 2 numerical

    assert "sequence_pos0_A" in feature_names
    assert "sequence_pos0_D" in feature_names
    # pos0_B won't be in feature names (invariant - never appears)
    assert "condition_A" in feature_names
    assert "pH" in feature_names
    assert "temperature" in feature_names

    assert feature_names[0] == "sequence_pos0_A"
    assert feature_names[8] == "condition_A"
    assert feature_names[9] == "pH"
    assert feature_names[10] == "temperature"


def test_assay_transformer_from_dataset(dataset_with_variables: Dataset) -> None:
    """Test AssayTransformer.from_dataset() using fixture."""
    transformer = AssayTransformer.from_dataset(dataset_with_variables)

    assert transformer.sequence_column == "sequence"
    assert transformer.target_columns == ["DMS Score"]
    assert "condition" in transformer.categorical_columns
    assert "pH" in transformer.numerical_columns
    assert "temperature" in transformer.numerical_columns

    X, y = transformer.fit_transform(dataset_with_variables)

    # Sequence variant features: pos0(A,D) + pos1(B,C,E) + pos2(C,E,F) = 8
    # Categorical: 1 (condition_A)
    # Numerical: 2 (pH, temperature)
    assert X.shape[0] == 3  # 3 samples
    assert X.shape[1] == 8 + 1 + 2  # 11 total features

    assert y.shape == (3,)
    # Dataset returns rows sorted by sequence: ABC (1.5), ACE (1.8), DEF (2.0)
    assert y[0] == 1.5
    assert y[1] == 1.8
    assert y[2] == 2.0
