from pathlib import Path

import numpy as np
import pytest
from Bio.PDB.Atom import Atom
from Bio.PDB.Chain import Chain
from Bio.PDB.mmcifio import MMCIFIO
from Bio.PDB.Model import Model
from Bio.PDB.PDBIO import PDBIO
from Bio.PDB.Residue import Residue
from Bio.PDB.Structure import Structure as BioStructure
from pydantic import ValidationError

from pg2_dataset.models.dataset import Dataset, Manifest
from pg2_dataset.models.structure import Structure, StructureManifestSection


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
    path = tmp_path / "test.pdb"
    path.touch()

    section = StructureManifestSection(path=path)

    assert section.model_dump().get("path") == path.as_posix()


def test_structure_minimal() -> None:
    """Only name and value are required for a minimal Structure."""
    try:
        Structure(name="test", value=BioStructure("test"))
    except ValidationError as e:
        raise AssertionError("Could not create Structure") from e
    else:
        assert True, "Structure created successfully with minimal fields."


@pytest.mark.parametrize("field", ["name", "description"])
def test_structure_empty_string_field(field: str) -> None:
    """A validation error is raised if string <field> is empty."""

    match = (
        f"validation error for Structure\n{field}\n  "
        "String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        Structure(value=BioStructure("test"), **{"name": "test", field: ""})


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


def test_dataset_with_structures(
    pdb_file: Path, cif_file: Path, bio_structure: BioStructure
) -> None:
    """A Dataset can be created with structures from the manifest."""
    manifest = Manifest(
        name="test",
        structures=[
            StructureManifestSection(path=pdb_file, name=bio_structure.id),
            StructureManifestSection(path=cif_file, name=bio_structure.id),
        ],
    )

    dataset = Dataset.from_manifest(manifest)

    assert len(dataset.structures) == 2
    assert dataset.structures[0].value.strictly_equals(bio_structure)

    # There is an inconsistency in biopython that loads the full name of an Atom
    # differently for a PDB and CIF file - the full name is trimmed.
    # Hence, we overwrite the fullname here before the assertion.
    list(bio_structure.get_atoms())[0].fullname = "CA"
    assert dataset.structures[1].value.strictly_equals(bio_structure)
