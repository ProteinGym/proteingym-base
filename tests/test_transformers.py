"""Tests for sklearn transformers."""
# Ignore argument and variable `X` in function should be lowercase
# ruff: noqa: N803, N806

import numpy as np
import polars as pl
import pytest
from Bio.Seq import Seq
from numpy.testing import assert_array_equal

from proteingym.base.assay import Assay
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType
from proteingym.base.transformers import AssayTransformer, SequenceOneHotEncoder


@pytest.fixture
def simple_assay() -> Assay:
    """Create a simple assay for testing."""
    seq1 = Sequence(
        name="seq1",
        value=Seq("ABC"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )
    seq2 = Sequence(
        name="seq2",
        value=Seq("DEF"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )
    return Assay(
        name="test_assay",
        records=[
            (seq1, 1.5),
            (seq2, 2.0),
        ],
        columns=["sequence", "DMS Score"],
    )


@pytest.fixture
def assay_with_variables() -> Assay:
    """Create an assay with both categorical and numerical variables."""
    seq1 = Sequence(
        name="seq1",
        value=Seq("ABC"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )
    seq2 = Sequence(
        name="seq2",
        value=Seq("DEF"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )
    seq3 = Sequence(
        name="seq3",
        value=Seq("ACE"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )
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
def assay_with_multiple_targets() -> Assay:
    """Create an assay with multiple target columns."""
    seq1 = Sequence(
        name="seq1",
        value=Seq("ABC"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )
    seq2 = Sequence(
        name="seq2",
        value=Seq("DEF"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.DNA,
    )
    return Assay(
        name="test_assay",
        records=[
            (seq1, 1.5, 0.8),
            (seq2, 2.0, 0.9),
        ],
        columns=["sequence", "DMS Score", "Binding Affinity"],
        variables={"pH": 7.0},
    )


def test_sequence_one_hot_encoder_basic() -> None:
    """Test basic functionality of SequenceOneHotEncoder."""
    encoder = SequenceOneHotEncoder()

    X = pl.DataFrame({"sequence": ["ABC", "DEF"]}).to_numpy()

    encoder.fit(X)
    transformed = encoder.transform(X)

    assert encoder.alphabet_ == ["A", "B", "C", "D", "E", "F"]
    assert encoder.max_length_ == 3

    assert transformed.shape == (2, 3 * 6)  # 3 positions × 6 characters

    assert np.sum(transformed[0, :]) == 3.0  # Has 3 characters
    assert transformed[0, 0] == 1.0  # A at position 0
    assert transformed[0, 7] == 1.0  # B at position 1
    assert transformed[0, 14] == 1.0  # C at position 2

    assert np.sum(transformed[1, :]) == 3.0  # Has 3 characters
    assert transformed[1, 3] == 1.0  # D at position 0
    assert transformed[1, 10] == 1.0  # E at position 1
    assert transformed[1, 17] == 1.0  # F at position 2


def test_sequence_one_hot_encoder_different_lengths() -> None:
    """Test SequenceOneHotEncoder with sequences of different lengths."""
    encoder = SequenceOneHotEncoder()

    X = pl.DataFrame({"sequence": ["AB", "ABCD"]}).to_numpy()

    encoder.fit(X)
    transformed = encoder.transform(X)

    assert encoder.alphabet_ == ["A", "B", "C", "D"]
    assert encoder.max_length_ == 4

    assert transformed.shape == (2, 4 * 4)  # 4 positions × 4 characters

    # Shorter sequences should be padded with zeros at the end
    assert np.sum(transformed[0, :]) == 2.0  # Has 2 characters
    assert transformed[0, 0] == 1.0  # A at position 0
    assert transformed[0, 5] == 1.0  # B at position 1

    assert np.sum(transformed[1, :]) == 4.0  # Has 4 characters
    assert transformed[1, 0] == 1.0  # A at position 0
    assert transformed[1, 5] == 1.0  # B at position 1
    assert transformed[1, 10] == 1.0  # C at position 2
    assert transformed[1, 15] == 1.0  # D at position 3


def test_sequence_one_hot_encoder_unknown_char() -> None:
    """Test SequenceOneHotEncoder with unknown characters in transform."""
    encoder = SequenceOneHotEncoder()

    X_train = pl.DataFrame({"sequence": ["ABC"]}).to_numpy()
    encoder.fit(X_train)

    # Transform with unknown character 'D'
    X_test = pl.DataFrame({"sequence": ["ABD"]}).to_numpy()
    transformed = encoder.transform(X_test)

    # Should have zeros for unknown character
    assert transformed.shape == (1, 3 * 3)  # 3 positions × 3 characters
    assert transformed[0, 0] == 1.0  # A at position 0
    assert transformed[0, 4] == 1.0  # B at position 1
    assert np.sum(transformed[0, 6:9]) == 0.0  # D is unknown, all zeros at position 2


def test_sequence_one_hot_encoder_get_feature_names_out() -> None:
    """Test SequenceOneHotEncoder.get_feature_names_out()."""
    encoder = SequenceOneHotEncoder()

    X = pl.DataFrame({"sequence": ["ABC", "DEF"]}).to_numpy()
    encoder.fit(X)

    feature_names = encoder.get_feature_names_out(["sequence"])

    assert len(feature_names) == 18  # 3 positions × 6 characters
    assert feature_names[0] == "sequence_pos0_A"
    assert feature_names[1] == "sequence_pos0_B"
    assert feature_names[6] == "sequence_pos1_A"
    assert feature_names[12] == "sequence_pos2_A"
    assert feature_names[17] == "sequence_pos2_F"


def test_assay_transformer_simple(simple_assay: Assay) -> None:
    """Test AssayTransformer with a simple assay (sequence + single target)."""
    df = simple_assay.to_df()

    transformer = AssayTransformer(
        sequence_column="sequence",
        target_columns=["DMS Score"],
    )

    X, y = transformer.fit_transform(df)

    assert X.shape[0] == 2  # 2 samples
    assert X.shape[1] == 3 * 6  # 3 positions × 6 characters
    assert_array_equal(
        X[0],
        [
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
        ],
    )
    assert_array_equal(
        X[1],
        [
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
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
    # Sequence: 3 positions × 6 chars = 18
    # Categorical: 1 (condition_A)
    # Numerical: 2 (pH, temperature)
    assert X.shape[0] == 3  # 3 samples
    assert X.shape[1] == 18 + 1 + 2  # 21 total features

    categorical_features = X[:, 18:19]

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
    # Sequence: 3 positions × 6 chars = 18
    # Numerical: 1 (pH)
    assert X.shape[0] == 2  # 2 samples
    assert X.shape[1] == 18 + 1  # 19 total features

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

    assert len(feature_names) == 21  # 18 sequence + 1 categorical + 2 numerical

    assert "sequence_pos0_A" in feature_names
    assert "sequence_pos0_B" in feature_names
    assert "condition_A" in feature_names
    assert "pH" in feature_names
    assert "temperature" in feature_names

    assert feature_names[0] == "sequence_pos0_A"
    assert feature_names[18] == "condition_A"
    assert feature_names[19] == "pH"
    assert feature_names[20] == "temperature"
