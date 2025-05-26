import os
from typing import ClassVar, Generic, Self, TypeVar
from warnings import warn

from pydantic import Field, model_validator

from pg2_dataset.backends.abstract_dataset import AbstractDataset

try:
    import biotite.structure.io.pdb as pdb
    import biotite.structure.io.pdbx as pdbx
except ImportError:
    biotite = None

try:
    from Bio.PDB import MMCIFParser, PDBParser
    from Bio.PDB.binary_cif import BinaryCIFParser
except ImportError:
    biopython = None

STRUCTURE = TypeVar("STRUCTURE", bound=["biotite", "biopython"])
SEARCH_ORDER = ("biopython", "biotite")


class StructureDataset(AbstractDataset, Generic[STRUCTURE]):
    """A dataset class for handling protein structure data.

    This class serves as a base for structure-specific dataset managers,
    supporting both Biotite and Biopython backends for structure handling.
    """

    file_path: str | None = None
    structures: dict = Field(default_factory=dict)
    managers: ClassVar[dict[str, type]] = {}

    def __init_subclass__(cls, **kwargs):
        """Register manager classes automatically based on class name.

        Requires a naming pattern of subclasses ending with StructureManager
        """
        if cls.__name__.endswith("StructureManager"):
            manager_type = cls.__name__.removesuffix("StructureManager").lower()
            cls.managers[manager_type] = cls

    def _select_manager_class(self):
        """Select appropriate manager class based on available libraries.

        Returns:
            type: The selected manager class.

        Raises:
            ImportError: If no suitable structure manager is found.
        """
        for manager_type in SEARCH_ORDER:
            manager_cls = self.managers.get(manager_type)
            if manager_cls:
                return manager_cls
        raise ImportError(
            "No suitable structure manager found. "
            "Please install either biopython or biotite."
        )

    def __init__(self, **data):
        """Initialize the StructureDataset.

        If instantiated directly, selects and initializes appropriate manager subclass.
        Otherwise, delegates to parent class initialization.

        Args:
            **data: Keyword arguments for dataset initialization.
        """
        if type(self) is StructureDataset:
            manager_cls = self._select_manager_class()
            self.__class__ = manager_cls
            self.__init__(**data)
        else:
            super().__init__(**data)

    def load_structures(
        self, id_list: list[str], fn_list: list[str]
    ) -> dict[str, STRUCTURE]:
        """Load multiple structures from files.

        Args:
            id_list: List of structure identifiers.
            fn_list: List of file paths corresponding to the structures.

        Returns:
            dict[str, STRUCTURE]: Dictionary mapping structure IDs to loaded structures.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement load_structures")

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
        if self.file_path:
            fp = os.path.abspath(self.file_path)
            if os.path.isdir(fp):
                id_list = os.listdir(fp)
                assert len(id_list) == len(set(id_list)), (
                    "Multiple files with same name found"
                )

                fn_list = [os.path.join(self.file_path, file) for file in id_list]
                self.structures = self.load_structures(id_list, fn_list)
                return self
            else:
                if os.path.isfile(fp):
                    structure_id = os.path.basename(self.file_path)
                    self.structures = self.load_structures(
                        [structure_id], [self.file_path]
                    )
                    return self
                else:
                    raise ValueError(f"No (correct) structure file path provided: {fp}")
        else:
            warn("No (correct) structure file path provided.", stacklevel=2)
            return None

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


class BiotiteStructureManager(StructureDataset["biotite"]):
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
        if type(fn) is not str:
            raise TypeError(
                "File path must be a string,"
                "did you mean to call .load_structures instead?"
            )

        if fn.endswith(".pdb"):
            return pdb.PDBFile.read(fn).get_structure()
        elif fn.endswith(".cif"):
            return pdbx.CIFFile.read(fn)
        elif fn.endswith(".bcif"):
            return pdbx.BinaryCIFFile.read(fn)
        else:
            raise ValueError(
                "File type not supported. "
                "Biotite supports the following formats:"
                "pdb (.pdb), mmcif (.cif) and binary cif (.bcif)"
            )

    def load_structures(self, id_list: list, fn_list: list) -> any:
        """Load multiple structures from files using Biotite.

        Args:
            id_list: List of structure identifiers.
            fn_list: List of file paths to the structures.

        Returns:
            dict: Dictionary mapping structure IDs to their corresponding
            structure objects.
        """
        structures = {}
        for idn, fn in zip(id_list, fn_list, strict=True):
            structures[idn] = self.load_structure(fn)

        return structures


class BiopythonStructureManager(StructureDataset["biopython"]):
    """Structure manager implementation using Biopython backend."""

    def load_structures(self, id_list: list[str], fn_list: list[str]) -> dict[str, any]:
        """Load multiple structures from files using Biopython.

        Args:
            id_list: List of structure identifiers.
            fn_list: List of file paths to the structures.

        Returns:
            dict[str, any]: Dictionary mapping structure IDs to their corresponding
            structure objects.
        """
        structures = {}
        for idn, fn in zip(id_list, fn_list, strict=True):
            structures[idn] = self.load_structure(idn, fn)
        return structures

    def load_structure(self, idn, fn) -> any:
        """Load a single structure from a file using Biopython.

        Args:
            idn: Structure identifier.
            fn: Path to the structure file.

        Returns:
            any: Loaded structure object.

        Raises:
            ValueError: If file type is not supported (.cif, .pdb, .bcif).
        """
        if fn.endswith(".pdb"):
            return PDBParser().get_structure(idn, fn)
        elif fn.endswith(".cif"):
            return MMCIFParser().get_structure(idn, fn)
        elif fn.endswith(".bcif"):
            return BinaryCIFParser().get_structure(idn, fn)
        else:
            raise ValueError(
                "File type not supported. "
                "Biopython supports the following formats:"
                "pdb (.pdb), mmcif (.cif) and binary cif (.bcif)"
            )
