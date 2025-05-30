from importlib.util import find_spec
from pathlib import Path
from typing import ClassVar

import pytest

from pg2_dataset.backends.structure_dataset import (
    STRUCTURE,
    AbstractStructureManager,
    BackendSearchOrder,
    StructureDataset,
)
from pg2_dataset.primitives.meta import StructuresMeta

TEST_DATA_DIR = str(Path(__file__).parent.parent / "test_data" / "structures")


@pytest.mark.skipif(
    not find_spec("Bio") and not find_spec("biotite"), reason="no structure backend"
)
class TestStructureDataset:
    @pytest.fixture
    def structure_files(self):
        test_data_path = Path(TEST_DATA_DIR)
        return {
            "pdb": str(test_data_path / "5kua_pdb.pdb"),
            "cif": str(test_data_path / "5kua_cif.cif"),
            "bcif": str(test_data_path / "5kua_bcif.bcif"),
        }

    @pytest.mark.parametrize("backend", ["Bio", "biotite"])
    def test_structure_manager_initialization(self, structure_files, backend: str):
        if not find_spec(backend):
            pytest.mark.skip(f"{backend} is not installed")
        with BackendSearchOrder([backend]):
            manager = AbstractStructureManager.get_available_manager()
            assert manager.name == backend
            structures = manager.load_structures(["test"], [structure_files["pdb"]])
            assert structures is not None
            assert len(structures) == 1

            dataset = StructureDataset(
                meta=StructuresMeta(file_path=structure_files["pdb"])
            )
            assert dataset._manager.name == backend
            assert len(dataset.structures) == 1

    @pytest.mark.parametrize(
        "file_format,backend",
        [
            ("pdb", "biotite"),
            ("cif", "biotite"),
            ("bcif", "biotite"),
            ("pdb", "Bio"),
            ("cif", "Bio"),
            ("bcif", "Bio"),
        ],
    )
    def test_file_format_loading(self, structure_files, file_format, backend):
        if not find_spec(backend):
            pytest.mark.skip(f"{backend} is not installed")
        with BackendSearchOrder([backend]):
            manager_cls = AbstractStructureManager.get_available_manager()
            manager = manager_cls()

        assert (
            manager.load_structure(structure_files[file_format], idn="test") is not None
        )

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
            StructureDataset(meta=StructuresMeta(file_path="nonexistent_file.pdb"))

    def test_unsupported_file_format(self, tmpdir):
        invalid_file = tmpdir / "test.xyz"
        invalid_file.write("dummy content")
        with pytest.raises(ValueError):
            dataset = StructureDataset(meta=StructuresMeta(file_path=str(invalid_file)))
            print(dataset)

    def test_no_backend_available(self, structure_files, monkeypatch):
        # noinspection PyUnusedLocal
        class FooStructureManager(AbstractStructureManager["Structure"]):
            """Structure manager implementation using Biopython backend."""

            name: ClassVar[str] = "Foo"

            @staticmethod
            def load_structures(ids: list[str], file_names: list[str]): ...

            @staticmethod
            def load_structure(fn: str, idn: str = "") -> STRUCTURE: ...

        with pytest.raises(ImportError):
            with BackendSearchOrder(["Foo"]):
                AbstractStructureManager.get_available_manager()