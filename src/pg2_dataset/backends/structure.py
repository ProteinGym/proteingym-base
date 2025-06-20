from pathlib import Path
from typing import ClassVar, Generic, Self, TypeVar

from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr

from pg2_dataset.primitives.managers import AbstractStructureManager
from pg2_dataset.primitives.meta import StructuresMeta

try:
    import biotite.structure.io.pdb as pdb
    import biotite.structure.io.pdbx as pdbx
    from biotite.structure import AtomArray
except ImportError:
    pass

try:
    from Bio.PDB import MMCIFParser, PDBParser
    from Bio.PDB.binary_cif import BinaryCIFParser
    from Bio.PDB.Structure import Structure
except ImportError:
    pass

STRUCTURE = TypeVar("STRUCTURE")


class Structure(BaseModel, Generic[STRUCTURE]):
    """A dataset class for handling protein structure data.

    This class uses dependency injection for structure management,
    supporting both Biotite and Biopython backends.
    """

    meta: StructuresMeta
    structures: dict[str, STRUCTURE] = Field(default_factory=dict)
    _manager: AbstractStructureManager[STRUCTURE] = PrivateAttr(default=None)

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
                    self._manager = manager_cls(meta=self.meta)
                except ImportError as e:
                    logger.warning(str(e))
                    return self

            fp = Path(self.meta.file_path).resolve()
            if fp.is_dir():
                ids = [f.name for f in fp.iterdir()]
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


class BiotiteStructureManager(AbstractStructureManager["AtomArray"]):
    """Structure manager implementation using Biotite backend."""

    def __init__(self, meta: StructuresMeta = None):
        self.meta = meta

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
            return pdbx.CIFFile.read(fn)
        elif fn_ext.endswith(".bcif"):
            return pdbx.BinaryCIFFile.read(fn)
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


class BiopythonStructureManager(AbstractStructureManager["Structure"]):
    """Structure manager implementation using Biopython backend."""

    def __init__(self, meta: StructuresMeta = None):
        self.meta = meta

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
