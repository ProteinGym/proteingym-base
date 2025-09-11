"""
Module for testing sequence operators.
"""

from pg2_dataset.sequence import Sequence, SequenceType, SequenceAlphabet
from Bio.Seq import Seq


def test_sequence_equals_itself():
    """A sequence should equal itself."""
    sequence = Sequence(name="Test Sequence", value=Seq("") , type=SequenceType.WILD_TYPE, alphabet=SequenceAlphabet.AA)
    assert sequence == sequence


def test_sequence_with_data_equals_itself():
    """A sequence with data should equal itself."""
    sequence = Sequence(name="Test Sequence", value=Seq("ACDEFG"), type=SequenceType.WILD_TYPE, alphabet=SequenceAlphabet.AA)
    assert sequence == sequence
