import os
from importlib.util import find_spec

import pytest

from pg2_dataset.backends.structure import (
    BiopythonStructureManager,
    BiotiteStructureManager,
    StructureDataset,
)

TEST_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "test_data", "structures"
)


class TestStructureDataset:
    @pytest.fixture
    def structure_files(self):
        return {
            "pdb": os.path.join(TEST_DATA_DIR, "5kua_pdb.pdb"),
            "cif": os.path.join(TEST_DATA_DIR, "5kua_cif.cif"),
            "bcif": os.path.join(TEST_DATA_DIR, "5kua_bcif.bcif"),
        }

    def test_dataset_initialization_with_biotite(self, structure_files):
        try:
            find_spec("biotite")

            # Save original managers state
            original_managers = StructureDataset.managers.copy()
            # Clear managers and register only Biotite
            StructureDataset.managers.clear()
            StructureDataset.managers["biotite"] = BiotiteStructureManager

            dataset = StructureDataset(file_path=structure_files["pdb"])
            assert isinstance(dataset, BiotiteStructureManager)
            assert len(dataset.structures) == 1

            # Restore original managers
            StructureDataset.managers = original_managers
        except ImportError:
            pytest.skip("biotite not installed")

    def test_dataset_initialization_with_biopython(self, structure_files):
        try:
            find_spec("Bio")

            original_managers = StructureDataset.managers.copy()
            StructureDataset.managers.clear()
            StructureDataset.managers["biopython"] = BiopythonStructureManager

            dataset = StructureDataset(file_path=structure_files["pdb"])
            assert isinstance(dataset, BiopythonStructureManager)
            assert len(dataset.structures) == 1

            StructureDataset.managers = original_managers
        except ImportError:
            pytest.skip("biopython not installed")

    def test_load_directory_of_structures(self, structure_files):
        try:
            find_spec("Bio")
            find_spec("biotite")

            dataset = StructureDataset(file_path=TEST_DATA_DIR)
            assert len(dataset.structures) > 1
            assert all(
                isinstance(s, type(next(iter(dataset.structures.values()))))
                for s in dataset.structures.values()
            )
        except ImportError:
            pytest.skip("biotite/biopython not installed")

    def test_biotite_structure_loading(self, structure_files):
        try:
            find_spec("biotite")

            manager = BiotiteStructureManager(file_path=structure_files["pdb"])
            assert len(manager.structures) == 1

            for _, path in structure_files.items():
                structure = manager.load_structure(path)
                assert structure is not None
        except ImportError:
            pytest.skip("biotite not installed")

    def test_biopython_structure_loading(self, structure_files):
        try:
            find_spec("Bio")

            manager = BiopythonStructureManager(file_path=structure_files["pdb"])
            assert len(manager.structures) == 1

            # Test different file formats
            for _, path in structure_files.items():
                structure = manager.load_structure("test", path)
                assert structure is not None
        except ImportError:
            pytest.skip("biopython not installed")

    def test_invalid_file_path(self):
        with pytest.raises(ValueError):
            StructureDataset(file_path="nonexistent_file.pdb")

    def test_unsupported_file_format(self, tmpdir):
        invalid_file = tmpdir / "test.xyz"
        invalid_file.write("dummy content")
        with pytest.raises(ValueError):
            dataset = StructureDataset(file_path=str(invalid_file))
            print(dataset)

    def test_no_backend_available(self, structure_files):
        original_managers = StructureDataset.managers.copy()
        StructureDataset.managers.clear()

        with pytest.raises(ImportError):
            StructureDataset(file_path=structure_files["pdb"])

        StructureDataset.managers = original_managers
