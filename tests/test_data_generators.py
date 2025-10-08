from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from proteingym.base.__main__ import app
from proteingym.base.data_generators import (
    AaPks,
    adjust_target_with_two_dummy_features,
    charge_ladder_dataset,
    charge_mutations,
    charge_random_dataset,
    peptide_charge,
)


def test_dummy_data_n_rows() -> None:
    ladder = charge_ladder_dataset(n_rows=5, seq_len=10)

    assert len(ladder) <= 5


def test_dummy_data_seq_len() -> None:
    ladder = charge_ladder_dataset(n_rows=5, seq_len=10)

    for row in ladder.iter_rows(named=True):
        assert len(row["sequence"]) == 10


def test_dummy_data_with_extra_features() -> None:
    """func:adjust_target_with_two_dummy_features adds the 'foo' and 'bar' columns."""
    expected_columns = ["foo", "bar"]

    ladder = charge_ladder_dataset(n_rows=5, seq_len=10)
    ladder = ladder.pipe(adjust_target_with_two_dummy_features, target="charge")

    assert set(expected_columns).issubset(set(ladder.columns))


def test_peptide_charge_basic() -> None:
    charge = peptide_charge("ACDEFG", ph=7.0)
    assert isinstance(charge, float)


def test_peptide_charge_different_ph() -> None:
    seq = "KRHED"
    charge_ph7 = peptide_charge(seq, ph=7.0)
    charge_ph1 = peptide_charge(seq, ph=1.0)
    charge_ph14 = peptide_charge(seq, ph=14.0)

    assert charge_ph1 != charge_ph7 != charge_ph14


def test_peptide_charge_amide() -> None:
    seq = "ACDEFG"
    charge_normal = peptide_charge(seq, amide=False)
    charge_amide = peptide_charge(seq, amide=True)

    assert charge_normal != charge_amide


def test_peptide_charge_invalid_sequence() -> None:
    with pytest.raises(
        ValueError, match="sequence does not match aa-sequence regular expression"
    ):
        peptide_charge("INVALIDSEQ123")


def test_peptide_charge_with_gaps() -> None:
    charge = peptide_charge("AC-DEF-G")
    assert isinstance(charge, float)


def test_charge_random_dataset_basic() -> None:
    df = charge_random_dataset(n_rows=10, min_seq_len=50)

    assert len(df) == 10
    assert "sequence" in df.columns
    assert "charge" in df.columns
    assert all(len(seq) == 50 for seq in df["sequence"])


def test_charge_random_dataset_variable_length() -> None:
    df = charge_random_dataset(n_rows=20, min_seq_len=10, max_seq_len=20)

    assert len(df) == 20
    assert all(10 <= len(seq) <= 20 for seq in df["sequence"])


def test_charge_random_dataset_max_seq_len_none() -> None:
    df = charge_random_dataset(n_rows=5, min_seq_len=15, max_seq_len=None)

    assert len(df) == 5
    assert all(len(seq) == 15 for seq in df["sequence"])


def test_charge_random_dataset_invalid_seq_len() -> None:
    with pytest.raises(
        RuntimeError, match="max_seq_len.*should not be smaller than min_seq_len"
    ):
        charge_random_dataset(n_rows=5, min_seq_len=20, max_seq_len=10)


def test_charge_mutations_basic() -> None:
    original = "ACDEFGHIKLMNPQRSTVWY"
    mutated = charge_mutations(original, n=5)

    assert len(mutated) == len(original)
    assert isinstance(mutated, str)


def test_charge_mutations_no_mutations() -> None:
    original = "ACDEFG"
    mutated = charge_mutations(original, n=0)

    assert mutated == original


def test_charge_mutations_all_positions() -> None:
    original = "AAAAA"
    mutated = charge_mutations(original, n=5)

    assert len(mutated) == 5
    assert mutated != original


def test_aa_pks_init_default() -> None:
    aa_pks = AaPks()

    assert "K" in aa_pks.positive
    assert "D" in aa_pks.negative
    assert aa_pks.negative["Cterm"] == 2.15


def test_aa_pks_init_amide() -> None:
    aa_pks = AaPks(amide=True)

    assert aa_pks.negative["Cterm"] == 15.0


def test_aa_pks_positive_residues() -> None:
    aa_pks = AaPks()
    pos_residues = aa_pks.positive_residues

    assert "K" in pos_residues
    assert "R" in pos_residues
    assert "Nterm" not in pos_residues


def test_aa_pks_negative_residues() -> None:
    aa_pks = AaPks()
    neg_residues = aa_pks.negative_residues

    assert "D" in neg_residues
    assert "E" in neg_residues
    assert "Cterm" not in neg_residues


def test_aa_pks_getitem() -> None:
    aa_pks = AaPks()

    assert aa_pks["K"] == 10.67
    assert aa_pks["D"] == 3.71
    assert aa_pks["X"] == 0  # Non-existent residue


def test_adjust_target_custom_feature_names() -> None:
    df = pl.DataFrame({"target": [1.0, 2.0, 3.0]})
    result = adjust_target_with_two_dummy_features(
        df, "target", feature_names=["custom1", "custom2"]
    )

    assert "custom1" in result.columns
    assert "custom2" in result.columns


def test_adjust_target_invalid_feature_names() -> None:
    df = pl.DataFrame({"target": [1.0, 2.0, 3.0]})

    with pytest.raises(ValueError, match="Expecting two feature names"):
        adjust_target_with_two_dummy_features(df, "target", feature_names=["one"])

    with pytest.raises(ValueError, match="Expecting two feature names"):
        adjust_target_with_two_dummy_features(
            df, "target", feature_names=["one", "two", "three"]
        )


@pytest.fixture
def runner() -> CliRunner:
    """Test runner for CLI commands."""
    return CliRunner()


def test_generate_data_cli_command(runner: CliRunner, tmp_path: Path) -> None:
    """Test the generate-data CLI command from __main__.py."""
    result = runner.invoke(
        app,
        [
            "generate-data",
            "feature1",
            "feature2",
            "--n-rows",
            "10",
            "--sequence-length",
            "20",
        ],
    )

    assert result.exit_code == 0

    df = pl.read_csv(result.output.encode())
    assert len(df) <= 10  # Remove the duplicates from randomly generated sequences.
    assert "sequence" in df.columns
    assert "charge" in df.columns
    assert "feature1" in df.columns
    assert "feature2" in df.columns
    assert all(len(seq) == 20 for seq in df["sequence"])
