"""
Module for testing MSA operators.
"""

from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from proteingym.base.msa import MSA


def test_msa_not_equals_integer():
    """A MSA should not equal an integer."""
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


def test_msa_equals_itself():
    """An MSA should equal itself."""
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
    assert msa == msa


def test_msa_with_data_equals_itself():
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
