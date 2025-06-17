import sys
from abc import ABC, abstractmethod
from importlib.util import find_spec
from pathlib import Path
from typing import ClassVar, Generic, Self, TypeVar

from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr

from pg2_dataset.primitives.meta import MSAMeta

biotite_available = False
biopython_available = False

if find_spec("biotite"):
    import biotite.sequence.io.fasta as biotite_fasta

    biotite_available = True

if find_spec("Bio"):
    from Bio import AlignIO
    from Bio.AlignIO import _FormatToIterator

    biopython_available = True

MSA = TypeVar("MSA")
search_order = ["Bio", "biotite"]
# search_order = ["biotite", "Bio"]


class BackendSearchOrder:
    def __init__(self, order: list[str]):
        self.order = order

    def __enter__(self):
        sys.modules[__name__].search_order = self.order

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.modules[__name__].search_order = ["biopython", "biotite"]


class AbstractMSAManager(ABC, Generic[MSA]):
    """Base class for MSA managers that handle loading multiple sequence alignments."""

    name: ClassVar[str] = ""
    backend_map: ClassVar[dict] = {}

    def __init__(self, meta: MSAMeta = None):
        self.meta = meta

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
            "No suitable MSA manager found.Please install either biopython or biotite."
        )

    @abstractmethod
    def load_msas(self, file_names: list[str]) -> dict[str, MSA]:
        """Load MSA from file.

        Args:
            file_names: List of file paths corresponding to the MSA.

        Returns:
            dict[str, STRUCTURE]: Dictionary mapping msa IDs to loaded structures.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        ...

    @abstractmethod
    def load_msa(self, file_name: str) -> MSA: ...


class MSA(BaseModel, Generic[MSA]):
    """DocString"""

    meta: MSAMeta
    msa: dict[str, MSA] = Field(default_factory=dict)
    _manager: AbstractMSAManager = PrivateAttr(default=None)

    # @property
    # def alignments(self) -> list[str]:
    #     return list(self.msa.values())

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
                    self._manager = manager_cls(meta=self.meta)
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
                raise ValueError(f"No (correct) MSA file path provided: {fp}")
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

    def load_msa(self, file_name: str) -> MSA:
        """
        Load an MSA from a file using Biotite.

        Args:
            file_name: Path to the MSA file.

        Returns:
            MSA: The loaded MSA object.
        """
        if not Path(file_name):
            raise TypeError(
                "File path must be a path to file."
                "Did you mean to call .load_msas instead?"
            )

        fn_ext = Path(file_name).suffix.lower()
        if (fn_ext == ".fa") or (fn_ext == ".fasta"):
            msa_input = biotite_fasta.FastaFile.read(file_name)
            alignment = biotite_fasta.get_alignment(
                msa_input, additional_gap_chars=self.meta.gap_chars
            )
            return alignment
        else:
            raise ValueError(
                "Biotite contains limited support for MSA files."
                "Currently we only support aligned fasta files "
                "for biotite alignment loading"
                "If you need support for different alignment types, "
                "consider using the BioPython backend"
            )

    def load_msas(self, file_names: list[str]) -> dict[str, MSA]:
        """Load multiple MSAs from files using Biotite.

        Args:
            ids: List of structure identifiers.
            file_names: List of file paths to the structures.

        Returns:
            dict: Dictionary mapping structure IDs to their corresponding
            structure objects.
        """
        alignments = {}
        for fn in file_names:
            idn = Path(fn).name
            alignments[idn] = self.load_msa(fn)

        return alignments


class BiopythonMSAManager(AbstractMSAManager):
    name: ClassVar[str] = "Bio"
    allowed_formats: list[str] = list(_FormatToIterator.keys())
    # Fasta is taken from other module by default and not in OG list,
    # but its an allowed type.
    allowed_formats.extend(["fasta"])

    def load_msa(self, file_name: str) -> MSA:
        """
        Load an MSA from a file using Biopython.

        Args:
            file_name: Path to the MSA file.

        Returns:
            MSA: The loaded MSA object.
        """
        if not Path(file_name):
            raise TypeError(
                "File path must be a path to file."
                "Did you mean to call .load_msas instead?"
            )
        if self.meta.file_format in self.allowed_formats:
            alignment = AlignIO.read(file_name, self.meta.file_format)
            return alignment
        else:
            raise ValueError(
                f"Unexpected format, Biopython only allows: {self.allowed_formats}"
                f"For more information see:"
                f"https://biopython.org/wiki/AlignIO"
            )

    def load_msas(self, file_names: list[str]) -> dict[str, MSA]:
        """Load multiple MSAs from files using Biotite.

        Args:
            ids: List of structure identifiers.
            file_names: List of file paths to the structures.

        Returns:
            dict: Dictionary mapping structure IDs to their corresponding
            structure objects.
        """
        alignments = {}
        for fn in file_names:
            idn = Path(fn).name
            alignments[idn] = self.load_msa(fn)

        return alignments
