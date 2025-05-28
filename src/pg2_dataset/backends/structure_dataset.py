from abc import abstractmethod
from importlib.util import find_spec
from pathlib import Path
from typing import Generic, Self, TypeVar
from warnings import warn

from pydantic import model_validator

from pg2_dataset.backends.abstract_dataset import AbstractDataset
from pg2_dataset.primitives.meta import StructuresMeta

biotite_available = False
biopython_available = False

if find_spec("biotite"):
    import biotite.structure.io.pdb as pdb
    import biotite.structure.io.pdbx as pdbx
    from biotite.structure import AtomArray

    biotite_available = True
else:
    biotite_available = False
if find_spec("Bio"):
    from Bio.PDB import MMCIFParser, PDBParser
    from Bio.PDB.binary_cif import BinaryCIFParser
    from Bio.PDB.Structure import Structure

    biopython_available = True
else:
    biotite_available = False

STRUCTURE = TypeVar("STRUCTURE")
SEARCH_ORDER = ["biopython", "biotite"]


def create_backend_map():
    """helper function for determining which backend to use accoring to search order

    Returns:
        dict: Dictionary of StructureManagers with associated availability.
    """
    return {
        "biotite": (BiotiteStructureManager, biotite_available),
        "biopython": (BiopythonStructureManager, biopython_available),
    }


class StructureManager(Generic[STRUCTURE]):
    """Base class for structure managers that handle loading protein structures."""

    @classmethod
    def get_available_manager(cls) -> type["StructureManager"]:
        """Get an appropriate structure manager based on available libraries.

        Returns:
            type[StructureManager]: The selected manager class.

        Raises:
            ImportError: If no suitable structure manager is found.
        """

        backend_map = create_backend_map()

        for backend in SEARCH_ORDER:
            manager_class, is_available = backend_map[backend]
            if is_available:
                return manager_class
        raise ImportError(
            "No suitable structure manager found. "
            "Please install either biopython or biotite."
        )

    @abstractmethod
    def load_structures(
        self, ids: list[str], file_names: list[str]
    ) -> dict[str, STRUCTURE]:
        """Load multiple structures from files.

        Args:
            ids: List of structure identifiers.
            file_names: List of file paths corresponding to the structures.

        Returns:
            dict[str, STRUCTURE]: Dictionary mapping structure IDs to loaded structures.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement load_structures")


class StructureDataset(AbstractDataset, Generic[STRUCTURE]):
    """A dataset class for handling protein structure data.

    This class uses dependency injection for structure management,
    supporting both Biotite and Biopython backends.
    """

    meta: StructuresMeta
    structures: dict[str, STRUCTURE] = {}
    _manager: StructureManager[STRUCTURE] | None = None

    def __init__(self, **data):
        """Initialize the StructureDataset with an appropriate structure manager.

        Args:
            **data: Keyword arguments for dataset initialization.
        """
        super().__init__(**data)
        if self._manager is None:
            manager_cls = StructureManager.get_available_manager()
            self._manager = manager_cls()

    @model_validator(mode="after")
    def configure_structures(self) -> Self:
        """Configure and load structures based on the provided file path.

        Validates and processes the file_path, loading either a single structure
        or multiple structures from a directory.

        Returns:
            Self: The configured dataset instance.

        Raises:
            ValueError: If no valid file path is provided or if the path is invalid.
        """
        if self.meta:
            file_path = self.meta.file_path

        if file_path:
            if not any([biotite_available, biopython_available]):
                raise ImportError(
                    "Path to structure is provided,"
                    "but neither biopython nor biotite is installed. "
                    "Please install either biopython or biotite "
                )

            # model validator runs before init is finished:
            if self._manager is None:
                manager_cls = StructureManager.get_available_manager()
                self._manager = manager_cls()

            fp = Path(file_path).resolve()
            if fp.is_dir():
                ids = [f.name for f in fp.iterdir()]
                if len(ids) != len(set(ids)):
                    raise ValueError(
                        "Directory contains multiple structures with same name"
                    )

                fn_list = [str(fp / file) for file in ids]
                self.structures = self._manager.load_structures(ids, fn_list)
                return self
            else:
                if fp.is_file():
                    structure_id = fp.name
                    self.structures = self._manager.load_structures(
                        [structure_id], [str(fp)]
                    )
                    return self
                else:
                    raise ValueError(f"No (correct) structure file path provided: {fp}")
        else:
            warn("No (correct) structure file path provided.", stacklevel=2)
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


class BiotiteStructureManager(StructureManager[AtomArray]):
    """Structure manager implementation using Biotite backend."""

    def load_structure(self, fn: str) -> any:
        """Load a single structure from a file using Biotite.

        Args:
            fn: Path to the structure file.

        Returns:
            any: Loaded structure object.

        Raises:
            TypeError: If file path is not a string.
            ValueError: If file type is not supported (.cif, .pdb, .bcif).
        """
        # if type(fn) is not str:
        #     raise TypeError(
        #         "File path must be a string,"
        #         "did you mean to call .load_structures instead?"
        #     )

        if not Path(fn):
            raise TypeError(
                "File path must be a path to file."
                "Did you mean to call .load_structures instead?"
            )

        fn_ext = Path(fn).suffix.lower()
        if fn_ext.endswith(".pdb"):
            return pdb.PDBFile.read(fn).get_structure()
        elif fn_ext.endswith(".cif"):
            return pdbx.CIFFile.read(fn)
        elif fn_ext.endswith(".bcif"):
            return pdbx.BinaryCIFFile.read(fn)
        else:
            raise ValueError(
                "File type not supported. "
                "Biotite supports the following formats:"
                "pdb (.pdb), mmcif (.cif) and binary cif (.bcif)"
            )

    def load_structures(
        self, ids: list[str], file_names: list[str]
    ) -> dict[str, AtomArray]:
        """Load multiple structures from files using Biotite.

        Args:
            id_list: List of structure identifiers.
            fn_list: List of file paths to the structures.

        Returns:
            dict: Dictionary mapping structure IDs to their corresponding
            structure objects.
        """
        structures = {}
        for idn, fn in zip(ids, file_names, strict=True):
            structures[idn] = self.load_structure(fn)

        return structures


class BiopythonStructureManager(StructureManager[Structure]):
    """Structure manager implementation using Biopython backend."""

    def load_structures(
        self, ids: list[str], file_names: list[str]
    ) -> dict[str, Structure]:
        """Load multiple structures from files using Biopython.

        Args:
            id_list: List of structure identifiers.
            fn_list: List of file paths to the structures.

        Returns:
            dict[str, any]: Dictionary mapping structure IDs to their corresponding
            structure objects.
        """
        structures = {}
        for idn, fn in zip(ids, file_names, strict=True):
            structures[idn] = self.load_structure(idn, fn)
        return structures

    def load_structure(self, idn: str, fn: str) -> any:
        """Load a single structure from a file using Biopython.

        Args:
            idn: Structure identifier.
            fn: Path to the structure file.

        Returns:
            any: Loaded structure object.

        Raises:
            ValueError: If file type is not supported (.cif, .pdb, .bcif).
        """
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
