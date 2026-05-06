import io
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest
import toml
from Bio.Seq import Seq
from evedesign.sequence import Sequence as evdSequence
from evedesign.sequence import Sequences
from pydantic import ValidationError

from proteingym.base import Dataset
from proteingym.base.msa import (
    MSA,
    MSAFormat,
    MSAManifestSection,
    MSAWeightsManifestSection,
)
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType


def test_msa_manifest_section_minimal(tmp_path: Path) -> None:
    """Only path is required for a minimal MSA manifest section."""
    path = tmp_path / "test.msa"
    path.touch()

    try:
        MSAManifestSection(path=path)
    except ValidationError as e:
        raise AssertionError("Could not create MSAManifestSection") from e
    else:
        assert True, "MSAManifestSection created successfully with minimal fields."


def test_msa_manifest_section_with_relative_path(tmp_path: Path) -> None:
    """The path can be relative to another path."""
    path = tmp_path / "test.msa"
    path.touch()
    context = {"relative_to_path": tmp_path}

    try:
        MSAManifestSection.model_validate({"path": "test.msa"}, context=context)
    except ValidationError as e:
        raise AssertionError("Could not create MSAManifestSection") from e
    else:
        assert True, "MSAManifestSection created successfully with minimal fields."


def test_msa_manifest_section_missing_path() -> None:
    """A validation error is raised if path is missing."""
    match = (
        "validation error for MSAManifestSection\npath\n  Path does not point to a file"
    )
    with pytest.raises(ValidationError, match=match):
        MSAManifestSection(path="non_existent.msa")  # noqa


@pytest.mark.parametrize("field", ["name", "description"])
def test_msa_manifest_section_empty_string_field(tmp_path: Path, field: str) -> None:
    """A validation error is raised if string <field> is empty."""
    path = tmp_path / "test.msa"
    path.touch()

    match = (
        f"validation error for MSAManifestSection\n{field}\n  "
        "String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        MSAManifestSection(path=path, **{field: ""})


def test_msa_manifest_section_serialize_path_as_posix(tmp_path: Path) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "test.msa"
    path.touch()

    section = MSAManifestSection(path=path)

    assert section.model_dump().get("path") == path.as_posix()


def test_msa_manifest_section_serialize_format_as_string(tmp_path: Path) -> None:
    """The format is serialized as a string.

    The StrEnum is tricky to test as it is both a string and enum, hence,
    we test it with a TOML serialization to be sure it is serialized correctly.
    """
    path = tmp_path / "test.msa"
    path.touch()

    section = MSAManifestSection(path=path)

    section_in_toml = toml.dumps(section.model_dump())
    assert "a3m" in section_in_toml


def test_msa_manifest_section_serialize_path_as_posix_relative_to(
    tmp_path: Path,
) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "test.msa"
    path.touch()
    context = {"relative_to_path": tmp_path}

    section = MSAManifestSection(path=path)

    assert section.model_dump(context=context).get("path") == "test.msa"


def test_msa_minimal() -> None:
    """Only name and value are required for a minimal MSA."""
    try:
        MSA(name="test", value=Sequences([]))
    except ValidationError as e:
        raise AssertionError("Could not create MSA") from e
    else:
        assert True, "MSA created successfully with minimal fields."


@pytest.fixture
def multiple_sequence_alignment() -> Sequences:
    """Minimal multiple sequence alignment for testing."""
    a = evdSequence("AAAACGT", id="Alpha")
    b = evdSequence("AAA-CGT", id="Beta")
    c = evdSequence("AAAAGGT", id="Gamma")
    alignment = Sequences([a, b, c])
    return alignment


@pytest.fixture
def fasta_file(
    tmp_path: Path, multiple_sequence_alignment: Sequences
) -> Path:
    """FASTA structure file for testing."""
    path = tmp_path / "structure.fasta"
    with open(path, "w") as f:
        for s in multiple_sequence_alignment.seqs:
            f.write(f">{s.id_}\n{s.seq}\n")
    return path


def test_msa_from_manifest_section_with_fasta(fasta_file: Path) -> None:
    """A MSA can be created from a manifest section with FASTA file."""
    section = MSAManifestSection(path=fasta_file, format=MSAFormat.FASTA)

    msa = MSA.from_manifest_section(section)

    assert msa.name == "structure"
    assert isinstance(msa.value, Sequences)


@pytest.fixture
def a3m_file(tmp_path: Path, multiple_sequence_alignment: Sequences) -> Path:
    """A3M structure file for testing."""
    path = tmp_path / "structure.a3m"
    with open(path, "w") as f:
        for s in multiple_sequence_alignment.seqs:
            f.write(f">{s.id_}\n{s.seq}\n")
    return path


def test_msa_from_manifest_section_with_a3m(a3m_file: Path) -> None:
    """An MSA can be created from a manifest section with A3M file."""
    section = MSAManifestSection(path=a3m_file, format=MSAFormat.A3M)

    msa = MSA.from_manifest_section(section)

    assert msa.name == "structure"
    assert isinstance(msa.value, Sequences)


@pytest.fixture
def weights_file(tmp_path: Path) -> Path:
    """Weights file for testing."""
    arr = [0.1, 0.5, 0.4]
    path = tmp_path / "weights.npy"
    np.save(path, arr)
    return path


def test_msa_weights_manifest_section_with_path(weights_file: Path) -> None:
    """An MSAWeightsManifestSection can be created with a path."""
    try:
        MSAWeightsManifestSection(name="test", path=weights_file)
    except ValidationError as e:
        raise AssertionError("Could not create MSAWeightsManifestSection") from e
    else:
        assert True, "MSAWeightsManifestSection created successfully."


def test_msa_weights_manifest_section_serialize_with_relative_path(
    tmp_path: Path,
) -> None:
    """MSAWeightsManifestSection path is serialized relative to context."""
    weights_file = tmp_path / "weights.npy"
    np.save(weights_file, np.array([0.1, 0.5, 0.4]))

    section = MSAWeightsManifestSection(name="test", path=weights_file)
    context = {"relative_to_path": tmp_path}

    dumped = section.model_dump(context=context)

    assert dumped["path"] == "weights.npy"


def test_msa_weights_manifest_section_invalid_format(tmp_path: Path) -> None:
    """A validation error is raised if weights file has invalid format."""
    weights_path = tmp_path / "weights.txt"
    weights_path.touch()

    with pytest.raises(
        ValidationError, match="Unsupported MSA weight file format: txt"
    ):
        MSAWeightsManifestSection(name="test", path=weights_path)


def test_msa_weights_from_manifest_section_with_path(weights_file: Path) -> None:
    """MSAWeights can be created from a manifest section with path."""
    from proteingym.base.msa import MSAWeights

    section = MSAWeightsManifestSection(name="test", path=weights_file)
    weights = MSAWeights.from_manifest_section(section)

    assert weights.name == "test"
    assert weights.value == [0.1, 0.5, 0.4]


def test_msa_weights_dump_to_file(tmp_path: Path) -> None:
    """MSAWeights can be dumped to a file."""
    from proteingym.base.msa import MSAWeights

    weights = MSAWeights(name="test", value=[0.1, 0.5, 0.4])
    path = weights.dump(path=tmp_path / "test_weights.npy")

    loaded_weights = np.load(path).tolist()
    assert loaded_weights == [0.1, 0.5, 0.4]


def test_msa_weights_dump_to_directory(tmp_path: Path) -> None:
    """MSAWeights can be dumped to a file inside a directory."""
    from proteingym.base.msa import MSAWeights

    weights = MSAWeights(name="test", value=[0.1, 0.5, 0.4])
    path = weights.dump(path=tmp_path)

    assert path.name == "test_weights.npy"
    loaded_weights = np.load(path).tolist()
    assert loaded_weights == [0.1, 0.5, 0.4]


def test_msa_weights_as_manifest_section(tmp_path: Path) -> None:
    """MSAWeights can be converted to a manifest section."""
    from proteingym.base.msa import MSAWeights

    weights = MSAWeights(name="test", value=[0.1, 0.5, 0.4])
    weights_path = weights.dump(path=tmp_path)

    section = weights.as_manifest_section(path=weights_path)

    assert section.name == "test"
    assert section.path == weights_path


def test_msa_as_manifest_section(fasta_file: Path) -> None:
    """An MSA can be converted to a manifest section."""
    expected = MSAManifestSection(
        path=fasta_file,
        name="test_msa",
        description=None,
    )
    msa = MSA(name="test_msa", value=Sequences([]))

    section = msa.as_manifest_section(path=fasta_file)

    assert section == expected


def test_msa_dump_to_file(
    tmp_path: Path, multiple_sequence_alignment: Sequences
) -> None:
    """A MSA can be dumped to a FASTA file."""
    msa = MSA(name="test", value=multiple_sequence_alignment)

    path = msa.dump(path=tmp_path / "msa.fasta")

    loaded_msa_value = Sequences.from_file(path, format="fasta")
    loaded_msa = MSA(name="test", value=loaded_msa_value)
    assert msa == loaded_msa


def test_msa_dump_to_directory(
    tmp_path: Path, multiple_sequence_alignment: Sequences
) -> None:
    """A MSA can be dumped to a FASTA file inside a directory."""
    msa = MSA(name="test", value=multiple_sequence_alignment)

    path = msa.dump(path=tmp_path)

    loaded_msa_value = Sequences.from_file(path, format="fasta")
    loaded_msa = MSA(name="test", value=loaded_msa_value)
    assert msa == loaded_msa


def test_msa_reference_sequence_present_in_dataset(
    multiple_sequence_alignment: Sequences,
) -> None:
    """A ValueError is raised if the reference sequence is not in the MSA."""
    seq = Sequence(
        name="ref_seq",
        value=Seq("TTTTTTT"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.DNA,
    )
    msa = MSA(
        name="test",
        value=multiple_sequence_alignment,
        reference_sequence_name="ref_seq",
    )

    try:
        dataset = Dataset(name="test", msas=[msa], sequences=[seq])
    except ValueError as e:
        raise ValueError(
            "Could not create Dataset with MSA and reference sequence"
        ) from e
    else:
        assert msa.reference_sequence_name in [seq.name for seq in dataset.sequences], (
            "Reference sequence not found in dataset sequences."
        )


def test_msa_reference_sequence_not_present_in_dataset(
    multiple_sequence_alignment: Sequences,
) -> None:
    """A ValueError is raised if the reference sequence is not in the MSA."""
    msa = MSA(
        name="test",
        value=multiple_sequence_alignment,
        reference_sequence_name="ref_seq",
    )

    with pytest.raises(
        ValueError,
        match="MSA 'test' reference sequence 'ref_seq' is not present in the"
        " dataset's sequences.",
    ):
        Dataset(name="test", msas=[msa], sequences=[])


def test_dataset_dump_with_msa(
    tmp_path: Path, multiple_sequence_alignment: Sequences
) -> None:
    """Test the zip file created by the Dataset dump with MSAs.

    The created archive:
    - Should not contain a bad file.
    - Should contain the sequence file.
    - Should result the sequence being loaded correctly.
    """
    msa = MSA(name="msa", value=multiple_sequence_alignment)
    dataset = Dataset(name="test", msas=[msa])

    path = dataset.dump(path=tmp_path)

    zip_ = ZipFile(path)
    assert not zip_.testzip(), "Dataset dump contains a bad file."
    assert "msas/msa.a3m" in zip_.namelist(), "MSA file not found in dataset dump."

    with zip_.open("msas/msa.a3m", "r") as msa_file:
        string_io = io.StringIO(msa_file.read().decode("utf-8"))
        # Manual write to file and then read with Sequences
        temp_file = tmp_path / "temp_msa.a3m"
        temp_file.write_text(string_io.getvalue())
        loaded_msa_value = Sequences.from_file(temp_file, format="a3m")
        loaded_msa = MSA(name="msa", value=loaded_msa_value)
        assert msa == loaded_msa


def test_dataset_dump_with_msas_contains_archive_names(
    tmp_path: Path, multiple_sequence_alignment: Sequences
) -> None:
    """Same as `test_dataset_dump_with_msa`, but with MSAs."""
    expected = {"msas/msa1.a3m", "msas/msa2.a3m"}
    msa1 = MSA(name="msa1", value=multiple_sequence_alignment)
    msa2 = MSA(name="msa2", value=multiple_sequence_alignment)
    dataset = Dataset(name="test", msas=[msa1, msa2])

    path = dataset.dump(path=tmp_path)

    archive_names = ZipFile(path).namelist()
    assert not expected - set(archive_names), (
        f"Expected the following archive names {expected}"
    )


def test_dataset_with_msas_dump_from_path_unit(
    tmp_path: Path, multiple_sequence_alignment: Sequences
) -> None:
    """Dumping a dataset with MSAs should return the same after reading"""
    msa1 = MSA(name="msa1", value=multiple_sequence_alignment)
    msa2 = MSA(name="msa2", value=multiple_sequence_alignment)
    dataset = Dataset(name="test", msas=[msa1, msa2])

    path = dataset.dump(path=tmp_path)

    loaded_dataset = Dataset.from_path(path)

    # TODO (#255): Implement Dataset.__eq__ and use it here instead of multiple asserts
    assert loaded_dataset.name == dataset.name
    assert len(loaded_dataset.msas) == len(dataset.msas)
    for loaded_msa, msa in zip(loaded_dataset.msas, dataset.msas, strict=True):
        assert loaded_msa.name == msa.name
        assert loaded_msa == msa


def test_dataset_fails_with_duplicate_msa_names(
    multiple_sequence_alignment: Sequences,
) -> None:
    """A dataset with duplicate MSA names should raise a ValidationError."""
    duplicate_names = ["duplicate1", "duplicate2"]
    msa1 = MSA(name=duplicate_names[0], value=multiple_sequence_alignment)
    msa2 = MSA(name=duplicate_names[0], value=multiple_sequence_alignment)
    msa3 = MSA(name=duplicate_names[1], value=multiple_sequence_alignment)
    msa4 = MSA(name=duplicate_names[1], value=multiple_sequence_alignment)

    match = "Duplicate names found in `Dataset.msas`:.*" + ", ".join(duplicate_names)
    with pytest.raises(ValidationError, match=match):
        Dataset(name="test", msas=[msa1, msa2, msa3, msa4])


def test_msa_repr(
    multiple_sequence_alignment: Sequences,
) -> None:
    """The MSA __repr__ method should return a concise representation."""
    description = "This is a test MSA used to verify the __repr__ method."
    msa = MSA(
        name="test_msa", value=multiple_sequence_alignment, description=description
    )

    repr_str = repr(msa)

    assert repr_str.startswith("MSA(")
    assert "name='test_msa'" in repr_str
    assert (
        "description: This is a test MSA used to verify the __repr__ method."
        in repr_str
    )
    assert "value:" in repr_str

    long_desc = "A" * 61 + "BCD"
    msa = MSA(
        name="long_desc_msa", value=multiple_sequence_alignment, description=long_desc
    )
    repr_str = repr(msa)
    assert f"description: {long_desc[:60]}..." in repr_str

    msa = MSA(name="no_desc_msa", value=multiple_sequence_alignment, description=None)
    repr_str = repr(msa)
    assert "description: None," in repr_str

    for s in multiple_sequence_alignment.seqs[:3]:
        assert s.id_ in repr_str
        assert s.seq[:50] in repr_str

    if len(multiple_sequence_alignment.seqs) > 3:
        assert "\t\t..." in repr_str
