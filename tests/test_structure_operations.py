"""
Module for testing structure operators.
"""

from biotite.structure import AtomArray

from proteingym.base.structure import Structure


def test_structure_not_equals_integer():
    """A structure should equal itself."""
    structure = Structure(
        name="Test Structure",
        value=AtomArray(0),
        description=None,
        metadata={},
    )
    assert structure != 1


def test_structure_equals_itself():
    """A structure should equal itself."""
    structure = Structure(
        name="Test Structure",
        value=AtomArray(0),
        description=None,
        metadata={},
    )
    assert structure == structure


def test_structure_with_data_equals_itself():
    """A structure with data should equal itself."""
    structure = Structure(
        name="Test Structure",
        value=AtomArray(0),
        description="A test structure",
        metadata={"source": "test"},
    )
    assert structure == structure
