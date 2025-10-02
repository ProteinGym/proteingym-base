"""
Module for testing assay operators.
"""

from proteingym.base.assay import Assay, SequenceAlphabet


def test_assay_not_equal_to_integer() -> None:
    """An assay is not equal to an integer"""
    assay = Assay(name="Test Assay", records=[], sequence_alphabet=SequenceAlphabet.AA)
    assert assay != 1


def test_assay_empty_equals_itself() -> None:
    """An empty assay should equal itself."""
    assay = Assay(name="Test Assay", records=[], sequence_alphabet=SequenceAlphabet.AA)
    assert assay == assay


def test_assay_empty_contains_itself() -> None:
    """An empty assay should contain itself (via set operations)."""
    assay = Assay(name="Test Assay", records=[], sequence_alphabet=SequenceAlphabet.AA)
    assert assay in assay


def test_assay_with_record_equals_itself() -> None:
    """An assay with a record should equal itself."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert assay == assay


def test_assay_with_record_contains_itself() -> None:
    """An assay with a record should contain itself."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert assay in assay


def test_assay_contains_subset() -> None:
    """An subset should be part of the assay."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    subset = Assay(
        name="Subset of test Assay",
        records=[("SEQ2", 2.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert subset in assay


def test_assay_contains_subset_mismatch() -> None:
    """This subset is not part of the assay."""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    subset = Assay(
        name="Subset of test Assay",
        records=[("SEQ3", 3.0)],
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert subset not in assay


def test_assay_equals_with_variable() -> None:
    """An assay with a record and variable should equal itself"""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert assay == assay


def test_assay_equals_with_variable_mismatch() -> None:
    """Two assays with the same records but different variables should not be equal."""
    assay1 = Assay(
        name="Test assay 1",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assay2 = Assay(
        name="Test assay 2",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable2": 2},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert assay1 != assay2


def test_assay_contains_includes_variables() -> None:
    """Variables should also be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1, "variable2": 2},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    subset = Assay(
        name="Test assay subset",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable2": 2},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert subset in assay


def test_assay_contains_includes_variable_mismatch() -> None:
    """Variables should also be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1, "variable2": 2},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    subset = Assay(
        name="Test assay subset",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable3": 3},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert subset not in assay


def test_assay_contains_includes_variable_value_mismatch() -> None:
    """Variable values should be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable1": 1, "variable2": 2},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    subset = Assay(
        name="Test assay subset",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        variables={"variable2": 3},
        sequence_alphabet=SequenceAlphabet.AA,
    )
    assert subset not in assay
