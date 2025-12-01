"""
Module for testing MSA operators.
"""

from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from proteingym.base.msa import MSA


def test_msa_not_equals_integer():
    """An MSA should not equal an integer."""
    alignment = MultipleSeqAlignment(
        [
            SeqRecord(Seq("ACDEFG"), id="seq1"),
            SeqRecord(Seq("GFEDCA"), id="seq2"),
        ]
    )
    msa = MSA(
        name="Test MSA",
        value=alignment,
        description=None,
    )
    assert msa != 1


def test_msa_empty_equals_itself() -> None:
    """An empty msa should equal itself."""
    alignment = MultipleSeqAlignment([])
    msa = MSA(
        name="Test MSA",
        value=alignment,
        description=None,
    )
    assert msa == msa


def test_msa_with_data_equals_itself() -> None:
    """An MSA with data should equal itself."""
    alignment = MultipleSeqAlignment(
        [
            SeqRecord(Seq("ACDEFG"), id="seq1"),
            SeqRecord(Seq("GFEDCA"), id="seq2"),
        ]
    )
    msa = MSA(
        name="Test MSA",
        value=alignment,
        description="A test MSA",
    )
    assert msa == msa


def test_msa_compares_value() -> None:
    """An MSA should compare based on its value."""
    alignment2 = MultipleSeqAlignment([])
    alignment1 = MultipleSeqAlignment([])
    msa1 = MSA(name="msa1", value=alignment1, description="A test MSA")
    msa2 = MSA(name="msa2", value=alignment2, description="A test MSA")
    assert msa1 == msa2
