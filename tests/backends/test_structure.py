from importlib.util import find_spec
from pathlib import Path

import pytest

from pg2_dataset.backends.structure_dataset import (
    BiopythonStructureManager,
    BiotiteStructureManager,
    StructureDataset,
    StructureManager,
)
from pg2_dataset.primitives.meta import StructuresMeta

TEST_DATA_DIR = str(Path(__file__).parent.parent / "test_data" / "structures")


class TestStructureDataset:
    @pytest.fixture
    def structure_files(self):
        test_data_path = Path(TEST_DATA_DIR)
        return {
            "pdb": str(test_data_path / "5kua_pdb.pdb"),
            "cif": str(test_data_path / "5kua_cif.cif"),
            "bcif": str(test_data_path / "5kua_bcif.bcif"),
        }

    @pytest.mark.parametrize(
        "manager_class",
        [
            pytest.param(
                BiotiteStructureManager,
                marks=pytest.mark.skipif(
                    not find_spec("biotite"), reason="biotite not installed"
                ),
            ),
            pytest.param(
                BiopythonStructureManager,
                marks=pytest.mark.skipif(
                    not find_spec("Bio"), reason="biopython not installed"
                ),
            ),
        ],
    )
    def test_structure_manager_initialization(self, structure_files, manager_class):
        manager = manager_class()

        structures = manager.load_structures(["test"], [structure_files["pdb"]])
        assert structures is not None
        assert len(structures) == 1

        # Test creating a dataset with this manager type
        # We need to monkeypatch get_available_manager to
        # return our specific manager class
        # to ensure the validator doesn't override our choice
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(StructureManager, "get_available_manager", lambda: manager_class)
            dataset = StructureDataset(
                meta=StructuresMeta(file_path=structure_files["pdb"])
            )
            assert isinstance(dataset._manager, manager_class)
            assert len(dataset.structures) == 1

    @pytest.mark.parametrize(
        "file_format,manager_class",
        [
            pytest.param(
                "pdb",
                BiotiteStructureManager,
                marks=pytest.mark.skipif(
                    not find_spec("biotite"), reason="biotite not installed"
                ),
            ),
            pytest.param(
                "cif",
                BiotiteStructureManager,
                marks=pytest.mark.skipif(
                    not find_spec("biotite"), reason="biotite not installed"
                ),
            ),
            pytest.param(
                "bcif",
                BiotiteStructureManager,
                marks=pytest.mark.skipif(
                    not find_spec("biotite"), reason="biotite not installed"
                ),
            ),
            pytest.param(
                "pdb",
                BiopythonStructureManager,
                marks=pytest.mark.skipif(
                    not find_spec("Bio"), reason="biopython not installed"
                ),
            ),
            pytest.param(
                "cif",
                BiopythonStructureManager,
                marks=pytest.mark.skipif(
                    not find_spec("Bio"), reason="biopython not installed"
                ),
            ),
            pytest.param(
                "bcif",
                BiopythonStructureManager,
                marks=pytest.mark.skipif(
                    not find_spec("Bio"), reason="biopython not installed"
                ),
            ),
        ],
    )
    def test_file_format_loading(self, structure_files, file_format, manager_class):
        manager = manager_class()

        if manager_class == BiotiteStructureManager:
            structure = manager.load_structure(structure_files[file_format])
        else:  # BiopythonStructureManager
            structure = manager.load_structure("test", structure_files[file_format])

        assert structure is not None

    def test_load_directory_of_structures(self, structure_files):
        if not any([find_spec("Bio"), find_spec("biotite")]):
            pytest.skip("neither biotite nor biopython installed")

        dataset = StructureDataset(meta=StructuresMeta(file_path=TEST_DATA_DIR))
        assert len(dataset.structures) > 1
        assert all(
            isinstance(s, type(next(iter(dataset.structures.values()))))
            for s in dataset.structures.values()
        )

    def test_invalid_file_path(self):
        with pytest.raises(ValueError):
            StructureDataset(file_path="nonexistent_file.pdb")

    def test_unsupported_file_format(self, tmpdir):
        invalid_file = tmpdir / "test.xyz"
        invalid_file.write("dummy content")
        with pytest.raises(ValueError):
            dataset = StructureDataset(file_path=str(invalid_file))
            print(dataset)

    def test_no_backend_available(self, structure_files, monkeypatch):
        def mock_get_available_manager(*args, **kwargs):
            raise ImportError("No suitable structure manager found")

        monkeypatch.setattr(
            StructureManager, "get_available_manager", mock_get_available_manager
        )

        with pytest.raises(ImportError):
            StructureDataset(meta=StructuresMeta(file_path=structure_files["pdb"]))
