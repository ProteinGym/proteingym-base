"""
Module for testing sequence operators.
"""

from Bio.Seq import Seq

from proteingym.base.sequence import (
    Sequence,
    SequenceAlphabet,
    SequenceType,
)


def test_sequence_not_equals_integer() -> None:
    """A sequence should not equal an integer."""
    sequence = Sequence(
        name="Test Sequence",
        value=Seq(""),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assert sequence != 1


def test_sequence_equals_itself() -> None:
    """A sequence should equal itself."""
    sequence = Sequence(
        name="Test Sequence",
        value=Seq(""),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assert sequence == sequence


def test_sequence_with_data_equals_itself() -> None:
    """A sequence with data should equal itself."""
    sequence = Sequence(
        name="Test Sequence",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assert sequence == sequence


def test_sequence_with_different_value_not_equals() -> None:
    """A sequence with different value should not equal."""
    sequence1 = Sequence(
        name="Test Sequence",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="Test Sequence",
        value=Seq("HIKLMN"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assert sequence1 != sequence2


def test_sequence_with_different_alphabet_not_equals() -> None:
    """A sequence with different alphabet should not equal."""
    sequence1 = Sequence(
        name="Test Sequence",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="Test Sequence",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    assert sequence1 != sequence2


def test_sequence_with_different_name_equals() -> None:
    """A sequence with a different name but same value should equal."""
    sequence1 = Sequence(
        name="Test Sequence 1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="Test Sequence 2",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assert sequence1 == sequence2
