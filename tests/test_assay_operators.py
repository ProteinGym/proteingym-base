"""
Module for testing assay operators.
"""

from pg2_dataset.assay import Assay


def test_assay_empty_equals_itself():
    """An empty assay should equal itself."""
    assay = Assay(name="Test Assay", records=[])
    assert assay == assay


def test_assay_empty_contains_itself():
    """An empty assay should contain itself (via set operations)."""
    assay = Assay(name="Test Assay", records=[])
    assert assay in assay


def test_assay_with_record_equals_itself():
    """An assay with a record should equal itself."""
    assay = Assay(name="Test Assay", records=[("SEQ1", 1.0)])
    assert assay == assay


def test_assay_with_record_contains_itself():
    """An assay with a record should contain itself."""
    assay = Assay(name="Test Assay", records=[("SEQ1", 1.0)])
    assert assay in assay
