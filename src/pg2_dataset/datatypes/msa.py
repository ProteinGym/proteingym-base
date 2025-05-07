from typing import List, Dict, Any, Optional, Tuple
import re

class MSA:
    def __init__(self, sequences: List[str], records: Dict[str, str]):
        self.sequences = sequences
        self.records = records
    
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
        header = header_line[1:].strip()
        
        # Check if the header has the format tr|NAME|DESCRIPTION
        pipe_match = re.match(r'.*\|(.*?)\|', header)
        if pipe_match:
            return pipe_match.group(1)
        else:
            return header
    
    @staticmethod
    def from_a2m(file_path: str) -> 'MSA':
        """
        Parse an A2M file and return an MSA object.
        
        Args:
            file_path: Path to the A2M file
            
        Returns:
            MSA object with sequences and records
        """
        with open(file_path, 'r') as file:
            lines = file.readlines()

        sequences = []
        records = {}
        l = 0
        while l < len(lines):
            if lines[l].startswith('>'):
                name = MSA._extract_record_name(lines[l])
                full_header = lines[l][1:].strip()
                
                l += 1
                seq = ''
                while l < len(lines) and not lines[l].startswith('>'):
                    seq += lines[l].strip()
                    l += 1
                sequences.append(seq)
                records[name] = seq
            else:
                l += 1
            
        # Check all sequences are same length
        if sequences:
            seq_length = len(sequences[0])
            if not all(len(seq) == seq_length for seq in sequences):
                raise ValueError("All sequences in A2M format must be of same length")

        return MSA(sequences=sequences, records=records)

    @staticmethod
    def from_a3m(file_path: str) -> 'MSA':
        """
        Parse an A3M file and return an MSA object.
        
        Args:
            file_path: Path to the A3M file
            
        Returns:
            MSA object with sequences and records
        """
        with open(file_path, 'r') as file:
            lines = file.readlines()

        sequences = []
        records = {}
        l = 0
        while l < len(lines):
            if lines[l].startswith('>'):
                name = MSA._extract_record_name(lines[l])
                full_header = lines[l][1:].strip()
                
                l += 1
                seq = ''
                while l < len(lines) and not lines[l].startswith('>'):
                    seq += lines[l].strip()
                    l += 1
                sequences.append(seq)
                records[name] = seq
            else:
                l += 1
                
        return MSA(sequences=sequences, records=records)
    
    def get_sequences(self) -> List[str]:
        """Return the list of sequences"""
        return self.sequences
    
    def get_records(self) -> Dict[str, str]:
        """Return the dictionary of record names to sequences"""
        return self.records
    
    def get_sequence_by_name(self, name: str) -> str:
        """Get a sequence by its record name"""
        if name in self.records:
            return self.records[name]
        raise KeyError(f"Record name '{name}' not found in MSA")
    
    # Additional method to get sequence by index
    def get_sequence_by_index(self, index: int) -> str:
        """Get a sequence by its index in the sequences list"""
        if 0 <= index < len(self.sequences):
            return self.sequences[index]
        raise IndexError(f"Index {index} out of range for MSA with {len(self.sequences)} sequences")
        
    @staticmethod
    def from_psi(file_path: str) -> 'MSA':
        """
        Parse a PSI file and return an MSA object.
        
        Args:
            file_path: Path to the PSI file
            
        Returns:
            MSA object with sequences and records
        """
        with open(file_path, 'r') as file:
            lines = file.readlines()

        sequences = []
        records = {}
        l = 0
        while l < len(lines):
            if lines[l].startswith('>'):
                name = MSA._extract_record_name(lines[l])
                
                l += 1
                seq = ''
                while l < len(lines) and not lines[l].startswith('>'):
                    seq += lines[l].strip()
                    l += 1
                sequences.append(seq)
                records[name] = seq
            else:
                l += 1
                
        return MSA(sequences=sequences, records=records)