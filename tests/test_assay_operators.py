"""
Module for testing assay operators.

TODO:
Move repetitive sequence and assay into fixtures.
"""

import pytest
from Bio.Seq import Seq

from proteingym.base.assay import Assay, AssaySlice, AssayTarget
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType


def test_assay_target_equality_does_not_consider_description() -> None:
    """Test that assay target equality does not consider the description."""
    assay_target1 = AssayTarget(name="DMS Score", description="DMS score")
    assay_target2 = AssayTarget(name="DMS Score", description="Different description")
    assert assay_target1 == assay_target2


def test_assay_length_equals_records_length() -> None:
    """The assay length should equal the number of records."""
    sequence = Sequence(
        name="seq1",
        value=Seq("ACD"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assay = Assay(name="Test Assay", records=[(sequence, 1.0), (sequence, 2.0)])
    assert len(assay) == 2


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
                    value=Seq("APC"),
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
    sequence = Sequence(
        name="seq1",
        value=Seq("APC"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assay = Assay(
        name="Test Assay", records=[(sequence, 1.0)], columns=["sequence", "DMS_score"]
    )
    assert assay in assay


def test_assay_empty_in_assay_with_record() -> None:
    """An empty assay should be a subset of an assay with a record."""
    assay_empty = Assay(name="Empty Assay", records=[])
    assay = Assay(
        name="Test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            )
        ],
        columns=["sequence", "DMS_score"],
    )
    assert assay_empty in assay


def test_assay_contains_subset() -> None:
    """An subset should be part of the assay."""
    assay = Assay(
        name="Test Assay",
        records=[
            (
                Sequence(
                    name="seq1",
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
                    value=Seq("GTC"),
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
                    value=Seq("APC"),
                    type=SequenceType.WILD_TYPE,
                    alphabet=SequenceAlphabet.AA,
                ),
                1.0,
            ),
            (
                Sequence(
                    name="seq2",
                    value=Seq("GTC"),
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
        assay[0]  # noqa


@pytest.fixture
def seq1() -> Sequence:
    """A test sequence 1."""
    seq1 = Sequence(
        name="seq1",
        value="APC",
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    return seq1


@pytest.fixture
def seq2() -> Sequence:
    """A test sequence 2."""
    seq2 = Sequence(
        name="seq2",
        value="GTC",
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    return seq2


def test_assay_slice_empty(seq1: Sequence, seq2: Sequence) -> None:
    """An empty mask should return the assay without records"""
    excepted = Assay(
        name="Test assay", records=[], columns=["sequence", "DMS_score", "stability"]
    )

    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )
    assert assay[[]] == excepted


def test_assay_slice_column_string_raises_not_implemented_error(
    seq1: Sequence, seq2: Sequence
) -> None:
    """Slicing an assay with a column string raises a NotImplementedError."""
    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )

    with pytest.raises(
        NotImplementedError, match="Getting a single column is not supported."
    ):
        assay["stability"]


def test_assay_slice_column_string_raises_key_error_for_unknown_column(
    seq1: Sequence, seq2: Sequence
) -> None:
    """Slicing an assy with an unknown column string raises a KeyError."""
    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )

    with pytest.raises(KeyError, match=r"Undefined columns: {'unknown'}"):
        assay[["sequence", "unknown"]]


def test_assay_slice_column(seq1: Sequence, seq2: Sequence) -> None:
    """Slicing an assay with a column returns an assay with only that column."""
    expected = Assay(name="Test assay", records=[(1.5,), (2.5,)], columns=["stability"])

    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )

    actual = assay[["stability"]]
    assert actual == expected


def test_assay_slice_columns(seq1: Sequence, seq2: Sequence) -> None:
    """Slicing an assay with columns returns an assay with those columns."""
    expected = Assay(
        name="Test assay",
        records=[
            (seq1, 1.5),
            (seq2, 2.5),
        ],
        columns=["sequence", "stability"],
    )

    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )

    actual = assay[["sequence", "stability"]]
    assert actual == expected


def test_assay_slice_object_with_columns(seq1: Sequence, seq2: Sequence) -> None:
    """Slicing an assay with columns returns an assay with those columns."""
    expected = Assay(
        name="Test assay",
        records=[
            (seq1, 1.5),
            (seq2, 2.5),
        ],
        columns=["sequence", "stability"],
    )

    slc = AssaySlice(columns=["sequence", "stability"])
    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )

    actual = assay[slc]
    assert actual == expected


def test_assay_slice_object_with_records(seq1: Sequence, seq2: Sequence) -> None:
    """Slicing an assay with records returns an assay with those records."""
    expected = Assay(
        name="Test assay",
        records=[
            (seq1, 1.0, 1.5),
        ],
        columns=["sequence", "DMS_score", "stability"],
    )

    slc = AssaySlice(records=[True, False])
    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )

    actual = assay[slc]
    assert actual == expected


def test_assay_slice_object_with_records_and_columns(
    seq1: Sequence, seq2: Sequence
) -> None:
    """Slicing an assay with records and columns returns an assay with those records."""
    expected = Assay(
        name="Test assay",
        records=[
            (seq1, 1.0),
        ],
        columns=["sequence", "DMS_score"],
    )

    slc = AssaySlice(records=[True, False], columns=["sequence", "DMS_score"])
    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )

    actual = assay[slc]
    assert actual == expected


def test_assay_slice_object_with_empty_columns(seq1: Sequence, seq2: Sequence) -> None:
    """Slicing an assay without columns returns an empty assay."""
    expected = Assay(name="Test assay", records=[], columns=[])

    slc = AssaySlice(records=[True, False], columns=[])
    assay = Assay(
        name="Test assay",
        records=[(seq1, 1.0, 1.5), (seq2, 2.0, 2.5)],
        columns=["sequence", "DMS_score", "stability"],
    )

    actual = assay[slc]
    assert actual == expected
