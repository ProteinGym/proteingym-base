import logging
import sys
from abc import ABC, abstractmethod
from importlib.util import find_spec
from pathlib import Path
from typing import ClassVar, Generic, Self, TypeVar

from pydantic import BaseModel, Field, PrivateAttr

from pg2_dataset.primitives.meta import StructuresMeta

logger = logging.getLogger(__name__)

biotite_available = False
biopython_available = False

if find_spec("biotite"):
    import biotite.structure.io.pdb as pdb
    import biotite.structure.io.pdbx as pdbx
    from biotite.structure import AtomArray
    from biotite.structure.io import save_structure
    from biotite.structure.io.pdbx import get_structure

    biotite_available = True
else:
    biotite_available = False
if find_spec("Bio"):
    from Bio.PDB import MMCIFIO, PDBIO, MMCIFParser, PDBParser
    from Bio.PDB.binary_cif import BinaryCIFParser
    from Bio.PDB.Structure import Structure

    biopython_available = True
else:
    biotite_available = False

STRUCTURE = TypeVar("STRUCTURE")
search_order = ["Bio", "biotite"]


class BackendSearchOrder:
    def __init__(self, order: list[str]):
        self.order = order

    def __enter__(self):
        sys.modules[__name__].search_order = self.order

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.modules[__name__].search_order = ["Bio", "biotite"]


class AbstractStructureManager(ABC, Generic[STRUCTURE]):
    """Base class for structure managers that handle loading protein structures."""

    name: ClassVar[str] = ""
    backend_map: ClassVar[dict] = {}

    def __init_subclass__(cls, **kwargs):
        cls.backend_map[cls.name] = cls, find_spec(cls.name)

    @classmethod
    def get_available_manager(cls) -> type["AbstractStructureManager"]:
        """Get an appropriate structure manager based on available libraries.

        Returns:
            type[AbstractStructureManager]: The selected manager class.

        Raises:
            ImportError: If no suitable structure manager is found.
        """

        for backend in search_order:
            manager_class, is_available = cls.backend_map[backend]
            if is_available:
                return manager_class
        raise ImportError(
            "No suitable structure manager found. Please install either biopython "
            "or biotite."
        )

    @staticmethod
    @abstractmethod
    def load_structures(ids: list[str], file_names: list[str]) -> dict[str, STRUCTURE]:
        """Load multiple structures from files.

        Args:
            ids: List of structure identifiers.
            file_names: List of file paths corresponding to the structures.

        Returns:
            dict[str, STRUCTURE]: Dictionary mapping structure IDs to loaded structures.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        ...

    @staticmethod
    @abstractmethod
    def load_structure(fn: str, idn: str = "") -> STRUCTURE: ...

    @staticmethod
    @abstractmethod
    def dump_structure(structure: STRUCTURE, path: str | Path) -> None: ...


class Structure(BaseModel, Generic[STRUCTURE]):
    """A dataset class for handling protein structure data.

    This class uses dependency injection for structure management,
    supporting both Biotite and Biopython backends.
    """

    meta: StructuresMeta
    structures: dict[str, STRUCTURE] = Field(default_factory=dict)
    _manager: AbstractStructureManager[STRUCTURE] = PrivateAttr(
        default_factory=AbstractStructureManager.get_available_manager.__init__
    )

    def model_post_init(self, *_, **__) -> Self:
        """Configure and load structures based on the provided file path.

        Validates and processes the file_path, loading either a single structure
        or multiple structures from a directory.

        Returns:
            Self: The configured dataset instance.

        Raises:
            ValueError: If no valid file path is provided or if the path is invalid.
        """

        if self.meta.file_path:
            # model post init runs before init is finished(?)
            if self._manager is None:
                try:
                    manager_cls = AbstractStructureManager.get_available_manager()
                    self._manager = manager_cls()
                except ImportError as e:
                    logger.warning(str(e))
                    return self

            fp = Path(self.meta.file_path).resolve()
            if fp.is_dir():
                ids = [
                    f.name for f in fp.iterdir() if not f.name.startswith(".")
                ]  # skip hidden files
                if len(ids) != len(set(ids)):
                    raise ValueError(
                        "Directory contains multiple structures with same name"
                    )

                fn_list = [str(fp / file) for file in ids]
                self.structures = self._manager.load_structures(ids, fn_list)
                return self
            elif fp.is_file():
                structure_id = fp.name
                self.structures = self._manager.load_structures(
                    [structure_id], [str(fp)]
                )
                return self
            else:
                raise ValueError(f"No (correct) structure file path provided: {fp}")
        else:
            logger.warning("No (correct) structure file path provided.", stacklevel=2)
            return self

    def train(self):
        """Get the training split of the dataset.

        Raises:
            NotImplementedError: Split functionality not yet implemented.
        """
        raise NotImplementedError("StructureDataset has no split implemented yet")

    def valid(self):
        """Get the validation split of the dataset.

        Raises:
            NotImplementedError: Split functionality not yet implemented.
        """
        raise NotImplementedError("StructureDataset has no split implemented yet")

    def test(self):
        """Get the test split of the dataset.

        Raises:
            NotImplementedError: Split functionality not yet implemented.
        """
        raise NotImplementedError("StructureDataset has no split implemented yet")

    def dump(self, path: str | Path) -> None:
        """Save the structure dataset to a specified directory.
        Args:
            path: Directory path where the structures will be saved.
        Raises:
            ValueError: If the file type is not supported.
        """
        if not self.structures:
            raise ValueError("No structures to save.")

        self._manager.dump_structure(self, path)


class BiotiteStructureManager(AbstractStructureManager["AtomArray"]):
    """Structure manager implementation using Biotite backend."""

    name: ClassVar[str] = "biotite"

    @staticmethod
    def load_structure(fn: str, **_) -> STRUCTURE:
        """Load a single structure from a file using Biotite.

        Args:
            fn: Path to the structure file.

        Returns:
            any: Loaded structure object.

        Raises:
            TypeError: If file path is not a string.
            ValueError: If file type is not supported (.cif, .pdb, .bcif).
        """
        if not Path(fn):
            raise TypeError(
                "File path must be a path to file."
                "Did you mean to call .load_structures instead?"
            )

        fn_ext = Path(fn).suffix.lower()
        if fn_ext.endswith(".pdb"):
            return pdb.PDBFile.read(fn).get_structure()
        elif fn_ext.endswith(".cif"):
            return get_structure(pdbx.CIFFile.read(fn))
        elif fn_ext.endswith(".bcif"):
            return get_structure(pdbx.BinaryCIFFile.read(fn))
        else:
            raise ValueError(
                "File type not supported. "
                "Biotite supports the following formats:"
                "pdb (.pdb), mmcif (.cif) and binary cif (.bcif)"
            )

    @staticmethod
    def load_structures(
        ids: list[str], file_names: list[str]
    ) -> dict[str, "AtomArray"]:
        """Load multiple structures from files using Biotite.

        Args:
            ids: List of structure identifiers.
            file_names: List of file paths to the structures.

        Returns:
            dict: Dictionary mapping structure IDs to their corresponding
            structure objects.
        """
        structures = {}
        for idn, fn in zip(ids, file_names, strict=True):
            structures[idn] = BiotiteStructureManager.load_structure(fn)

        return structures

    @staticmethod
    def dump_structure(structure: Structure, path: str | Path) -> None:
        path = Path(path)

        for idn, stack in structure.structures.items():
            if idn.endswith(".pdb"):
                pdb_file = pdb.PDBFile()
                pdb_file.set_structure(stack)
                pdb_file.write(path / idn)

            elif idn.endswith(".cif") or idn.endswith(".bcif"):
                save_structure(str(path / idn), stack)

            else:
                raise ValueError(
                    "File type not supported. "
                    "Biotite supports the following formats:"
                    "pdb (.pdb), mmcif (.cif) and binary cif (.bcif)"
                )


class BiopythonStructureManager(AbstractStructureManager["Structure"]):
    """Structure manager implementation using Biopython backend."""

    name: ClassVar[str] = "Bio"

    @staticmethod
    def load_structures(
        ids: list[str], file_names: list[str]
    ) -> dict[str, "Structure"]:
        """Load multiple structures from files using Biopython.

        Args:
            ids: List of structure identifiers.
            file_names: List of file paths to the structures.

        Returns:
            dict[str, any]: Dictionary mapping structure IDs to their corresponding
            structure objects.
        """
        structures = {}
        for idn, fn in zip(ids, file_names, strict=True):
            structures[idn] = BiopythonStructureManager.load_structure(fn, idn)
        return structures

    @staticmethod
    def load_structure(fn: str, idn: str = "") -> STRUCTURE:
        """Load a single structure from a file using Biopython.

        Args:
            idn: Structure identifier.
            fn: Path to the structure file.

        Returns:
            any: Loaded structure object.

        Raises:
            ValueError: If file type is not supported (.cif, .pdb, .bcif).
        """
        if not idn:
            raise ValueError("Structure identifier must be provided.")

        if not Path(fn):
            raise TypeError(
                "File path must be a path to file."
                "Did you mean to call .load_structures instead?"
            )

        fn_ext = Path(fn).suffix.lower()
        if fn_ext.endswith(".pdb"):
            return PDBParser().get_structure(idn, fn)
        elif fn_ext.endswith(".cif"):
            return MMCIFParser().get_structure(idn, fn)
        elif fn_ext.endswith(".bcif"):
            return BinaryCIFParser().get_structure(idn, fn)
        else:
            raise ValueError(
                "File type not supported. "
                "Biopython supports the following formats:"
                "pdb (.pdb), mmcif (.cif) and binary cif (.bcif)"
            )

    @staticmethod
    def dump_structure(structure: Structure, path: str | Path) -> None:
        path = Path(path)

        for idn, stack in structure.structures.items():
            if idn.endswith(".pdb"):
                io = PDBIO()
                io.set_structure(stack)
                io.save(str(path / idn))

            elif idn.endswith(".cif"):
                io = MMCIFIO()
                io.set_structure(stack)
                io.save(str(path / idn))

            else:
                raise ValueError(
                    "File type not supported. "
                    "Biopython supports the following formats:"
                    "pdb (.pdb) and mmcif (.cif) for read and write,"
                    "and binary cif (.bcif) for read only."
                )
