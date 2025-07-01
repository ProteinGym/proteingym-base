import logging
from pathlib import Path
from typing import ClassVar, Generic, Self, TypeVar

from pydantic import BaseModel, Field, PrivateAttr

from pg2_dataset.primitives.managers import AbstractMSAManager
from pg2_dataset.primitives.meta import MSAMeta

try:
    import biotite.sequence.io.fasta as biotite_fasta
except ImportError:
    pass

try:
    from Bio import AlignIO
    from Bio.AlignIO import _FormatToIterator
except ImportError:
    pass

MSA = TypeVar("MSA")
logger = logging.getLogger(__name__)


class MSA(BaseModel, Generic[MSA]):
    """MSA loading class which takes the correct backend manager for
    specific request package according to search order in managers.py

    Args:
        Generic (MSA): Generic backend manager for MSA

    Raises:
        ValueError: When an incorrect filepath is provided
        NotImplementedError: When trying to call train/valid/test
    """

    meta: MSAMeta
    msa: dict[str, MSA] = Field(default_factory=dict)
    _manager: AbstractMSAManager = PrivateAttr(default=None)

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
    def __init__(self, meta: MSAMeta = None):
        self.meta = meta

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
    def __init__(self, meta: MSAMeta = None):
        self.meta = meta

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
