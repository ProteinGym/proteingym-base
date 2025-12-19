import random
import re
from collections import Counter
from typing import Optional

import numpy as np
import polars as pl

AA_ALPHABET = list("ACDEFGHIKLMNPQRSTVWY")
AA_GAP_PATTERN = re.compile("^[-ACDEFGHIKLMNPQRSTVWY]+$", flags=re.IGNORECASE)


class AaPks:
    def __init__(self, amide: bool = False):
        self.positive = {"Nterm": 9.38, "K": 10.67, "R": 12.10, "H": 6.04}
        self.negative = {
            "D": 3.71,
            "E": 4.15,
            "C": 8.14,
            "Y": 10.10,
            "Cterm": 15.0 if amide else 2.15,
        }

    @property
    def positive_residues(self) -> dict[str, float]:
        return {a: p for a, p in self.positive.items() if len(a) == 1}

    @property
    def negative_residues(self) -> dict[str, float]:
        return {a: p for a, p in self.negative.items() if len(a) == 1}

    def __getitem__(self, item) -> float:
        return self.positive.get(item, self.negative.get(item, 0))


def peptide_charge(seq: str, ph: float = 7.0, amide: bool = False) -> float:
    """Calculate charge of a single sequence.

    The method used is first described by Bjellqvist. In the case of amidation,
    the value for the  'Cterm' pKa is 15 (and Cterm is added to the pos_pks
    dictionary. The pKa scale is extracted from: http://www.hbcpnetbase.com/ (CRC
    Handbook of Chemistry and Physics, 96th ed). **pos_pks** = {'Nterm': 9.38,
    'K': 10.67, 'R': 12.10, 'H': 6.04} **neg_pks** = {'Cterm': 2.15, 'D': 3.71,
    'E': 4.15, 'C': 8.14, 'Y': 10.10}

    Adopted from https://github.com/alexarnimueller/modlAMP

    Args:
        seq: peptide sequence.
        ph: pH at which to calculate peptide charge.
        amide: whether the sequences have an amidated C-terminus.

    Returns:
        float:  value of the global charge of the sequence
    """

    if not AA_GAP_PATTERN.match(seq):
        raise ValueError(
            "sequence does not match aa-sequence regular expression %s" % seq
        )
    aa_pks = AaPks(amide)
    aa_content = Counter(seq)
    aa_content["Nterm"] = 1
    aa_content["Cterm"] = 1
    pos_charge = 0.0
    for aa, pk in aa_pks.positive.items():
        c_r = 10 ** (pk - ph)
        partial_charge = c_r / (c_r + 1.0)
        pos_charge += aa_content[aa] * partial_charge
    neg_charge = 0.0
    for aa, pk in aa_pks.negative.items():
        c_r = 10 ** (ph - pk)
        partial_charge = c_r / (c_r + 1.0)
        neg_charge += aa_content[aa] * partial_charge
    return pos_charge - neg_charge


def _generate_sequence(seq_len: int) -> str:
    return "".join(random.choices(AA_ALPHABET, k=seq_len))


def charge_random_dataset(
    n_rows: int = 200, min_seq_len: int = 200, max_seq_len: Optional[int] = None
) -> pl.DataFrame:
    if max_seq_len is None:
        max_seq_len = min_seq_len

    if max_seq_len < min_seq_len:
        raise RuntimeError(
            f"max_seq_len ({max_seq_len}) should not be smaller than min_seq_len "
            f"({min_seq_len})."
        )
    sequences = [
        _generate_sequence(random.randint(min_seq_len, max_seq_len))
        for _ in range(n_rows)
    ]
    charge = [peptide_charge(seq) for seq in sequences]
    return pl.DataFrame({"sequence": sequences, "charge": charge})


def charge_mutations(sequence: str, n: int) -> str:
    seq = list(sequence)
    aa_pks = AaPks()
    charged = list(aa_pks.positive_residues) + list(aa_pks.negative_residues)
    for _ in range(n):
        pos = random.randint(0, len(sequence) - 1)
        seq[pos] = random.choice(charged)
    return "".join(seq)


def charge_ladder_dataset(n_rows: int = 200, seq_len: int = 20) -> pl.DataFrame:
    parent = _generate_sequence(seq_len)

    sequences = set()
    while len(sequences) < n_rows:
        sequences.add(charge_mutations(parent, random.randint(0, seq_len)))

    charge = [peptide_charge(seq) for seq in sequences]
    return pl.DataFrame({"sequence": list(sequences), "charge": charge})


def adjust_target_with_two_dummy_features(
    df: pl.DataFrame, target: str, *, feature_names: list[str] | None = None
) -> pl.DataFrame:
    """Add two dummy features to a DataFrame and adjust the target column based on them.

    This function adds two new features to the input DataFrame:
    - A continuous feature with random values between 0-100
    - A categorical feature with random choices between "a" and "b"

    The target variable is then transformed using these new features according to:
    target_new = target_old * (2 if bar=="a" else -1) - foo/50

    Args:
        df: Input DataFrame containing the target column.
        target: Name of the target column to adjust.
        feature_names: Names for the two new features.
            Must contain exactly 2 names. Defaults to ["foo", "bar"] if None.

    Returns:
        pl.DataFrame: DataFrame with two new features added and
        the target variable adjusted.

    Raises:
        ValueError: If feature_names doesn't contain exactly 2 names.

    Examples:
    >>> df = pl.DataFrame({'target': [10, 20, 30]})
    >>> result = adjust_target_with_two_dummy_features(df, 'target')
    >>> result.columns
    ['target', 'foo', 'bar']
    """
    feature_names = feature_names or ("foo", "bar")

    if len(feature_names) != 2:
        raise ValueError(f"Expecting two feature names: {feature_names}")

    return df.with_columns(
        [
            (pl.lit(np.random.random(len(df)) * 100)).alias(feature_names[0]),
            (pl.lit(np.random.choice(["a", "b"], len(df)))).alias(feature_names[1]),
        ]
    ).with_columns(
        (
            pl.col(target)
            * pl.when(pl.col(feature_names[1]) == "a").then(2).otherwise(-1)
            - pl.col(feature_names[0]) / 50
        ).alias(target)
    )
