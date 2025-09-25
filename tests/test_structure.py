import io
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest
from Bio.PDB.Atom import Atom
from Bio.PDB.Chain import Chain
from Bio.PDB.mmcifio import MMCIFIO
from Bio.PDB.MMCIFParser import MMCIFParser
from Bio.PDB.Model import Model
from Bio.PDB.PDBIO import PDBIO
from Bio.PDB.PDBParser import PDBParser
from Bio.PDB.Residue import Residue
from Bio.PDB.Structure import Structure as BioStructure
from pydantic import ValidationError

from pg2_dataset.dataset import Dataset
from pg2_dataset.manifest import MANIFEST_LATEST_VERSION, Manifest
from pg2_dataset.structure import (
    Structure,
    StructureFormat,
    StructureManifestSection,
)


def test_structure_manifest_section_minimal(tmp_path: Path) -> None:
    """Only path is required for a minimal structure manifest section."""
    path = tmp_path / "test.pdb"
    path.touch()

    try:
        StructureManifestSection(path=path)
    except ValidationError as e:
        raise AssertionError("Could not create StructureManifestSection") from e
    else:
        assert True, (
            "StructureManifestSection created successfully with minimal fields."
        )


def test_structure_manifest_section_with_relative_path(tmp_path: Path) -> None:
    """The path can be relative to another path."""
    path = tmp_path / "structure.pdb"
    path.touch()
    context = {"relative_to_path": tmp_path}

    try:
        StructureManifestSection.model_validate(
            {
                "path": "structure.pdb",
            },
            context=context,
        )
    except ValidationError as e:
        raise AssertionError("Could not create StructureManifestSection") from e
    else:
        assert True, (
            "StructureManifestSection created successfully with minimal fields."
        )


def test_structure_manifest_section_missing_path() -> None:
    """A validation error is raised if path is missing."""
    match = (
        "validation error for StructureManifestSection\npath\n  "
        "Path does not point to a file"
    )
    with pytest.raises(ValidationError, match=match):
        StructureManifestSection(path="non_existent.pdb")


@pytest.mark.parametrize("field", ["name", "description"])
def test_structure_manifest_section_empty_string_field(
    tmp_path: Path, field: str
) -> None:
    """A validation error is raised if string <field> is empty."""
    path = tmp_path / "test.pdb"
    path.touch()

    match = (
        f"validation error for StructureManifestSection\n{field}\n  "
        "String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        StructureManifestSection(path=path, **{field: ""})


def test_structure_manifest_section_serialize_path_as_posix(tmp_path: Path) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "structure.pdb"
    path.touch()

    section = StructureManifestSection(path=path)

    assert section.model_dump().get("path") == path.as_posix()


def test_structure_manifest_section_serialize_path_as_posix_relative_to(
    tmp_path: Path,
) -> None:
    """The path is serialized as a Posix path relative to another path."""
    path = tmp_path / "structure.pdb"
    path.touch()
    context = {"relative_to_path": tmp_path}

    section = StructureManifestSection(path=path)

    assert section.model_dump(context=context).get("path") == "structure.pdb"


def test_structure_minimal() -> None:
    """Only name and value are required for a minimal Structure."""
    try:
        Structure(name="test", value=BioStructure("test"))
    except ValidationError as e:
        raise AssertionError("Could not create Structure") from e
    else:
        assert True, "Structure created successfully with minimal fields."


@pytest.fixture
def bio_structure() -> BioStructure:
    """Minimal biopython structure for testing."""
    structure = BioStructure("test")

    model = Model(id=0)
    structure.add(model)

    chain = Chain(id="A")
    model.add(chain)

    residue = Residue(
        id=(" ", 1, " "),
        resname="GLY",
        segid="",
    )
    chain.add(residue)

    atom = Atom(
        name="CA",
        coord=np.array([10.0, 20.0, 30.0], dtype=float),
        bfactor=20.0,
        occupancy=1.0,
        altloc=" ",
        fullname=" CA ",  # PDB atom name field (4 characters)
        serial_number=1,
        element="C",
    )
    residue.add(atom)

    return structure


@pytest.fixture
def pdb_file(tmp_path: Path, bio_structure: BioStructure) -> Path:
    """PDB structure file for testing."""
    io = PDBIO()
    io.set_structure(bio_structure)
    path = tmp_path / "structure.pdb"
    io.save(path.as_posix())
    return path


@pytest.fixture
def cif_file(tmp_path: Path, bio_structure: BioStructure) -> Path:
    """CIF structure file for testing."""
    io = MMCIFIO()
    io.set_structure(bio_structure)
    path = tmp_path / "structure.cif"
    io.save(path.as_posix())
    return path


def test_structure_from_manifest_section_with_pdb(pdb_file: Path) -> None:
    """A Structure can be created from a manifest section with PDB file."""
    section = StructureManifestSection(path=pdb_file)

    structure = Structure.from_manifest_section(section)

    assert structure.name == "structure"
    assert isinstance(structure.value, BioStructure)


def test_structure_from_manifest_section_with_cif(cif_file: Path) -> None:
    """A Structure can be created from a manifest section with CIF file."""
    section = StructureManifestSection(path=cif_file)

    structure = Structure.from_manifest_section(section)

    assert structure.name == "structure"
    assert isinstance(structure.value, BioStructure)


def test_structure_from_manifest_section_structure_id_as_stem(pdb_file: Path) -> None:
    """The structure ID is set to the file stem."""
    section = StructureManifestSection(path=pdb_file)

    structure = Structure.from_manifest_section(section)

    assert structure.value.get_id() == pdb_file.stem


def test_structure_from_manifest_section_structure_id_as_name(pdb_file: Path) -> None:
    """The structure ID is set to the new name."""
    section = StructureManifestSection(path=pdb_file, name="new_structure")

    structure = Structure.from_manifest_section(section)

    assert structure.value.get_id() == "new_structure"


def test_structure_dump_to_pdb(tmp_path: Path, bio_structure: BioStructure) -> None:
    """A Structure can be dumped to a PDB file."""
    structure = Structure(name="test", value=bio_structure)

    path = structure.dump(path=tmp_path)

    loaded_structure = PDBParser().get_structure("test", path)
    assert loaded_structure.strictly_equals(bio_structure)


def test_structure_dump_to_cif(tmp_path: Path, bio_structure: BioStructure) -> None:
    """A Structure can be dumped to a cif file."""
    structure = Structure(name="test", value=bio_structure)

    path = structure.dump(path=tmp_path, format=StructureFormat.MMCIF)

    # There is an inconsistency in biopython that loads the full name of an Atom
    # differently for a PDB and CIF file - the full name is trimmed for the
    # later. Hence, we overwrite the fullname here before the assertion.
    list(bio_structure.get_atoms())[0].fullname = "CA"
    loaded_structure = MMCIFParser().get_structure("test", path)
    assert loaded_structure.strictly_equals(bio_structure)


def test_dataset_with_structures(
    pdb_file: Path, cif_file: Path, bio_structure: BioStructure
) -> None:
    """A Dataset can be created with structures from the manifest."""
    bio_structure1 = bio_structure.copy()
    bio_structure1.id = "structure1"
    bio_structure2 = bio_structure.copy()
    bio_structure2.id = "structure2"
    manifest = Manifest(
        version=MANIFEST_LATEST_VERSION,
        name="test",
        structures=[
            StructureManifestSection(path=pdb_file, name=bio_structure1.id),
            StructureManifestSection(path=cif_file, name=bio_structure2.id),
        ],
    )
    dataset = Dataset.from_manifest(manifest)

    assert len(dataset.structures) == 2
    assert dataset.structures[0].value.strictly_equals(bio_structure1)

    # There is an inconsistency in biopython that loads the full name of an Atom
    # differently for a PDB and CIF file - the full name is trimmed.
    # Hence, we overwrite the fullname here before the assertion.
    list(bio_structure2.get_atoms())[0].fullname = "CA"
    assert dataset.structures[1].value.strictly_equals(bio_structure2)


def test_dataset_dump_with_structure(
    tmp_path: Path, bio_structure: BioStructure
) -> None:
    """The dataset can be dumped with structures.

    The created archive:
    - Should not contain a bad file.
    - Should contain the structure file.
    - Should result the structure being loaded correctly.
    """
    structure = Structure(name="test", value=bio_structure)
    dataset = Dataset(name="test", structures=[structure])

    path = dataset.dump(path=tmp_path)

    zip = ZipFile(path)
    assert not zip.testzip(), "Dataset dump contains a bad file."
    assert "structures/test.pdb" in zip.namelist(), (
        "Structure file not found in dataset dump."
    )

    with zip.open("structures/test.pdb", "r") as structure_file:
        string_io = io.StringIO(structure_file.read().decode("utf-8"))
        loaded_structure = PDBParser().get_structure("test", string_io)
        assert bio_structure == loaded_structure


def test_dataset_dump_with_structures_contains_archive_names(
    tmp_path: Path, bio_structure: BioStructure
) -> None:
    """Same as `test_dataset_dump_with_structure`, but with multiple structures."""
    expected = {"structures/structure1.pdb", "structures/structure2.pdb"}
    structure1 = Structure(name="structure1", value=bio_structure)
    structure2 = Structure(name="structure2", value=bio_structure)
    dataset = Dataset(name="test", structures=[structure1, structure2])

    path = dataset.dump(path=tmp_path)

    archive_names = ZipFile(path).namelist()
    assert not expected - set(archive_names), (
        f"Expected the following archive names {expected}"
    )


def test_dataset_with_structure_dump_from_path_unit(
    tmp_path: Path, bio_structure: BioStructure
) -> None:
    """Dumping a dataset with structure should return the same after reading"""
    structure = Structure(name=bio_structure.id, value=bio_structure)
    dataset = Dataset(name="test", structures=[structure])

    path = dataset.dump(path=tmp_path)

    loaded_dataset = Dataset.from_path(path)

    # TODO (#255): Implement Dataset.__eq__ and use it here instead of multiple asserts
    assert loaded_dataset.name == dataset.name
    assert len(loaded_dataset.structures) == len(dataset.structures)
    for loaded_structure, structure in zip(
        loaded_dataset.structures, dataset.structures, strict=True
    ):
        assert loaded_structure.name == structure.name
        assert loaded_structure.value == structure.value


def test_dataset_failes_with_duplicate_structure_names() -> None:
    """A dataset fails if there are duplicate structure names."""
    duplicate_names = ["duplicate1", "duplicate2"]
    structure1 = Structure(name=duplicate_names[0], value=BioStructure("test"))
    structure2 = Structure(name=duplicate_names[0], value=BioStructure("test"))
    structure3 = Structure(name=duplicate_names[1], value=BioStructure("test2"))
    structure4 = Structure(name=duplicate_names[1], value=BioStructure("test2"))

    with pytest.raises(
        ValidationError,
        match=rf"Duplicate names found in:.*Structures:.*{', '.join(duplicate_names)}",
    ):
        Dataset(
            name="test", structures=[structure1, structure2, structure3, structure4]
        )


def test_structure_repr(tmp_path: Path, bio_structure: BioStructure) -> None:
    """Test the string representation of the Structure class."""
    structure = Structure(
        name="test structure",
        value=bio_structure,
        description="A test structure",
        metadata={"key1": "value1", "key2": "value2"},
    )

    repr_str = repr(structure)
    assert "Structure(\n\tname='test structure'," in repr_str
    assert "description: A test structure," in repr_str
    assert "value: Type[Structure]," in repr_str
    assert "\tmetadata:" in repr_str
    assert "\t\tkey1: value1," in repr_str
    assert "\t\tkey2: value2," in repr_str
