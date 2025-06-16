import sys
from abc import ABC, abstractmethod
from importlib.util import find_spec
from pathlib import Path
from typing import ClassVar, Generic, Self, TypeVar

from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr

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

MSA = TypeVar("MSA")
search_order = ["Bio", "biotite"]


class BackendSearchOrder:
    def __init__(self, order: list[str]):
        self.order = order

    def __enter__(self):
        sys.modules[__name__].search_order = self.order

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.modules[__name__].search_order = ["Bio", "biotite"]


class AbstractMSAManager(ABC, Generic[STRUCTURE]):
    """Base class for MSA managers that handle loading multiple sequence alignments."""

    name: ClassVar[str] = ""
    backend_map: ClassVar[dict] = {}

    def __init_subclass__(cls, **kwargs):
        cls.backend_map[cls.name] = cls, find_spec(cls.name)

    @classmethod
    def get_available_manager(cls) -> type["AbstractMSAManager"]:
        """Get an appropriate MSA manager based on available libraries.

        Returns:
            type[AbstractMSAManager]: The selected manager class.

        Raises:
            ImportError: If no suitable MSA manager is found.
        """

        for backend in search_order:
            manager_class, is_available = cls.backend_map[backend]
            if is_available:
                return manager_class
        raise ImportError(
            "No suitable MSA manager found. Please install either biopython "
            "or biotite."
        )

    @staticmethod
    @abstractmethod
    def load_msas(file_names: list[str]) -> dict[str, MSA]:
        """Load MSA from file.

        Args:
            file_names: List of file paths corresponding to the MSA.

        Returns:
            dict[str, STRUCTURE]: Dictionary mapping msa IDs to loaded structures.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        ...

    @staticmethod
    @abstractmethod
    def load_msa(file_name: str) -> MSA: ...



class MSADataset(BaseModel, Generic[MSA]):
    """DocString"""
    meta: MSAMeta
    msa: dict[str, MSA] = Field(default_factory=dict)
    _manager: AbstractMSAManager = PrivateAttr(
        default_factory=AbstractMSAManager.get_available_manager
    )

    @property
    def sequences(self) -> list[str]:
        return list(self.msa.values())

    def model_post_init(self, *_, **__) -> Self:
        """Configure and load MSA based on the provided file path.

        Validates and processes the file_path, loading either a single MSA
        or multiple MSAs from a directory.

        Returns:
            Self: The configured dataset instance.

        Raises:
            ValueError: If no valid file path is provided or if the path is invalid.
        """
        if self.meta.file_path:
            # model post init runs before init is finished(?)
            if self._manager is None:
                try:
                    manager_cls = AbstractMSAManager.get_available_manager()
                    self._manager = manager_cls()
                except ImportError as e:
                    logger.warning(str(e))
                    return self

            fp = Path(self.meta.file_path).resolve()
            if fp.is_dir():
                fn_list = [str(fp / file) for file in fp.iterdir()]
                self.msa = self._manager.load_msas(fn_list)
                return self
            elif fp.is_file():
                self.msa = self._manager.load_msa(str(fp))
                return self
        else:
            logger.warning("No (correct) MSA file path provided.", stacklevel=2)

    def train(self):
        """Get the training split of the dataset.

        Raises:
            NotImplementedError: Split functionality not yet implemented.
        """
        raise NotImplementedError("MSADataset has no split implemented yet")

    def valid(self):
        """Get the validation split of the dataset.

        Raises:
            NotImplementedError: Split functionality not yet implemented.
        """
        raise NotImplementedError("MSADataset has no split implemented yet")

    def test(self):
        """Get the test split of the dataset.

        Raises:
            NotImplementedError: Split functionality not yet implemented.
        """
        raise NotImplementedError("MSADataset has no split implemented yet")


class BiotiteMSAManager(AbstractMSAManager):

    name: ClassVar[str] = "biotite"


    def load_msa(self, fp):
        file_handlers = {
            ".a3m": partial(self.from_a3m, self),
            ".a2m": partial(self.from_a2m, self),
            ".psi": partial(self.from_psi, self),
        }

        for extension, handler in file_handlers.items():
            if fp.endswith(extension):
                return handler(fp)

        raise ValueError(
            f"File {fp} is not a valid / supported MSA file. "
            f"Currently supported formats are: {', '.join(file_handlers.keys())}"
        )

    @staticmethod
    def load_msa(file_name: str) -> MSA:
        """
        Load an MSA from a file using Biotite.

        Args:
            file_name: Path to the MSA file.

        Returns:
            MSA: The loaded MSA object.
        """
        return BiotiteMSAManager.load_msa(file_name)

    @staticmethod
    def load_msas(file_names: list[str]) -> MSA:
    


    @staticmethod
    def _extract_record_name(header_line: str) -> str:
        """
        Extract the record name from a FASTA header line.
        If the name is in the format >tr|NAME|DESCRIPTION, extract NAME.
        Otherwise, use the full header (without the >).

        Args:
            header_line: The FASTA header line starting with '>'

        Returns:
            The extracted record name
        """
        # Remove the '>' character
        if header_line.startswith(">"):
            header = header_line[1:].strip()
        else:
            header = header_line.strip()

        # Check if the header has the format tr|NAME|DESCRIPTION
        pipe_match = re.match(r".*\|(.*?)\|", header)
        if pipe_match:
            return pipe_match.group(1)
        else:
            return header

    @classmethod
    def from_a2m(cls, self, file_path: str) -> any:
        """
        Parse an A2M file and return an MSA object.

        Args:
            file_path: Path to the A2M file

        Returns:
            MSA object with sequences and records
        """
        records = {}
        name = None
        seq = ""
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()
                if line.startswith(">"):
                    if name is not None:
                        records[name] = seq
                    name = self._extract_record_name(line)
                    seq = ""
                else:
                    seq += line

            # save last entry
            if name is not None:
                records[name] = seq

        if len({len(s) for s in records.values()}) > 1:
            raise ValueError("All sequences in A2M format must be of same length")

        return records

    @classmethod
    def from_a3m(cls, self, file_path: str) -> any:
        """
        Parse an A3M file and return an MSA object.

        Args:
            file_path: Path to the A3M file

        Returns:
            MSA object with sequences and records
        """
        records = {}
        name = None
        seq = ""
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()
                if line.startswith(">"):
                    if name is not None:
                        records[name] = seq
                    name = self._extract_record_name(line)
                    seq = ""
                else:
                    seq += line

            # save last entry
            if name is not None:
                records[name] = seq

        return records

    @classmethod
    def from_psi(cls, self, file_path: str) -> any:
        """
        Parse a PSI file and return an MSA object.

        Args:
            file_path: Path to the PSI file

        Returns:
            MSA object with sequences and records
        """

        records = {}
        with open(file_path, "r") as file:
            for line in file:
                header, sequence = line.strip().split()
                name = self._extract_record_name(header)
                records[name] = sequence

        return records
