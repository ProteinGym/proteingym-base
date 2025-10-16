"""
Module for testing assay operators.
"""

import pytest

from proteingym.base.assay import Assay
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType


@pytest.mark.parametrize(
    "records",
    [
        [],
        [
            (
                Sequence(
                    name="seq1",
                    value="ACD",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            )
        ],
    ],
)
def test_assay_length_equals_records_length(
    records: list[tuple[Sequence | str | int | float | bool | str]],
) -> None:
    """The assay length should equal the number of records."""
    assay = Assay(name="Test Assay", records=records)
    assert len(assay) == len(records)


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
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            )
        ],
        columns=["sequence", "DMS_score"],
    )
    assert assay == assay


def test_assay_with_record_contains_itself() -> None:
    """An assay with a record should contain itself."""
    assay = Assay(
        name="Test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            )
        ],
        columns=["sequence", "DMS_score"],
    )
    assert assay in assay


def test_assay_contains_subset() -> None:
    """An subset should be part of the assay."""
    assay = Assay(
        name="Test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Subset of test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            )
        ],
        columns=["sequence", "DMS_score"],
    )
    assert subset in assay


def test_assay_contains_subset_mismatch() -> None:
    """This subset is not part of the assay."""
    assay = Assay(
        name="Test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Subset of test Assay",
        records=[
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                3.0,
            ),
        ],
        columns=["sequence", "DMS_score"],
    )
    assert subset not in assay


def test_assay_equals_with_name_mismatch() -> None:
    """An assay name should not be considered for equality."""
    assay = Assay(
        name="Test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable1": 1},
        columns=["sequence", "DMS_score"],
    )
    other_assay = Assay(
        name="Other Test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable1": 1},
        columns=["sequence", "DMS_score"],
    )
    assert assay == other_assay


def test_assay_equals_with_variable() -> None:
    """An assay with a record and variable should equal itself"""
    assay = Assay(
        name="Test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable1": 1},
        columns=["sequence", "DMS_score"],
    )
    assert assay == assay


def test_assay_equals_with_variable_mismatch() -> None:
    """Two assays with the same records but different variables should not be equal."""
    assay1 = Assay(
        name="Test assay 1",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable1": 1},
        columns=["sequence", "DMS_score"],
    )
    assay2 = Assay(
        name="Test assay 2",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    assert assay1 != assay2


def test_assay_contains_includes_variables() -> None:
    """Variables should also be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable1": 1, "variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Test assay subset",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    assert subset in assay


def test_assay_contains_includes_variable_mismatch() -> None:
    """Variables should also be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable1": 1, "variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Test assay subset",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable3": 3},
        columns=["sequence", "DMS_score"],
    )
    assert subset not in assay


def test_assay_contains_includes_variable_value_mismatch() -> None:
    """Variable values should be considered for equality."""
    assay = Assay(
        name="Test assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable1": 1, "variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    subset = Assay(
        name="Test assay subset",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable2": 3},
        columns=["sequence", "DMS_score"],
    )
    assert subset not in assay


@pytest.mark.parametrize("slc", [slice(None), [True, True]])
def test_assay_slice_all(slc: slice | list[bool]) -> None:
    """Slicing an assay with [:] should return the same assay."""
    assay = Assay(
        name="Test assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        variables={"variable1": 1, "variable2": 2},
        columns=["sequence", "DMS_score"],
    )
    assert assay == assay[slc]


@pytest.mark.parametrize("slc", [slice(0, 1), [True, False]])
def test_assay_slice_first_with_slice(slc: slice | list[bool]) -> None:
    """Slicing an assay with [:1] should return the first record."""
    assay = Assay(
        name="Test assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS_score"],
    )
    first = Assay(
        name="Test assay with first record",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
        ],
        columns=["sequence", "DMS_score"],
    )
    assert first == assay[slc]


@pytest.mark.parametrize("slc", [slice(1, 2), [False, True]])
def test_assay_slice_last(slc: slice | list[bool]) -> None:
    """Slicing an assay with [1:] should return the last record."""
    assay = Assay(
        name="Test assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS_score"],
    )
    last = Assay(
        name="Test assay with last record",
        records=[
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS_score"],
    )
    assert last == assay[slc]


def test_assay_get_first_raises_not_implemented_error() -> None:
    """Getting an assay with [0] should return the first record."""
    assay = Assay(
        name="Test assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value="APC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value="GTC",
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                2.0,
            ),
        ],
        columns=["sequence", "DMS_score"],
    )
    with pytest.raises(
        NotImplementedError, match="Getting a single record is not supported."
    ):
        assay[0]
