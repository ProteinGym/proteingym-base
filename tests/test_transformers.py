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

from proteingym.base.assay import Assay, Field
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
        assay_targets=[Field(name="DMS Score")],
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
        assay_targets=[Field(name="DMS Score")],
        assay_variables=[
            Field(name="pH", value=7.0),
            Field(name="temperature", value=37),
            Field(name="condition", value="A"),
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

    # Variant columns: pos0(A,D), pos1(B,E), pos2(C,F)
    # ABC → [1,0, 1,0, 1,0]  (A at pos0, B at pos1, C at pos2)
    # DEF → [0,1, 0,1, 0,1]  (D at pos0, E at pos1, F at pos2)
    expected = np.array(
        [
            [1.0, 0.0, 1.0, 0.0, 1.0, 0.0],  # ABC
            [0.0, 1.0, 0.0, 1.0, 0.0, 1.0],  # DEF
        ]
    )
    assert_array_equal(transformed, expected)


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

    # ABG → [1,0, 1,0, 0,0]  (A at pos0, B at pos1, G is unknown at pos2)
    expected = np.array([[1.0, 0.0, 1.0, 0.0, 0.0, 0.0]])
    assert_array_equal(transformed, expected)


def test_sequence_one_hot_encoder_get_feature_names_out() -> None:
    """Test SequenceOneHotEncoder.get_feature_names_out()."""
    encoder = SequenceOneHotEncoder()

    X = pl.DataFrame({"sequence": ["ABC", "DEF"]})
    encoder.fit(X)

    feature_names = encoder.get_feature_names_out(["sequence"])

    expected_names = np.array(
        [
            "sequence_pos0_A",
            "sequence_pos0_D",
            "sequence_pos1_B",
            "sequence_pos1_E",
            "sequence_pos2_C",
            "sequence_pos2_F",
        ]
    )
    assert_array_equal(feature_names, expected_names)


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

    # Variant columns: pos0(A,D), pos1(B,E), pos2(C,F)
    # ABC → [1,0, 1,0, 1,0], DEF → [0,1, 0,1, 0,1]
    expected = np.array(
        [
            [1.0, 0.0, 1.0, 0.0, 1.0, 0.0],  # ABC
            [0.0, 1.0, 0.0, 1.0, 0.0, 1.0],  # DEF
        ]
    )
    assert_array_equal(transformed, expected)


def test_assay_transformer_simple(simple_assay: Assay) -> None:
    """Test AssayTransformer with a simple assay (sequence + single target)."""
    df = simple_assay.to_df()

    transformer = AssayTransformer(
        sequence_column="sequence",
        target_columns=["DMS Score"],
    )

    X, y = transformer.fit_transform(df)

    expected_X = np.array(
        [
            [1.0, 0.0, 1.0, 0.0, 1.0, 0.0],  # ABC
            [0.0, 1.0, 0.0, 1.0, 0.0, 1.0],  # DEF
        ]
    )
    assert_array_equal(X, expected_X)

    expected_y = np.array([1.5, 2.0])
    assert_array_equal(y, expected_y)


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
    assert X.shape == (3, 11)  # 3 samples × 11 features

    expected_categorical = np.array([[1.0], [1.0], [1.0]])
    assert_array_equal(X[:, 8:9], expected_categorical)

    expected_y = np.array([1.5, 2.0, 1.8])
    assert_array_equal(y, expected_y)


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
    assert X.shape == (2, 7)  # 2 samples × 7 features

    expected_y = np.array(
        [
            [1.5, 0.8],  # DMS Score and Binding Affinity for sample 1
            [2.0, 0.9],  # DMS Score and Binding Affinity for sample 2
        ]
    )
    assert_array_equal(y, expected_y)


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

    expected_features_present = [
        "sequence_pos0_A",
        "sequence_pos0_D",
        "condition_A",
        "pH",
        "temperature",
    ]
    for feature in expected_features_present:
        assert feature in feature_names

    expected_positions = np.array(
        [
            "sequence_pos0_A",
            "condition_A",
            "pH",
            "temperature",
        ]
    )
    actual_positions = np.array(
        [
            feature_names[0],
            feature_names[8],
            feature_names[9],
            feature_names[10],
        ]
    )
    assert_array_equal(actual_positions, expected_positions)


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
    assert X.shape == (3, 11)  # 3 samples × 11 features

    # Dataset returns rows sorted by sequence: ABC (1.5), ACE (1.8), DEF (2.0)
    expected_y = np.array([1.5, 1.8, 2.0])
    assert_array_equal(y, expected_y)
