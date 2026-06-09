import functools

import numpy as np
import polars as pl
import polars.testing
import pytest
from Bio.Seq import Seq

from proteingym.base.assay import Field
from proteingym.base.dataset import Assay, Dataset, Sequence, Subsets
from proteingym.base.sequence import SequenceAlphabet, SequenceType
from proteingym.base.splits import (
    KFoldQuantileSplitter,
    KFoldSplitter,
    PredefinedSplitter,
    QuantileSplitter,
    RandomSplitter,
    _cast_indices_to_mask,  # noqa
    _reshape_list,  # noqa
    _subsample_mask,  # noqa
    _unique_sequences_for_targets,  # noqa
)


@pytest.mark.parametrize(
    "indices, length, expected",
    [
        ([0, 2, 4], 6, [True, False, True, False, True, False]),
        ([1, 3], 5, [False, True, False, True, False]),
        ([], 4, [False, False, False, False]),
    ],
)
def test_cast_indices_to_mask(
    indices: list[int], length: int, expected: list[bool]
) -> None:
    """Unit test the _cast_indices_to_mask function."""
    assert _cast_indices_to_mask(indices, length=length) == expected


@pytest.mark.parametrize(
    "flat_list, shape, expected",
    [
        ([1, 2, 3, 4], (1, 3), [[1], [2, 3, 4]]),
        ([1, 2, 3, 4], (4,), [[1, 2, 3, 4]]),
        ([1, 2, 3, 4, 5, 6], (2, 2, 2), [[1, 2], [3, 4], [5, 6]]),
    ],
)
def test_reshape_list(
    flat_list: list[int], shape: tuple[int, ...], expected: list[int]
) -> None:
    """Unit test the _reshape_list function."""
    assert _reshape_list(flat_list, shape) == expected


def test_subsample_mask_raise_value_error_if_fraction_not_a_fraction() -> None:
    with pytest.raises(ValueError, match="Fraction must be between 0 and 1"):
        _subsample_mask(np.array([True, False, True, True]), fraction=1.1)


def test_random_splitter_raises_value_error_if_fractions_do_not_sum_to_one() -> None:
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must sum to 1."):
        RandomSplitter(fractions=[0.7, 0.3, 0.1])


def test_random_splitter_raises_value_error_if_fraction_below_zero() -> None:
    """Test that RandomSplitter raises ValueError if fractions do not sum to 1."""
    with pytest.raises(ValueError, match="Fractions must be positive numbers."):
        RandomSplitter(fractions=[0.7, 0.4, -0.1])


def test_random_splitter_splits_length(dataset_empty: Dataset) -> None:
    """Test that RandomSplitter splits the dataset into the correct number of slices."""
    fractions = [0.8, 0.2]
    splitter = RandomSplitter(fractions)
    subsets = splitter.split(dataset_empty)
    assert len(subsets) == len(fractions)


def test_quantile_splitter_raises_value_error_if_quantile_not_a_fraction() -> None:
    """Test that QuantileSplitter raises ValueError if the quantile is not a value
    between 0 and 1."""
    with pytest.raises(ValueError, match="Quantile must lie between 0 and 1."):
        QuantileSplitter(quantile=1.1, fraction=0.8)


def test_quantile_splitter_raises_value_error_if_fraction_not_a_fraction() -> None:
    """Test that QuantileSplitter raises ValueError if the quantile is not a value
    between 0 and 1."""
    with pytest.raises(ValueError, match="Fraction must lie between 0 and 1."):
        QuantileSplitter(quantile=0.75, fraction=1.1)


def test_quantile_splitter_creates_two_subsets(dataset_empty: Dataset) -> None:
    """Test that QuantileSplitter splits the dataset into two slices."""
    quantile = 0.75
    fraction = 0.5
    splitter = QuantileSplitter(quantile, fraction)
    subsets = splitter.split(dataset_empty, target="DMS Score")
    assert len(subsets) == 2


def test_quantile_splitter_test_slice_target_values_exceed_all_train_targets(
    dataset_with_varying_targets: Dataset,
) -> None:
    """Test that test slice contains the hit variants — values that exceed the
    quantile threshold and therefore the maximum value in the train slice."""
    import numpy as np

    target = "DMS Score"
    quantile = 0.75
    fraction = 0.5
    splitter = QuantileSplitter(quantile, fraction, random_state=42)
    subsets = splitter.split(dataset_with_varying_targets, target=target)

    train_slice, test_slice = subsets.slices
    for assay, train_assay_slice, test_assay_slice in zip(
        dataset_with_varying_targets.assays,
        train_slice.assays,
        test_slice.assays,
        strict=True,
    ):
        target_idx = [f.name for f in assay.fields].index(target)
        all_values = np.array([r[target_idx] for r in assay.records], dtype=float)
        train_mask = np.asarray(train_assay_slice.records, dtype=bool)
        test_mask = np.asarray(test_assay_slice.records, dtype=bool)
        train_values = all_values[train_mask]
        test_values = all_values[test_mask]
        threshold = float(pl.Series(all_values).quantile(quantile))
        n_hits = int(np.sum(all_values > threshold) * (1 - fraction))
        train_max = float(train_values.max())
        assert int(np.sum(test_values > train_max)) >= n_hits


@pytest.fixture
def dataset_with_missing_values() -> Dataset:
    seq1 = Sequence(
        name="one",
        value=Seq("A"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.AA,
    )
    seq2 = Sequence(
        name="two",
        value=Seq("C"),
        type=SequenceType.STANDARD,
        alphabet=SequenceAlphabet.AA,
    )
    return Dataset(
        name="foo",
        sequences=[seq1, seq2],
        assays=[
            Assay(
                fields=[
                    Field(name="sequence"),
                    Field(name="complete"),
                    Field(name="incomplete"),
                ],
                name="bar",
                records=[
                    (seq1, 1, None),
                    (seq2, 1, 2),
                ],
            )
        ],
    )


@pytest.mark.parametrize(
    "targets,expected",
    [(["complete"], {"A", "C"}), (["incomplete"], {"C"})],
)
def test_unique_sequences_for_targets_with_none_values(
    targets, expected, dataset_with_missing_values
):
    assert {
        str(s)
        for s in _unique_sequences_for_targets(dataset_with_missing_values, targets)
    } == expected


def test_unique_sequences_for_targets_all_sequences(dataset_with_missing_values):
    dataset = dataset_with_missing_values
    result = {str(s) for s in _unique_sequences_for_targets(dataset)}
    expected = {str(r[0].value) for r in dataset.assays[0].records}
    assert result == expected


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_empty_assay",
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    "fractions",
    [
        [0.5, 0.5],  # Each split with one record
        [0.9, 0.1],  # One split with no records
    ],
)
def test_random_splitter_splits_in_dataset(
    dataset: Dataset, fractions: list[float]
) -> None:
    """Test that RandomSplitter splits the dataset into the correct number of slices."""
    splitter = RandomSplitter(fractions)
    subsets = splitter.split(dataset)
    for i, split in enumerate(subsets):
        assert split in dataset, f"Split {i + 1} not in original dataset."


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
def test_random_splitter_splits_are_disjoint(dataset: Dataset) -> None:
    """Test that RandomSplitter splits are disjoint."""
    fractions = [0.5, 0.5]
    splitter = RandomSplitter(fractions)
    split_first, split_second = tuple(splitter.split(dataset=dataset))
    assert split_first not in split_second and split_second not in split_first


def test_kfold_splitter_raises_value_error_if_n_splits_below_two() -> None:
    """Test that KFoldSplitter raises ValueError if n_splits is below 2."""
    with pytest.raises(ValueError, match="Number of splits must be at least 2."):
        KFoldSplitter(n_splits=1)


@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_splitter_splits_length(dataset_empty: Dataset, n_splits: int) -> None:
    """Test that KFoldSplitter splits the dataset into the correct number of folds."""
    splitter = KFoldSplitter(n_splits=n_splits)
    superset = splitter.split(dataset_empty)
    assert len(superset) == n_splits


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_empty_assay",
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_splitter_splits_in_dataset(dataset: Dataset, n_splits: int) -> None:
    """Test that KFoldSplitter splits the dataset into the correct number of slices."""
    splitter = KFoldSplitter(n_splits=n_splits)
    superset = splitter.split(dataset)
    for i, split in enumerate(superset):
        assert split in dataset, f"Split {i + 1} not in original dataset."


def test_kfold_splitter_splits_are_disjoint(dataset_with_assays: Dataset) -> None:
    """Test that KFoldSplitter splits are disjoint."""
    splitter = KFoldSplitter(n_splits=2)
    superset = splitter.split(dataset_with_assays)
    split_first, split_second = tuple(superset)
    assert split_first not in split_second
    assert split_second not in split_first


@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_splitter_splits_contain_all_records(
    dataset_with_assays: Dataset, n_splits: int
) -> None:
    """Test that KFoldSplitter splits contain all records from the original dataset."""
    splitter = KFoldSplitter(n_splits=n_splits)
    subsets = splitter.split(dataset_with_assays)
    dataset_with_all_splits = functools.reduce(lambda d1, d2: d1 | d2, subsets)
    # Using a dataframe comparison here as the dataset reconstructed from the
    # folds will have the records spread over multiple assays
    pl.testing.assert_frame_equal(
        dataset_with_assays.to_df(),
        dataset_with_all_splits.to_df(),  # noqa
        check_dtypes=False,
        check_column_order=False,
    )


@pytest.mark.parametrize(
    "splitter",
    [
        RandomSplitter(fractions=[0.5, 0.5]),
        KFoldSplitter(n_splits=2),
    ],
)
def test_splitter_splits_with_targets_columns(
    dataset_with_assay: Dataset,
    splitter: RandomSplitter | KFoldSplitter,
) -> None:
    """A split with targets should contain the target and sequence columns."""
    expected_field_names = ["sequence", "DMS Score"]
    splits = splitter.split(dataset_with_assay, targets=["DMS Score"])
    assays = [assay for split in splits for assay in split.assays]
    assert all(
        expected_field_names == [e.name for e in assay.fields] for assay in assays
    )


@pytest.mark.parametrize(
    "splitter",
    [
        RandomSplitter(fractions=[0.5, 0.5]),
        KFoldSplitter(n_splits=2),
    ],
    ids=lambda splitter: splitter.__class__.__name__,
)
def test_splitter_splits_share_no_sequences(
    dataset_with_assays: Dataset,
    splitter: RandomSplitter | KFoldSplitter,
) -> None:
    """Different splits must never contain the same sequences."""
    train, valid = splitter.split(dataset_with_assays, targets=["DMS Score"])
    train_seq = {record[0].value for assay in train.assays for record in assay.records}
    valid_seq = {record[0].value for assay in valid.assays for record in assay.records}
    assert train_seq.intersection(valid_seq) == set()


@pytest.mark.parametrize(
    "splitter",
    [
        RandomSplitter(fractions=[0.5, 0.5]),
        KFoldSplitter(n_splits=2),
    ],
)
def test_splitter_splits_with_target_not_in_all_assays(
    dataset_with_assays: Dataset,
    splitter: RandomSplitter | KFoldSplitter,
) -> None:
    """If a target is not in all assays, the assays without the targets are empty."""
    splits = splitter.split(dataset_with_assays, targets=["stability"])
    assays = [assay for split in splits for assay in split.assays]
    assert all(
        assay.is_empty()
        for assay in assays
        if Field(name="stability") not in assay.fields
    )
    # Make sure we do not lose all data
    assert any(not split.to_df().is_empty() for split in splits)


def test_quantile_splitter_splits_with_target_not_in_all_assays(
    dataset_with_assays: Dataset,
) -> None:
    """If a target is not in all assays, the assays without the targets are empty."""
    splitter = QuantileSplitter(quantile=0.75, fraction=0.5)
    splits = splitter.split(dataset_with_assays, target="stability")
    assays = [assay for split in splits for assay in split.assays]
    assert all(
        assay.is_empty()
        for assay in assays
        if Field(name="stability") not in assay.fields
    )
    # Make sure we do not lose all data
    assert any(not split.to_df().is_empty() for split in splits)


def test_kfold_quantile_splitter_raises_value_error_if_n_splits_below_two() -> None:
    """Test that KFoldQuantileSplitter raises ValueError if n_splits is below 2."""
    with pytest.raises(ValueError, match="Number of splits must be at least 2."):
        KFoldQuantileSplitter(quantile=0.75, n_splits=1)


@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_quantile_splitter_splits_length(
    dataset_empty: Dataset, n_splits: int
) -> None:
    """Test that KFoldQuantileSplitter splits the dataset into the correct number of
    folds."""
    splitter = KFoldQuantileSplitter(quantile=0.75, n_splits=n_splits)
    subsets = splitter.split(dataset_empty, target="DMS Score")
    assert len(subsets["train_folds"]) == n_splits
    assert len(subsets["test_folds"]) == n_splits


@pytest.mark.parametrize(
    "dataset",
    [
        "dataset_with_single_assay",
        "dataset_with_multiple_assays",
    ],
    indirect=True,
)
@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_quantile_splitter_splits_in_dataset(
    dataset: Dataset, n_splits: int
) -> None:
    """Test that KFoldQuantileSplitter splits the dataset into the correct number of
    slices."""
    target = "DMS Score"
    splitter = KFoldQuantileSplitter(quantile=0.75, n_splits=n_splits)
    subsets = splitter.split(dataset, target=target)

    # The splits only retain the sequence and target columns, so we compare the
    # (sequence, target value) records against those of the original dataset.
    original = set()
    for assay in dataset.assays:
        target_idx = [f.name for f in assay.fields].index(target)
        for record in assay.records:
            original.add((str(record[0].value), record[target_idx]))

    for key in ("train_folds", "test_folds"):
        for split in subsets[key]:
            for assay in split.assays:
                for record in assay.records:
                    assert (str(record[0].value), record[1]) in original


def test_kfold_quantile_splitter_splits_are_disjoint(
    dataset_with_assays: Dataset,
) -> None:
    """Test that KFoldQuantileSplitter splits are disjoint."""
    splitter = KFoldQuantileSplitter(quantile=0.75, n_splits=2)
    subsets = splitter.split(dataset_with_assays, target="DMS Score")
    for train, test in zip(subsets["train_folds"], subsets["test_folds"], strict=True):
        assert train not in test
        assert test not in train


@pytest.mark.parametrize("n_splits", [2, 3, 5])
def test_kfold_quantile_splitter_splits_contain_all_records(
    dataset_with_assays: Dataset, n_splits: int
) -> None:
    """Test that KFoldQuantileSplitter splits contain all records from the original
    dataset."""
    target = "DMS Score"
    splitter = KFoldQuantileSplitter(
        quantile=0.75, n_splits=n_splits, shuffle=True, random_state=42
    )
    subsets = splitter.split(dataset_with_assays, target=target)

    def records_of(subset: Subsets) -> set[tuple[str, float]]:
        return {
            (str(record[0].value), record[1])
            for split in subset
            for assay in split.assays
            for record in assay.records
        }

    covered = records_of(subsets["train_folds"]) | records_of(subsets["test_folds"])

    original = set()
    for assay in dataset_with_assays.assays:
        target_idx = [f.name for f in assay.fields].index(target)
        for record in assay.records:
            original.add((str(record[0].value), record[target_idx]))

    assert covered == original


def test_kfold_quantile_splitter_test_folds_contain_hit_variants(
    dataset_with_varying_targets: Dataset,
) -> None:
    """Test that test folds contains the hit variants — values that exceed the
    quantile threshold and therefore the maximum value in the corresponding
    training folds."""
    target = "DMS Score"
    quantile = 0.75
    splitter = KFoldQuantileSplitter(
        quantile=quantile, n_splits=2, shuffle=True, random_state=42
    )
    subsets = splitter.split(dataset_with_varying_targets, target=target)

    for train_slice, test_slice in zip(
        subsets.slices["train_folds"], subsets.slices["test_folds"], strict=True
    ):
        for assay, train_assay_slice, test_assay_slice in zip(
            dataset_with_varying_targets.assays,
            train_slice.assays,
            test_slice.assays,
            strict=True,
        ):
            if not test_assay_slice.columns:
                continue  # Assay without the target is empty.
            target_idx = [f.name for f in assay.fields].index(target)
            all_values = np.array([r[target_idx] for r in assay.records], dtype=float)
            threshold = float(np.quantile(all_values, quantile))
            train_mask = np.asarray(train_assay_slice.records, dtype=bool)
            test_mask = np.asarray(test_assay_slice.records, dtype=bool)
            train_values = all_values[train_mask]
            hits = all_values[test_mask][all_values[test_mask] > threshold]
            if train_values.size and hits.size:
                assert hits.min() > train_values.max()


def test_kfold_quantile_splitter_splits_with_target_columns(
    dataset_with_assay: Dataset,
) -> None:
    """A split with targets should contain the target and sequence columns."""
    expected_field_names = ["sequence", "DMS Score"]
    splitter = KFoldQuantileSplitter(quantile=0.75, n_splits=2)
    subsets = splitter.split(dataset_with_assay, target="DMS Score")
    assays = [
        assay
        for key in ("train_folds", "test_folds")
        for split in subsets[key]
        for assay in split.assays
    ]
    assert all(
        expected_field_names == [e.name for e in assay.fields]
        for assay in assays
        if assay.fields
    )


def test_kfold_quantile_splitter_splits_with_target_not_in_all_assays(
    dataset_with_assays: Dataset,
) -> None:
    """If a target is not in all assays, the assays without the targets are empty."""
    splitter = KFoldQuantileSplitter(quantile=0.75, n_splits=2)
    subsets = splitter.split(dataset_with_assays, target="stability")
    splits = [split for key in ("train_folds", "test_folds") for split in subsets[key]]
    assays = [assay for split in splits for assay in split.assays]
    assert all(
        assay.is_empty()
        for assay in assays
        if Field(name="stability") not in assay.fields
    )
    # Make sure we do not lose all data
    assert any(not split.to_df().is_empty() for split in splits)


def test_random_splitter_combining_split_targets(dataset_with_assays: Dataset) -> None:
    """Test that different splits for different targets can be combined."""
    subsets = Subsets(dataset=dataset_with_assays)

    splitter = RandomSplitter(fractions=[0.5, 0.5])
    subsets.update(
        random_dms_score=splitter.split(dataset_with_assays, targets=["DMS Score"])
    )
    subsets.update(
        random_stability=splitter.split(dataset_with_assays, targets=["stability"])
    )

    assays = [assay for split in subsets["random_dms_score"] for assay in split.assays]
    expected_fields = [Field(name="sequence"), Field(name="DMS Score")]
    assert all(expected_fields == assay.fields for assay in assays if assay.fields)

    assays = [assay for split in subsets["random_stability"] for assay in split.assays]
    expected_fields = [Field(name="sequence"), Field(name="stability")]
    assert all(expected_fields == assay.fields for assay in assays if assay.fields)


def test_splitters_combining_split_strategies(dataset_with_assays: Dataset) -> None:
    """Test that different split strategies can be combined."""
    subsets = Subsets(dataset=dataset_with_assays)

    random_splitter = RandomSplitter(fractions=[0.5, 0.5])
    subsets.update(random=random_splitter.split(dataset_with_assays))

    kfold_splitter = KFoldSplitter(n_splits=2)
    subsets.update(kfold=kfold_splitter.split(dataset_with_assays))

    assert "random" in subsets.slices and len(subsets.slices["random"]) == 2
    assert "kfold" in subsets.slices and len(subsets.slices["kfold"]) == 2


def test_predefined_splitter_returns_in_user_defined_order(
    dataset_with_assay_predefined_split: Dataset,
) -> None:
    """
    With required split_order, verify that returned subsets
    follow the exact user-provided order.
    """
    splitter = PredefinedSplitter(
        split_column="split", split_order=["train", "val", "test"]
    )
    subsets = splitter.split(dataset_with_assay_predefined_split)

    assert len(subsets) == 3

    # fixture is train, test, val on purpose
    # fixture sequences order: train="ACGT", test="TGCA", val="AAAA"
    expected_sequences = ["ACGT", "AAAA", "TGCA"]
    for subset, expected_seq in zip(subsets, expected_sequences, strict=False):
        records = [r for assay in subset.assays for r in assay.records]
        assert len(records) == 1
        assert str(records[0][0].value) == expected_seq


def test_predefined_splitter_strict_unknown_key_raises(
    dataset_with_assay_predefined_split: Dataset,
) -> None:
    """
    If the dataset contains a split value not present in split_order, raise.
    Example: dataset has 'val', but split_order is ['train', 'test'] only.
    """
    splitter = PredefinedSplitter(split_column="split", split_order=["train", "test"])

    with pytest.raises(
        ValueError, match=r"Found split values in dataset not in split_order"
    ):
        splitter.split(dataset_with_assay_predefined_split)


def test_predefined_splitter_strict_missing_key_raises(
    dataset_with_assay_predefined_split: Dataset,
) -> None:
    """
    If split_order requires a value missing in the dataset, raise.
    Example: split_order requires 'holdout' but data has only train/val/test.
    """
    splitter = PredefinedSplitter(
        split_column="split", split_order=["train", "val", "test", "holdout"]
    )

    with pytest.raises(ValueError, match=r"Dataset is missing required split values"):
        splitter.split(dataset_with_assay_predefined_split)


def test_predefined_splitter_with_targets_in_assay(
    dataset_with_assay_predefined_split: Dataset,
) -> None:
    """
    Verify that when targets exist, slices include
    the sequence and the requested target.
    """
    splitter = PredefinedSplitter(
        split_column="split", split_order=["train", "val", "test"]
    )
    subsets = splitter.split(dataset_with_assay_predefined_split, targets=["target1"])

    for subset in subsets:
        for assay in subset.assays:
            if not assay.is_empty():
                field_names = [f.name for f in assay.fields]
                assert "sequence" in field_names
                assert "target1" in field_names


def test_predefined_splitter_raises_on_sequence_overlap(
    dataset_with_duplicates_sequences_across_splits: Dataset,
) -> None:
    """
    Verifies the exact ValueError message when the
    same sequence appears in multiple splits.
    """
    splitter = PredefinedSplitter(split_column="split", split_order=["train", "test"])

    with pytest.raises(ValueError) as exc:
        splitter.split(
            dataset_with_duplicates_sequences_across_splits, targets=["DMS Score"]
        )

    msg = str(exc.value)
    assert "Sequence overlap detected" in msg
    assert "'train'" in msg and "'test'" in msg
    assert "Found 1 overlapping sequence(s)." in msg  # only seq1 overlaps


def test_predefined_splitter_missing_split_column_raises_missing_split_values(
    dataset_with_assay: Dataset,  # fixture without "split" column
) -> None:
    """
    When the split column is absent from all the assays, should raise a ValueError
    """
    splitter = PredefinedSplitter(
        split_column="split", split_order=["train", "test", "fake"]
    )

    with pytest.raises(ValueError, match=r"not found in any assay of the dataset"):
        splitter.split(dataset_with_assay, targets=["DMS Score"])


def test_predefined_splitter_targets_missing_in_assay_sets_empty_fields(
    dataset_two_assays_with_split_and_mixed_targets: Dataset,
) -> None:
    """
    If a requested target is not present in an assay, its slice should expose
    no fields (empty fields list).
    """
    splitter = PredefinedSplitter(split_column="split", split_order=["train", "test"])
    subsets = splitter.split(
        dataset_two_assays_with_split_and_mixed_targets, targets=["target_a"]
    )

    assert len(subsets) == 2

    for subset in subsets:
        assert len(subset.assays) == 2
        slice_a = subset.assays[0]  # assay_a has target_a
        slice_b = subset.assays[1]  # assay_b does NOT have target_a

        fields_a = [f.name for f in slice_a.fields]
        fields_b = [f.name for f in slice_b.fields]

        # Assay A includes sequence + target_a (split is a non-target, so not included)
        assert "sequence" in fields_a
        assert "target_a" in fields_a

        # Assay B should be empty
        assert fields_b == []


def test_predefined_splitter_assay_missing_split_column_yields_empty_view(
    dataset_mixed_split_presence: Dataset,
) -> None:
    """
    For assays missing the split column, the slice should be empty:
    """
    splitter = PredefinedSplitter(split_column="split", split_order=["train", "test"])
    subsets = splitter.split(dataset_mixed_split_presence, targets=["DMS Score"])

    assert len(subsets) == 2

    for subset in subsets:
        assert len(subset.assays) == 2

        slice_missing = subset.assays[0]
        slice_present = subset.assays[1]

        assert slice_missing.is_empty()
        assert len(slice_missing.records) == 0
        assert len(slice_missing.fields) == 0

        assert not slice_present.is_empty()
        assert len(slice_present.records) == 1
        present_field_names = [f.name for f in slice_present.fields]
        assert "sequence" in present_field_names
