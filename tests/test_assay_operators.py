"""
Module for testing assay operators.
"""

import pytest

from proteingym.base.assay import Assay, SequenceAlphabet


def test_assay_not_equal_to_integer() -> None:
    """An assay is not equal to an integer"""
    assay = Assay(name="Test Assay", records=[])
    assert assay != 1


def test_assay_empty_equals_itself() -> None:
    """An empty assay should equal itself."""
    assay = Assay(name="Test Assay", records=[])
    assert assay == assay


def test_assay_empty_contains_itself() -> None:
    """An empty assay should contain itself (via set operations)."""
    assay = Assay(name="Test Assay", records=[])
    assert assay in assay


def test_assay_contains_returns_false_for_non_assay() -> None:
    """An assay should not contain a non-assay."""
    assay = Assay(name="Test Assay", records=[])
    assert 1 not in assay


def test_assay_with_record_equals_itself() -> None:
    """An assay with a record should equal itself."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0)],
        columns=["sequence", "DMS_score"],
    )
    assert assay == assay


def test_assay_with_record_contains_itself() -> None:
    """An assay with a record should contain itself."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0)],
        columns=["sequence", "DMS_score"],
    )
    assert assay in assay


def test_assay_contains_subset() -> None:
    """An subset should be part of the assay."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Subset of test Assay",
        records=[("SEQ2", 2.0)],
        columns=["sequence", "DMS_score"],
    )
    assert subset in assay


def test_assay_contains_subset_mismatch() -> None:
    """This subset is not part of the assay."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Subset of test Assay",
        records=[("SEQ3", 3.0)],
        columns=["sequence", "DMS_score"],
    )
    assert subset not in assay


def test_assay_equals_with_name_mismatch() -> None:
    """An assay name should not be considered for equality."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    other_assay = Assay(
        name="Other Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert assay == other_assay


def test_assay_equals_with_variable() -> None:
    """An assay with a record and variable should equal itself"""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1},
        columns=["sequence", "DMS_score"],
    )
    assert assay == assay


def test_assay_equals_with_variable_mismatch() -> None:
    """Two assays with the same records but different variables should not be equal."""
    assay1 = Assay(
        name="Test assay 1",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1},
        columns=["sequence", "DMS_score"],
    )
    assay2 = Assay(
        name="Test assay 2",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    assert assay1 != assay2


def test_assay_contains_includes_variables() -> None:
    """Variables should also be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1, "variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Test assay subset",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    assert subset in assay


def test_assay_contains_includes_variable_mismatch() -> None:
    """Variables should also be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1, "variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Test assay subset",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable3": 3},
        columns=["sequence", "DMS_score"],
    )
    assert subset not in assay


def test_assay_contains_includes_variable_value_mismatch() -> None:
    """Variable values should be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1, "variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Test assay subset",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable2": 3},
        columns=["sequence", "DMS_score"],
    )
    assert subset not in assay


@pytest.mark.parametrize("slc", [slice(None), [True, True]])
def test_assay_slice_all(slc: slice | list[bool]) -> None:
    """Slicing an assay with [:] should return the same assay."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1, "variable2": 2},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert assay == assay[slc]


@pytest.mark.parametrize("slc", [slice(0, 1), [True, False]])
def test_assay_slice_first_with_slice(slc: slice | list[bool]) -> None:
    """Slicing an assay with [:1] should return the first record."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    first = Assay(
        name="Test assay with first record",
        records=[("SEQ1", 1.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert first == assay[slc]


@pytest.mark.parametrize("slc", [slice(1, 2), [False, True]])
def test_assay_slice_last(slc: slice | list[bool]) -> None:
    """Slicing an assay with [1:] should return the last record."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    last = Assay(
        name="Test assay with last record",
        records=[("SEQ2", 2.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert last == assay[slc]


def test_assay_get_first_raises_not_implemented_error() -> None:
    """Getting an assay with [0] should return the first record."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    with pytest.raises(
        NotImplementedError, match="Getting a single record is not supported."
    ):
        assay[0]
