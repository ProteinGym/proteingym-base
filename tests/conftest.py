import biotite.sequence.io.fasta as fasta
import polars as pl
import pytest
from Bio.Seq import Seq
from biotite.structure import AtomArray

from proteingym.base.assay import SEQUENCE, Assay, AssayRaw, Field
from proteingym.base.dataset import AssaySlice, Dataset, DatasetSlice, Subsets
from proteingym.base.msa import MSA
from proteingym.base.publication import Publication
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType
from proteingym.base.structure import Structure


@pytest.fixture
def dataset_empty() -> Dataset:
    """An empty dataset."""
    dataset = Dataset(
        name="dataset_empty",
        description="An empty dataset for testing purposes.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assay_empty() -> Dataset:
    """A dataset containing an empty assay."""
    assay = Assay(
        name="empty_assay",
        records=[],
        fields=[Field(name="sequence"), Field(name="DMS Score")],
    )
    dataset = Dataset(
        name="dataset_with_empty_assay",
        description="A dataset containing an empty assay.",
        assay_variables=[],
        assay_targets=[Field(name="DMS Score")],
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assay() -> Dataset:
    """A dataset containing a single assay."""
    sequence1 = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="seq2",
        value=Seq("GFEDCA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assay = Assay(
        name="assay1",
        records=[
            (sequence1, 1.0, 1.5),
            (sequence2, 2.0, 2.5),
        ],
        fields=[
            Field(name="sequence"),
            Field(name="DMS Score"),
            Field(name="stability"),
        ],
    )
    dataset = Dataset(
        name="dataset_with_single_assay",
        description="A dataset containing a single assay.",
        assay_variables=[Field(name="var1", description="A test variable")],
        assay_targets=[
            Field(name="DMS Score", description="The DMS score"),
            Field(name="stability", description="The resistance to temperature"),
        ],
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assay_raw() -> Dataset:
    """A dataset containing a single assay and its raw assay."""
    sequence1 = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="seq2",
        value=Seq("GFEDCA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assay = Assay(
        name="assay1",
        records=[
            (sequence1, 1.0, 1.5),
            (sequence2, 2.0, 2.5),
        ],
        fields=[
            Field(name="sequence"),
            Field(name="DMS Score"),
            Field(name="stability"),
        ],
    )
    assay_raw = AssayRaw(
        name="assay1",
        records=[
            (0.3,),
            (0.9,),
        ],
        fields=[Field(name="OD", description="Optical Density at 600nm")],
    )
    dataset = Dataset(
        name="dataset_with_single_raw_assay",
        description="A dataset containing a single assay and its raw assay.",
        assay_variables=[Field(name="var1", description="A test variable")],
        assay_targets=[
            Field(name="DMS Score", description="The DMS score"),
            Field(name="stability", description="The resistance to temperature"),
        ],
        assays=[assay],
        assays_raw=[assay_raw],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assays() -> Dataset:
    """A dataset containing multiple assays."""
    sequences = [
        Sequence(
            name=f"seq{i}",
            value=Seq(s),
            type=SequenceType.WILD_TYPE,
            alphabet=SequenceAlphabet.AA,
        )
        for i, s in enumerate(
            ["AA", "CC", "DD", "EE", "FF", "GG", "HH", "II", "JJ", "KK"]
        )
    ]
    assay1 = Assay(
        name="assay2",
        records=[
            (sequences[0], 1.1, 1.5),
            (sequences[0], 1.2, 1.4),  # duplicate sequence to handle that
            (sequences[1], 1.1, 1.5),
            (sequences[2], 1.1, 1.5),
            (sequences[3], 1.1, 1.5),
            (sequences[4], 1.1, 1.5),
            (sequences[5], 1.1, 1.5),
            (sequences[6], 1.1, 1.5),
            (sequences[7], 1.1, 1.5),
            (sequences[8], 1.1, 1.5),
            (sequences[9], 1.1, 1.5),
        ],
        fields=[
            Field(name="sequence"),
            Field(name="DMS Score"),
            Field(name="stability"),
        ],
    )
    assay2 = Assay(
        name="assay3",
        records=[
            (sequences[0], 1.0),
            (sequences[1], 1.0),
            (sequences[2], 1.0),
            (sequences[3], 1.0),
            (sequences[4], 1.0),
            (sequences[5], 1.0),
            (sequences[6], 1.0),
            (sequences[7], 1.0),
            (sequences[8], 1.0),
            (sequences[9], 1.0),
        ],
        fields=[Field(name="sequence"), Field(name="DMS Score")],
    )
    dataset = Dataset(
        name="dataset_with_multiple_assays",
        description="A dataset containing multiple assays.",
        assay_variables=[Field(name="var1", description="A test variable")],
        assay_targets=[
            Field(name="DMS Score", description="The DMS score"),
            Field(name="stability", description="The resistance to temperature"),
        ],
        assays=[assay1, assay2],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_varying_targets() -> Dataset:
    """A dataset containing multiple assays with varied target distributions."""
    sequences = [
        Sequence(
            name=f"seq{i}",
            value=Seq(s),
            type=SequenceType.WILD_TYPE,
            alphabet=SequenceAlphabet.AA,
        )
        for i, s in enumerate(
            ["AA", "CC", "DD", "EE", "FF", "GG", "HH", "II", "JJ", "KK"]
        )
    ]
    assay1 = Assay(
        name="assay2",
        records=[
            (sequences[0], 0.12, 1.83),
            (sequences[0], 0.47, 1.21),  # duplicate sequence to handle that
            (sequences[1], 1.05, 2.44),
            (sequences[2], -0.38, 0.67),
            (sequences[3], 2.19, 3.02),
            (sequences[4], 0.74, 1.56),
            (sequences[5], -1.12, 0.31),
            (sequences[6], 1.63, 2.78),
            (sequences[7], 0.29, 1.04),
            (sequences[8], -0.55, 1.92),
            (sequences[9], 1.87, 2.15),
        ],
        fields=[
            Field(name="sequence"),
            Field(name="DMS Score"),
            Field(name="stability"),
        ],
    )
    assay2 = Assay(
        name="assay3",
        records=[
            (sequences[0], 0.34),
            (sequences[1], 1.21),
            (sequences[2], -0.78),
            (sequences[3], 2.05),
            (sequences[4], 0.91),
            (sequences[5], -1.43),
            (sequences[6], 1.67),
            (sequences[7], 0.08),
            (sequences[8], -0.26),
            (sequences[9], 1.94),
        ],
        fields=[Field(name="sequence"), Field(name="DMS Score")],
    )
    dataset = Dataset(
        name="dataset_with_realistic_assays",
        description="A dataset containing multiple assays with varied target "
        "distributions.",
        assay_variables=[Field(name="var1", description="A test variable")],
        assay_targets=[
            Field(name="DMS Score", description="The DMS score"),
            Field(name="stability", description="The resistance to temperature"),
        ],
        assays=[assay1, assay2],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_assay_predefined_split() -> Dataset:
    """A dataset containing an assay with predefined split column."""
    sequences = [
        Sequence(
            name=f"seq{i}",
            value=Seq(s),
            type=SequenceType.WILD_TYPE,
            alphabet=SequenceAlphabet.AA,
        )
        for i, s in enumerate(["ACGT", "TGCA", "AAAA"])
    ]
    assay = Assay(
        name="test_assay",
        fields=[
            Field(name="sequence"),
            Field(name="target1"),
            Field(name="split"),
        ],
        records=[
            (sequences[0], 1.0, "train"),
            (sequences[1], 2.0, "test"),  # test before val to test ordering
            (sequences[2], 3.0, "val"),
        ],
        non_targets=["split"],
    )
    dataset = Dataset(
        name="dataset_with_predefined_split",
        description="A dataset with predefined split column.",
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_two_assays_with_split_and_mixed_targets() -> Dataset:
    """
    Two assays with split labels but different targets.
        assay A has fields: sequence, split, target_a
        assay B has fields: sequence, split, target_b
    Requesting targets=['target_a'] should return:
        assay A slice: columns include sequence + target_a
        assay B slice: columns == [] (since target_a not present)
    """
    seq1 = Sequence(
        name="s1",
        value=Seq("ACDE"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    seq2 = Sequence(
        name="s2",
        value=Seq("FGHI"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )

    assay_a = Assay(
        name="assay_a",
        fields=[Field(name="sequence"), Field(name="split"), Field(name="target_a")],
        records=[
            (seq1, "train", 1.0),
            (seq2, "test", 2.0),
        ],
        non_targets=["split"],
    )

    assay_b = Assay(
        name="assay_b",
        fields=[Field(name="sequence"), Field(name="split"), Field(name="target_b")],
        records=[
            (seq1, "train", 3.0),
            (seq2, "test", 4.0),
        ],
        non_targets=["split"],
    )

    dataset = Dataset(
        name="dataset_two_assays_with_split_and_mixed_targets",
        description="Two assays with split; targets differ per assay.",
        assays=[assay_a, assay_b],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_mixed_split_presence() -> Dataset:
    """
    Two assays, where the first one contains the split non-target and
    the second does not
    """

    seq1 = Sequence(
        name="s1",
        value=Seq("AAAA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    seq2 = Sequence(
        name="s2",
        value=Seq("BBBB"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )

    assay_without_split = Assay(
        name="assay_no_split",
        fields=[Field(name="sequence"), Field(name="DMS Score")],
        records=[
            (seq1, 0.1),
            (seq2, 0.2),
        ],
    )

    assay_with_split = Assay(
        name="assay_with_split",
        fields=[Field(name="sequence"), Field(name="split"), Field(name="DMS Score")],
        records=[
            (seq1, "train", 1.0),
            (seq2, "test", 2.0),
        ],
        non_targets=["split"],
    )

    dataset = Dataset(
        name="dataset_mixed_split_presence",
        description="One assay without split column, one assay with split column.",
        assays=[assay_without_split, assay_with_split],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_sequence() -> Dataset:
    """A dataset containing a single sequence."""
    sequence = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    dataset = Dataset(
        name="dataset_with_single_sequence",
        description="A dataset containing a single sequence.",
        assay_variables=[],
        assays=[],
        sequences=[sequence],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_sequences() -> Dataset:
    """A dataset containing multiple sequences."""
    sequence1 = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    sequence2 = Sequence(
        name="seq2",
        value=Seq("GFEDCA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    dataset = Dataset(
        name="dataset_with_multiple_sequences",
        description="A dataset containing multiple sequences.",
        assay_variables=[],
        assays=[],
        sequences=[sequence1, sequence2],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_duplicates_sequences_across_splits() -> Dataset:
    """A dataset where the same sequence appears in multiple splits (overlap)."""
    sequences = [
        Sequence(
            name="seq1",
            value=Seq("ACDEFG"),
            type=SequenceType.WILD_TYPE,
            alphabet=SequenceAlphabet.AA,
        ),
        Sequence(
            name="seq2",
            value=Seq("GFEDCA"),
            type=SequenceType.WILD_TYPE,
            alphabet=SequenceAlphabet.AA,
        ),
    ]

    assay = Assay(
        name="overlap_assay",
        fields=[
            Field(name="sequence"),
            Field(name="DMS Score"),
            Field(name="split"),
        ],
        records=[
            (sequences[0], 1.0, "train"),
            (sequences[1], 2.0, "train"),
            (sequences[0], 3.0, "test"),
        ],
        non_targets=["split"],
    )

    dataset = Dataset(
        name="dataset_with_duplicates_sequences_across_splits",
        description="Dataset with overlapping sequences across splits for testing.",
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )
    return dataset


@pytest.fixture
def datasets_with_different_targets_across_assays() -> Dataset:
    seq1 = Sequence(
        name="seq1",
        value=Seq("ACDEFG"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    seq2 = Sequence(
        name="seq2",
        value=Seq("GFEDCA"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
    )
    assay1 = Assay(
        name="assay_with_target_A",
        records=[(seq1, 1.0), (seq2, 2.0)],
        fields=[
            Field(name=SEQUENCE, description=None),
            Field(name="target_A", description=None),
        ],
    )
    assay2 = Assay(
        name="assay_with_target_B",
        records=[(seq1, 10.0), (seq2, 20.0)],
        fields=[
            Field(name=SEQUENCE, description=None),
            Field(name="target_B", description=None),
        ],
    )
    dataset = Dataset(
        name="multi_assay_dataset",
        assay_targets=[
            Field(name="target_A", description=None),
            Field(name="target_B", description=None),
        ],
        assays=[assay1, assay2],
    )
    return dataset


@pytest.fixture
def dataset_with_structure() -> Dataset:
    """A dataset containing a single structure."""
    structure = Structure(
        name="structure1",
        value=AtomArray(0),
        description="A test structure",
        metadata={"source": "test"},
    )
    dataset = Dataset(
        name="dataset_with_single_structure",
        description="A dataset containing a single structure.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[structure],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_structures() -> Dataset:
    """A dataset containing multiple structures."""
    structure1 = Structure(
        name="structure1",
        value=AtomArray(0),
        description="A test structure",
        metadata={"source": "test"},
    )
    structure2 = Structure(
        name="structure2",
        value=AtomArray(0),
        description="A test structure",
        metadata={"source": "test"},
    )
    dataset = Dataset(
        name="dataset_with_multiple_structures",
        description="A dataset containing multiple structures.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[structure1, structure2],
        msas=[],
    )
    return dataset


@pytest.fixture
def dataset_with_msa() -> Dataset:
    """A dataset containing a single MSA."""
    alignment = fasta.FastaFile()
    alignment["seq1"] = "ACDEFG"
    alignment["seq2"] = "GFEDCA"
    msa = MSA(
        name="msa1",
        value=alignment,
        description="A test MSA",
    )
    dataset = Dataset(
        name="dataset_with_single_msa",
        description="A dataset containing a single MSA.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[msa],
    )
    return dataset


@pytest.fixture
def dataset_with_msas() -> Dataset:
    """A dataset containing multiple MSAs."""
    alignment1 = fasta.FastaFile()
    alignment1["seq1"] = "ACDEFG"
    alignment1["seq2"] = "GFEDCA"
    alignment2 = fasta.FastaFile()
    alignment2["seq3"] = "ADCGFE"
    alignment2["seq4"] = "FEDCBA"
    msa1 = MSA(name="msa1", value=alignment1, description="A test MSA")
    msa2 = MSA(name="msa2", value=alignment2, description="A test MSA")
    dataset = Dataset(
        name="dataset_with_multiple_msas",
        description="A dataset containing multiple MSAs.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[msa1, msa2],
    )
    return dataset


@pytest.fixture
def dataset_with_publication() -> Dataset:
    """A dataset containing publication information."""
    publication = Publication(
        title="Test Publication",
        author="Test Author",
        journal="Test Journal",
        year="2023",
    )
    dataset = Dataset(
        name="dataset_with_publication",
        description="A dataset containing publication information.",
        assay_variables=[],
        assays=[],
        sequences=[],
        structures=[],
        msas=[],
        publication=publication,
    )
    return dataset


@pytest.fixture
def dataset_with_everything(
    dataset_with_assays: Dataset,
    dataset_with_sequences: Dataset,
    dataset_with_structures: Dataset,
    dataset_with_msas: Dataset,
) -> Dataset:
    """A dataset containing everything."""
    # Tightly coupled with datasets fixture
    dataset = (
        dataset_with_assays
        | dataset_with_sequences
        | dataset_with_structures
        | dataset_with_msas
    ).model_copy(update={"name": "dataset_with_everything"})
    return dataset


@pytest.fixture
def datasets(
    dataset_empty: Dataset,
    dataset_with_assay_empty: Dataset,
    dataset_with_assay: Dataset,
    dataset_with_assay_raw: Dataset,
    dataset_with_assays: Dataset,
    dataset_with_assay_predefined_split: Dataset,
    dataset_with_sequence: Dataset,
    dataset_with_sequences: Dataset,
    dataset_with_duplicates_sequences_across_splits: Dataset,
    dataset_with_structure: Dataset,
    dataset_with_structures: Dataset,
    dataset_with_msa: Dataset,
    dataset_with_msas: Dataset,
    dataset_with_publication: Dataset,
    dataset_with_everything: Dataset,
) -> list[Dataset]:
    """All test datasets."""
    return [
        dataset_empty,
        dataset_with_assay_empty,
        dataset_with_assay,
        dataset_with_assay_raw,
        dataset_with_assays,
        dataset_with_assay_predefined_split,
        dataset_with_sequence,
        dataset_with_sequences,
        dataset_with_duplicates_sequences_across_splits,
        dataset_with_structure,
        dataset_with_structures,
        dataset_with_msa,
        dataset_with_msas,
        dataset_with_publication,
        dataset_with_everything,
    ]


@pytest.fixture
def dataset(request: pytest.FixtureRequest, datasets: list[Dataset]) -> Dataset:
    """A generic dataset for testing.

    Args:
        request (pytest.FixtureRequest): The pytest request object.
            Expecting to contain the dataset name in `request.param`.
        datasets: a list of named datasets.

    Returns:
        Dataset: The dataset with the requested name.
    """
    param = getattr(request, "param", "UNKNOWN")
    dataset = next((d for d in datasets if d.name == param), None)
    if dataset is None:
        raise ValueError(f"Unknown dataset: {param}")
    return dataset


dataset2 = dataset  # To have a second fixture for union tests


@pytest.fixture
def metrics_dataset_with_assay() -> Dataset:
    """A dataset containing a single assay with 10 records."""
    sequences = [
        Sequence(
            name=f"seq{i}",
            value=Seq(seq_value),
            type=SequenceType.ENGINEERED_SEQUENCE,
            alphabet=SequenceAlphabet.AA,
        )
        for i, seq_value in enumerate(
            [
                "ACDEFG",
                "ACDEFH",
                "ACDEFI",
                "ACDEFK",
                "ACDEFL",
                "ACDEFM",
                "ACDEFN",
                "ACDEFP",
                "ACDEFQ",
                "ACDEFR",
            ],
            start=1,
        )
    ]

    assay = Assay(
        name="assay1",
        records=[(sequences[i], float(i + 1), float(i + 1) + 0.5) for i in range(10)],
        fields=[
            Field(name="sequence"),
            Field(name="DMS Score"),
            Field(name="stability"),
        ],
    )
    return Dataset(
        name="dataset_with_single_assay",
        description="A dataset containing a single assay.",
        assay_variables=[Field(name="var1", description="A test variable")],
        assay_targets=[
            Field(name="DMS Score", description="The DMS score"),
            Field(name="stability", description="The resistance to temperature"),
        ],
        assays=[assay],
        sequences=[],
        structures=[],
        msas=[],
    )


@pytest.fixture
def metrics_predicted_dataset(metrics_dataset_with_assay: Dataset) -> Dataset:
    """A predictions dataset built from metrics_dataset_with_assay."""
    predictions_df = pl.DataFrame(
        {
            "sequence": [
                "ACDEFG",
                "ACDEFH",
                "ACDEFI",
                "ACDEFK",
                "ACDEFL",
                "ACDEFM",
                "ACDEFN",
                "ACDEFP",
                "ACDEFQ",
                "ACDEFR",
            ],
            "DMS Score": [1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1],
        }
    )
    return metrics_dataset_with_assay.predictions_delta(
        predictions_df, target="DMS Score"
    )


@pytest.fixture
def metrics_subsets_with_assays(metrics_dataset_with_assay: Dataset) -> Subsets:
    """A Subsets object with a 5-fold 'random' split (2 records per fold)."""
    folds = []
    for fold_idx in range(5):
        records_mask = [False] * 10
        records_mask[fold_idx * 2] = True
        records_mask[fold_idx * 2 + 1] = True

        fold_slice = DatasetSlice(
            assays=[AssaySlice(records=records_mask)],
            metadata={"fold": float(fold_idx)},
        )
        folds.append(fold_slice)

    return Subsets(dataset=metrics_dataset_with_assay, slices={"random": folds})
