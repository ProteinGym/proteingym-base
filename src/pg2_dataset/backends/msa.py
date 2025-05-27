import os
import re
from functools import partial
from warnings import warn

from pydantic import Field, model_validator

from pg2_dataset.backends.abstract_dataset import AbstractDataset


class MSADataset(AbstractDataset):
    file_path: str | None = ""
    msa: dict = Field(default_factory=dict)

    # do we need MSAMeta? Want kind of meta data?
    # meta: MSAMeta

    @property
    def sequences(self) -> list[str]:
        return list(self.msa.values())

    @model_validator(mode="after")
    def parse_msa_path(self):
        if self.file_path:
            fp = os.path.abspath(self.file_path)
            if os.path.isdir(fp):
                raise NotImplementedError("MSADataset does not support directories yet")
            if os.path.isfile(fp):
                self.msa = self.load_msa(fp)
                return self
        else:
            warn("No (correct) MSA file path provided.", stacklevel=2)
        return self

    def load_msa(self, fp):
        file_handlers = {
            ".a3m": partial(self.from_a3m, self),
            ".a2m": partial(self.from_a2m, self),
            ".psi": partial(self.from_psi, self),
        }

        for extension, handler in file_handlers.items():
            if fp.endswith(extension):
                return handler(fp)

        raise ValueError(f"File {fp} is not a valid / supported MSA file. " \
                f"Currently supported formats are: {', '.join(file_handlers.keys())}")

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
