"""
Module for testing structure operators.
"""

from Bio.PDB.Structure import Structure as BioStructure

from proteingym.base.structure import Structure


def test_structure_equals_itself():
    """A structure should equal itself."""
    bio_structure = BioStructure("test")
    structure = Structure(
        name="Test Structure",
        value=bio_structure,
        description=None,
        metadata={},
    )
    assert structure == structure


def test_structure_with_data_equals_itself():
    """A structure with data should equal itself."""
    bio_structure = BioStructure("test_with_data")
    structure = Structure(
        name="Test Structure",
        value=bio_structure,
        description="A test structure",
        metadata={"source": "test"},
    )
    assert structure == structure
