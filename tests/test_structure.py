import io
from pathlib import Path
from zipfile import ZipFile

import biotite.structure.io.pdb as pdb
import biotite.structure.io.pdbx as pdbx
import numpy as np
import pytest
from biotite.structure import Atom, AtomArray
from pydantic import ValidationError

from proteingym.base import Dataset, Manifest
from proteingym.base.manifest import MANIFEST_LATEST_VERSION
from proteingym.base.structure import (
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
        StructureManifestSection(path="non_existent.pdb")  # noqa


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
        Structure(name="test", value=AtomArray(0))
    except ValidationError as e:
        raise AssertionError("Could not create Structure") from e
    else:
        assert True, "Structure created successfully with minimal fields."


@pytest.fixture
def biotite_structure() -> AtomArray:
    """Minimal biotite structure for testing."""
    atom = Atom(
        res_name="GLY",
        atom_name="CA",
        res_id=1,
        chain_id="A",
        coord=np.array([10.0, 20.0, 30.0]),
        element="C",
        hetero=False,
        occupancy=1.0,
        b_factor=20.0,
    )
    array = AtomArray(1)
    array[0] = atom
    return array


@pytest.fixture
def pdb_file(tmp_path: Path, biotite_structure: AtomArray) -> Path:
    """PDB structure file for testing."""
    path = tmp_path / "structure.pdb"
    file = pdb.PDBFile()
    file.set_structure(biotite_structure)
    file.write(path)
    return path


@pytest.fixture
def cif_file(tmp_path: Path, biotite_structure: AtomArray) -> Path:
    """CIF structure file for testing."""
    path = tmp_path / "structure.cif"
    file = pdbx.CIFFile()
    pdbx.set_structure(file, biotite_structure)
    file.write(path)
    return path


@pytest.fixture
def bcif_file(tmp_path: Path, biotite_structure: AtomArray) -> Path:
    """Binary CIF structure file for testing."""
    path = tmp_path / "structure.bcif"
    file = pdbx.BinaryCIFFile()
    pdbx.set_structure(file, biotite_structure)
    file.write(path)
    return path


def test_structure_from_manifest_section_with_pdb(pdb_file: Path) -> None:
    """A Structure can be created from a manifest section with PDB file."""
    section = StructureManifestSection(path=pdb_file)

    structure = Structure.from_manifest_section(section)

    assert structure.name == "structure"
    assert isinstance(structure.value, AtomArray)


def test_structure_from_manifest_section_with_cif(cif_file: Path) -> None:
    """A Structure can be created from a manifest section with CIF file."""
    section = StructureManifestSection(path=cif_file)

    structure = Structure.from_manifest_section(section)

    assert structure.name == "structure"
    assert isinstance(structure.value, AtomArray)


def test_structure_from_manifest_section_with_bcif(bcif_file: Path) -> None:
    """A Structure can be created from a manifest section with Binary CIF file."""
    section = StructureManifestSection(path=bcif_file)

    structure = Structure.from_manifest_section(section)

    assert structure.name == "structure"
    assert isinstance(structure.value, AtomArray)


def test_structure_from_manifest_section_structure_id_as_stem(pdb_file: Path) -> None:
    """The structure ID is set to the file stem."""
    section = StructureManifestSection(path=pdb_file)

    structure = Structure.from_manifest_section(section)

    assert structure.name == pdb_file.stem


def test_structure_from_manifest_section_structure_id_as_name(pdb_file: Path) -> None:
    """The structure ID is set to the new name."""
    section = StructureManifestSection(path=pdb_file, name="new_structure")

    structure = Structure.from_manifest_section(section)

    assert structure.name == "new_structure"


def test_structure_dump_to_pdb(tmp_path: Path, biotite_structure: AtomArray) -> None:
    """A Structure can be dumped to a PDB file."""
    structure = Structure(name="test", value=biotite_structure)

    path = structure.dump(path=tmp_path)

    loaded_file = pdb.PDBFile.read(path)
    loaded_structure = loaded_file.get_structure(model=1)
    # Compare only coordinates and basic annotations for simplicity in test
    assert np.allclose(loaded_structure.coord, biotite_structure.coord)
    assert np.array_equal(loaded_structure.res_name, biotite_structure.res_name)


def test_structure_dump_to_cif(tmp_path: Path, biotite_structure: AtomArray) -> None:
    """A Structure can be dumped to a cif file."""
    structure = Structure(name="test", value=biotite_structure)

    path = structure.dump(path=tmp_path, fmt=StructureFormat.MMCIF)

    loaded_file = pdbx.CIFFile.read(path)
    loaded_structure = pdbx.get_structure(loaded_file, model=1)
    assert np.allclose(loaded_structure.coord, biotite_structure.coord)
    assert np.array_equal(loaded_structure.res_name, biotite_structure.res_name)


def test_structure_dump_to_bcif(tmp_path: Path, biotite_structure: AtomArray) -> None:
    """A Structure can be dumped to a binary cif file."""
    structure = Structure(name="test", value=biotite_structure)

    path = structure.dump(path=tmp_path, fmt=StructureFormat.BINARY_CIF)

    loaded_file = pdbx.BinaryCIFFile.read(path)
    loaded_structure = pdbx.get_structure(loaded_file, model=1)
    assert np.allclose(loaded_structure.coord, biotite_structure.coord)
    assert np.array_equal(loaded_structure.res_name, biotite_structure.res_name)


def test_dataset_with_structures(
    pdb_file: Path, cif_file: Path, biotite_structure: AtomArray
) -> None:
    """A Dataset can be created with structures from the manifest."""
    structure1_val = biotite_structure.copy()
    structure2_val = biotite_structure.copy()
    manifest = Manifest(
        version=MANIFEST_LATEST_VERSION,
        name="test",
        structures=[
            StructureManifestSection(path=pdb_file, name="structure1"),
            StructureManifestSection(path=cif_file, name="structure2"),
        ],
    )
    dataset = Dataset.from_manifest(manifest)

    assert len(dataset.structures) == 2
    assert np.allclose(dataset.structures[0].value.coord, structure1_val.coord)
    assert np.allclose(dataset.structures[1].value.coord, structure2_val.coord)


def test_dataset_dump_with_structure(
    tmp_path: Path, biotite_structure: AtomArray
) -> None:
    """The dataset can be dumped with structures.

    The created archive:
    - Should not contain a bad file.
    - Should contain the structure file.
    - Should result the structure being loaded correctly.
    """
    structure = Structure(name="test", value=biotite_structure)
    dataset = Dataset(name="test", structures=[structure])

    path = dataset.dump(path=tmp_path)

    zip_ = ZipFile(path)
    assert not zip_.testzip(), "Dataset dump contains a bad file."
    assert "structures/test.pdb" in zip_.namelist(), (
        "Structure file not found in dataset dump."
    )

    with zip_.open("structures/test.pdb", "r") as structure_file:
        # Biotite can read from string/bytes-like objects using io.StringIO/BytesIO
        # or just passing the content if it supports it.
        # PDBFile.read takes a file path or file-like object.
        content = structure_file.read().decode("utf-8")
        string_io = io.StringIO(content)
        loaded_file = pdb.PDBFile.read(string_io)
        loaded_structure = loaded_file.get_structure(model=1)
        assert np.allclose(biotite_structure.coord, loaded_structure.coord)


def test_dataset_dump_with_structures_contains_archive_names(
    tmp_path: Path, biotite_structure: AtomArray
) -> None:
    """Same as `test_dataset_dump_with_structure`, but with multiple structures."""
    expected = {"structures/structure1.pdb", "structures/structure2.pdb"}
    structure1 = Structure(name="structure1", value=biotite_structure)
    structure2 = Structure(name="structure2", value=biotite_structure)
    dataset = Dataset(name="test", structures=[structure1, structure2])

    path = dataset.dump(path=tmp_path)

    archive_names = ZipFile(path).namelist()
    assert not expected - set(archive_names), (
        f"Expected the following archive names {expected}"
    )


def test_dataset_with_structure_dump_from_path_unit(
    tmp_path: Path, biotite_structure: AtomArray
) -> None:
    """Dumping a dataset with structure should return the same after reading"""
    structure = Structure(name="test_struct", value=biotite_structure)
    dataset = Dataset(name="test", structures=[structure])

    path = dataset.dump(path=tmp_path)

    loaded_dataset = Dataset.from_path(path)

    assert loaded_dataset.name == dataset.name
    assert len(loaded_dataset.structures) == len(dataset.structures)
    for loaded_structure, structure in zip(
        loaded_dataset.structures, dataset.structures, strict=True
    ):
        assert loaded_structure.name == structure.name
        assert loaded_structure == structure


def test_dataset_fails_with_duplicate_structure_names() -> None:
    """A dataset fails if there are duplicate structure names."""
    duplicate_names = ["duplicate1", "duplicate2"]
    structure1 = Structure(name=duplicate_names[0], value=AtomArray(0))
    structure2 = Structure(name=duplicate_names[0], value=AtomArray(0))
    structure3 = Structure(name=duplicate_names[1], value=AtomArray(0))
    structure4 = Structure(name=duplicate_names[1], value=AtomArray(0))

    match = "Duplicate names found in `Dataset.structures`:.*" + ", ".join(
        duplicate_names
    )
    with pytest.raises(ValidationError, match=match):
        Dataset(
            name="test", structures=[structure1, structure2, structure3, structure4]
        )


def test_structure_repr(tmp_path: Path, biotite_structure: AtomArray) -> None:
    """Test the string representation of the Structure class."""
    structure = Structure(
        name="test structure",
        value=biotite_structure,
        description="A test structure",
        metadata={"key1": "value1", "key2": "value2"},
    )

    repr_str = repr(structure)
    assert "Structure(\n\tname='test structure'," in repr_str
    assert "description: A test structure," in repr_str
    assert "value: Type[AtomArray]," in repr_str
    assert "\tmetadata:" in repr_str
    assert "\t\tkey1: value1," in repr_str
    assert "\t\tkey2: value2," in repr_str

    long_desc = "A" * 61 + "BCD"
    structure = Structure(
        name="longdesc",
        value=biotite_structure,
        description=long_desc,
        metadata={},
    )
    repr_str = repr(structure)
    assert f"description: {long_desc[:60]}..." in repr_str

    structure = Structure(
        name="nodesc",
        value=biotite_structure,
        description=None,
        metadata={},
    )
    repr_str = repr(structure)
    assert "description: None," in repr_str

    structure = Structure(
        name="nometa",
        value=biotite_structure,
        description="desc",
        metadata={},
    )
    repr_str = repr(structure)
    assert "\tmetadata: 0," in repr_str

    long_value = "X" * 65
    structure = Structure(
        name="longmeta",
        value=biotite_structure,
        description="desc",
        metadata={"longkey": long_value},
    )
    repr_str = repr(structure)
    assert f"\t\tlongkey: {long_value[:60]}..." in repr_str

@pytest.fixture
def biotite_structure() -> AtomArray:
    """Minimal biotite structure for testing."""
    atom = Atom(
        res_name="GLY",
        atom_name="CA",
        res_id=1,
        chain_id="A",
        coord=np.array([10.0, 20.0, 30.0]),
        element="C",
        hetero=False,
        occupancy=1.0,
        b_factor=20.0,
    )
    array = AtomArray(1)
    array[0] = atom
    return array

def test_structure_equality_mismatch_type(biotite_structure):
    s1 = Structure(name="s1", value=biotite_structure)
    assert s1 != "not a structure"

def test_structure_equality_mismatch_length(biotite_structure):
    s1 = Structure(name="s1", value=biotite_structure)
    
    array2 = AtomArray(2)
    array2[0] = biotite_structure[0]
    array2[1] = biotite_structure[0]
    s2 = Structure(name="s1", value=array2)
    
    assert s1 != s2

def test_structure_equality_mismatch_coords(biotite_structure):
    s1 = Structure(name="s1", value=biotite_structure)
    
    array2 = biotite_structure.copy()
    array2.coord[0] = [0.0, 0.0, 0.0]
    s2 = Structure(name="s1", value=array2)
    
    assert s1 != s2

def test_structure_equality_mismatch_annotation_categories(biotite_structure):
    s1 = Structure(name="s1", value=biotite_structure)
    
    array2 = biotite_structure.copy()
    array2.add_annotation("new_cat", dtype=int)
    array2.new_cat = np.array([1])
    
    s2 = Structure(name="s1", value=array2)
    
    assert s1 != s2

def test_structure_equality_mismatch_annotation_values(biotite_structure):
    s1 = Structure(name="s1", value=biotite_structure)
    
    array2 = biotite_structure.copy()
    array2.res_id[0] = 999
    
    s2 = Structure(name="s1", value=array2)
    
    assert s1 != s2

def test_structure_from_manifest_section_unsupported_format(tmp_path):
    path = tmp_path / "test.unsupported"
    path.touch()
    section = StructureManifestSection(path=path)
    with pytest.raises(NotImplementedError, match="Unsupported file type"):
        Structure.from_manifest_section(section)

def test_structure_dump_unsupported_format(biotite_structure):
    s = Structure(name="test", value=biotite_structure)
    class MockFormat:
        value = ".xyz"
    with pytest.raises(NotImplementedError, match="Unsupported file type"):
        s.dump(fmt=MockFormat()) # type: ignore

def test_structure_not_equals_integer():
    """A structure should equal itself."""
    structure = Structure(
        name="Test Structure",
        value=AtomArray(0),
        description=None,
        metadata={},
    )
    assert structure != 1

def test_structure_equals_itself():
    """A structure should equal itself."""
    structure = Structure(
        name="Test Structure",
        value=AtomArray(0),
        description=None,
        metadata={},
    )
    assert structure == structure

def test_structure_with_data_equals_itself():
    """A structure with data should equal itself."""
    structure = Structure(
        name="Test Structure",
        value=AtomArray(0),
        description="A test structure",
        metadata={"source": "test"},
    )
    assert structure == structure