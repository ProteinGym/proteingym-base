"""
Module for testing assay operators.
"""

from pg2_dataset.assay import Assay


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


def test_assay_with_record_equals_itself() -> None:
    """An assay with a record should equal itself."""
    assay = Assay(name="Test Assay", records=[("SEQ1", 1.0)])
    assert assay == assay


def test_assay_with_record_contains_itself() -> None:
    """An assay with a record should contain itself."""
    assay = Assay(name="Test Assay", records=[("SEQ1", 1.0)])
    assert assay in assay


def test_assay_contains_subset() -> None:
    """An subset should be part of the assay."""
    assay = Assay(name="Test Assay", records=[("SEQ1", 1.0), ("SEQ2", 2.0)])
    subset = Assay(name="Subset of test Assay", records=[("SEQ2", 2.0)])
    assert subset in assay


def test_assay_equals_with_condition() -> None:
    """An assay with a record and condition should equal itself"""
    assay = Assay(
        name="Test Assay",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        conditions={"condition1": 1},
    )
    assert assay == assay


def test_assay_equals_with_condition_mismatch() -> None:
    """Two assays with the same records but different conditions should not be equal."""
    assay1 = Assay(
        name="Test assay 1",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        conditions={"condition1": 1},
    )
    assay2 = Assay(
        name="Test assay 2",
        records=[("SEQ1", 1.0), ("SEQ2", 2.0)],
        conditions={"condition2": 1},
    )
    assert assay1 != assay2
