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


def test_structure_manifest_missing_path() -> None:
    """A validation error is raised if path is missing."""
    match = (
        "validation error for StructureManifestSection\npath\n  "
        "Path does not point to a file"
    )
    with pytest.raises(ValidationError, match=match):
        StructureManifestSection(path="non_existent.pdb")


@pytest.mark.parametrize("field", ["name", "description"])
def test_structure_manifest_empty_string_field(tmp_path: Path, field: str) -> None:
    """A validation error is raised if <field> is empty."""
    path = tmp_path / "test.pdb"
    path.touch()

    match = (
        f"validation error for StructureManifestSection\n{field}\n  "
        "String should have at least 1 character"
    )
    with pytest.raises(ValidationError, match=match):
        StructureManifestSection(path=path, **{field: ""})


def test_structure_manifest_serialize_path_as_posix(tmp_path: Path) -> None:
    """The path is serialized as a Posix path."""
    path = tmp_path / "test.pdb"
    path.touch()

    section = StructureManifestSection(path=path)
    assert section.model_dump().get("path") == path.as_posix()


def test_structure_minimal() -> None:
    """A minimal Structure can be created."""
    try:
        Structure(name="test", value=BioStructure("test"))
    except ValidationError as e:
        raise AssertionError("Could not create Structure") from e
    else:
        assert True, "Structure created successfully with minimal fields."


@pytest.mark.parametrize("field", ["name", "description"])
def test_structure_empty_string_field(tmp_path: Path, field: str) -> None:
    """A validation error is raised if <field> is empty."""

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

    model_id = 0
    model = Model(model_id)
    structure.add(model)

    chain_id = "A"
    chain = Chain(chain_id)
    model.add(chain)

    residue_id = (" ", 1, " ")
    residue = Residue(residue_id, "GLY", "")
    chain.add(residue)

    coord = np.array([10.0, 20.0, 30.0], dtype=float)
    b_factor = 20.0
    occupancy = 1.0
    altloc = " "
    fullname = " CA "  # PDB atom name field (4 characters)
    element = "C"
    atom = Atom(
        name="CA",
        coord=coord,
        bfactor=b_factor,
        occupancy=occupancy,
        altloc=altloc,
        fullname=fullname,
        serial_number=1,
        element=element,
    )
    residue.add(atom)

    return structure


@pytest.fixture
def structure_pdb_file(tmp_path: Path, bio_structure: BioStructure) -> Path:
    """PDB structure file for testing."""
    io = PDBIO()
    io.set_structure(bio_structure)
    path = tmp_path / "structure.pdb"
    io.save(path.as_posix())
    return path


@pytest.fixture
def structure_cif_file(tmp_path: Path, bio_structure: BioStructure) -> Path:
    """CIF structure file for testing."""
    io = MMCIFIO()
    io.set_structure(bio_structure)
    path = tmp_path / "structure.cif"
    io.save(path.as_posix())
    return path


def test_structure_from_manifest_section_with_c(structure_cif_file) -> None:
    """A Structure can be created from a manifest section."""
    section = StructureManifestSection(path=structure_cif_file)
    structure = Structure.from_manifest_section(section)

    assert structure.name == "structure"
    assert isinstance(structure.value, BioStructure)
