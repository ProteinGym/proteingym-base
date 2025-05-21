import os

from pydantic import Field, model_validator
from typing_extensions import Self

from pg2_dataset.backends.abstract_dataset import AbstractDataset

# Wanted to do in init but circular imports
# Any 'defaults' to place optional imports?
try:
    import biotite.structure.io.pdb as pdb
    import biotite.structure.io.pdbx as pdbx
except ImportError:
    _has_biotite = False
else:
    _has_biotite = True

try:
    from Bio.PDB import MMCIFParser, PDBParser
    from Bio.PDB.binary_cif import BinaryCIFParser
except ImportError:
    _has_biopython = False
    try:
        BinaryCIFParser = None
    except ImportError:
        _has_biopython = True
        _has_msgpack = False
else:
    _has_biopython = True
    _has_msgpack = True


class StructureDataset(AbstractDataset):
    structure_file_path: str | None = None
    structures: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def configure_structure_file_path(self) -> Self:
        if self.structure_file_path:
            return self

        elif (
            self.settings
            and self.settings.artifacts
            and self.settings.artifacts.structure
        ):
            self.structure_file_path = self.settings.artifacts.structure
            return self

        else:
            raise ValueError("No structure file path provided.")

    @model_validator(mode="after")
    def configure_structures(self) -> Self:
        """Checks if the file path given is a single structure or directory of
        structures and returns the structures

        Args:
            path: location of the structure files
        """
        if self.structure_file_path:
            fp = os.path.join(os.getcwd(), self.structure_file_path)
            if os.path.isdir(fp):
                id_list = os.listdir(fp)
                assert len(id_list) == len(set(id_list)), (
                    "Multiple files with same name found"
                )

                fn_list = [
                    os.path.join(self.structure_file_path, file) for file in id_list
                ]
                self.structures = self._load_structures(id_list, fn_list)
                return self
            else:
                if os.path.isfile(fp):
                    structure_id = self.structure_file_path.split("/")[-1]
                    self.structures = self._load_structures(
                        [structure_id], [self.structure_file_path]
                    )
                    return self
                else:
                    raise ValueError("No (correct) structure file path provided.")
        else:
            raise ValueError("No (correct) structure file path provided.")

    def train(self):
        raise NotImplementedError("StructureDataset has no split implemented yet")

    def valid(self):
        raise NotImplementedError("StructureDataset has no split implemented yet")

    def test(self):
        raise NotImplementedError("StructureDataset has no split implemented yet")

    def _load_structures(self, id_list: list, fn_list: list) -> list:
        """Loads in list of structures"""

        if _has_biopython:
            structures = self._load_biopython_structures(id_list, fn_list)
        elif _has_biotite:
            structures = self._load_biotite_structures(id_list, fn_list)
        else:
            raise ImportError("Biotite or Biopython not installed")
        return structures

    def _load_biotite_structures(self, id_list: list, fn_list: list) -> list:
        """Loads in list of biotite structures"""
        structures = {}
        for idn, fn in zip(id_list, fn_list, strict=False):
            structures[idn] = self._load_biotite_structure(fn)
        return structures

    def _load_biotite_structure_file(self, fn: str) -> any: #"Structure"?
        """Loads in the biotite structure file
        Allows for calling file if you want to access metadata"""

        # Kind of placeholder until we figure out how we want
        # to deal with fact that biotite separates structure
        # from file.

        if _has_biotite:
            if fn.endswith(".pdb"):
                return pdb.PDBFile.read(fn)
            if fn.endswith(".cif"):
                return pdbx.CIFFile.read(fn)
            if fn.endswith(".bcif"):
                return pdbx.BinaryCIFFile.read(fn)
        else:
            raise ImportError("Biotite not installed")

    def _load_biotite_structure(self, fn: str) -> any: #"Structure"?
        """Loads in biotite structure
        Allows for easy access to structural information only"""

        if type(fn) is list:
            raise TypeError(
                "File path must be a string,"
                "did you mean to call _load_biotite_structures?"
            )

        if _has_biotite:
            if fn.endswith(".pdb"):
                return pdb.PDBFile.read(fn).get_structure()
            if fn.endswith(".cif"):
                return pdbx.CIFFile.read(fn).get_structure()
            if fn.endswith(".bcif"):
                return pdbx.BinaryCIFFile.read(fn).get_structure()
        else:
            raise ImportError("Biotite not installed")

    def _load_biopython_structures(self, id_list, fn_list):
        """Loads in list of biopython structures"""
        structures = {}
        for idn, fn in zip(id_list, fn_list, strict=False):
            structures[idn] = self._load_biopython_structure(idn, fn)
        return structures

    def _load_biopython_structure(self, struc_id, fn) -> any: #"Structure"
        """Loads in biopython structure
        Allows to access the meta data associated with each structure file"""

        if _has_biopython:
            if fn.endswith(".pdb"):
                return PDBParser().get_structure(struc_id, fn)
            if fn.endswith(".cif"):
                return MMCIFParser().get_structure(struc_id, fn)
            if fn.endswith(".bcif"):
                if _has_msgpack:
                    return BinaryCIFParser().get_structure(struc_id, fn)
                else:
                    raise ImportError("Msgpack not installed")
        else:
            raise ImportError("Biopython not installed")
