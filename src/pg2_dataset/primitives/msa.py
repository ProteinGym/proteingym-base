import re


class MSA:
    def __init__(self, records: dict[str, str]):
        self.records = records

    @property
    def sequences(self) -> list[str]:
        return list(self.records.values())

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

    @staticmethod
    def from_a2m(file_path: str) -> "MSA":
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
                    name = MSA._extract_record_name(line)
                    seq = ""
                else:
                    seq += line

            # save last entry
            if name is not None:
                records[name] = seq

        if len({len(s) for s in records.values()}) > 1:
            raise ValueError("All sequences in A2M format must be of same length")

        return MSA(records=records)

    @staticmethod
    def from_a3m(file_path: str) -> "MSA":
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
                    name = MSA._extract_record_name(line)
                    seq = ""
                else:
                    seq += line

            # save last entry
            if name is not None:
                records[name] = seq

        return MSA(records=records)

    @staticmethod
    def from_psi(file_path: str) -> "MSA":
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
                name = MSA._extract_record_name(header)
                records[name] = sequence

        return MSA(records=records)
