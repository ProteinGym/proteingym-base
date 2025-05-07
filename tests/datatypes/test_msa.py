import os
import sys
import tempfile
import unittest
from unittest.mock import patch, mock_open

# Add the src directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from pg2_dataset.datatypes.msa import MSA


class TestMSA(unittest.TestCase):
    """Test cases for the MSA (Multiple Sequence Alignment) class."""

    def setUp(self):
        """Set up test data for each test."""
        self.sequences = ["ACGTACGT", "ACGTA-GT", "ACGT--GT"]
        self.records = {
            "seq1": "ACGTACGT",
            "seq2": "ACGTA-GT",
            "seq3": "ACGT--GT"
        }
        self.msa = MSA(sequences=self.sequences, records=self.records)

    def test_init(self):
        """Test the initialization of the MSA class."""
        self.assertEqual(self.msa.sequences, self.sequences)
        self.assertEqual(self.msa.records, self.records)

    def test_get_sequences(self):
        """Test the get_sequences method."""
        self.assertEqual(self.msa.get_sequences(), self.sequences)

    def test_get_records(self):
        """Test the get_records method."""
        self.assertEqual(self.msa.get_records(), self.records)

    def test_get_sequence_by_name(self):
        """Test retrieving a sequence by its record name."""
        self.assertEqual(self.msa.get_sequence_by_name("seq1"), "ACGTACGT")
        self.assertEqual(self.msa.get_sequence_by_name("seq2"), "ACGTA-GT")
        self.assertEqual(self.msa.get_sequence_by_name("seq3"), "ACGT--GT")

    def test_get_sequence_by_name_error(self):
        """Test error handling when a record name is not found."""
        with self.assertRaises(KeyError):
            self.msa.get_sequence_by_name("nonexistent")

    def test_get_sequence_by_index(self):
        """Test retrieving a sequence by its index."""
        self.assertEqual(self.msa.get_sequence_by_index(0), "ACGTACGT")
        self.assertEqual(self.msa.get_sequence_by_index(1), "ACGTA-GT")
        self.assertEqual(self.msa.get_sequence_by_index(2), "ACGT--GT")

    def test_get_sequence_by_index_error(self):
        """Test error handling when an index is out of range."""
        with self.assertRaises(IndexError):
            self.msa.get_sequence_by_index(3)
        with self.assertRaises(IndexError):
            self.msa.get_sequence_by_index(-4)

    def test_extract_record_name(self):
        """Test the _extract_record_name static method."""
        # Test with tr|NAME|DESCRIPTION format
        self.assertEqual(MSA._extract_record_name(">tr|ABC123|Some description"), "ABC123")
        
        # Test with sp|NAME|DESCRIPTION format
        self.assertEqual(MSA._extract_record_name(">sp|XYZ789|Another description"), "XYZ789")
        
        # Test with simple format
        self.assertEqual(MSA._extract_record_name(">Simple header"), "Simple header")
        
        # Test with other pipe formats
        self.assertEqual(MSA._extract_record_name(">db|ACC|Name"), "ACC")

    def test_from_a2m(self):
        """Test the from_a2m static method."""
        a2m_content = ">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA-GT\n>sp|XYZ789|Description2\nACGT--GT\n"
        
        with patch("builtins.open", mock_open(read_data=a2m_content)):
            msa = MSA.from_a2m("dummy_path.a2m")
            
            self.assertEqual(len(msa.sequences), 3)
            self.assertEqual(msa.sequences[0], "ACGTACGT")
            self.assertEqual(msa.sequences[1], "ACGTA-GT")
            self.assertEqual(msa.sequences[2], "ACGT--GT")
            
            self.assertEqual(len(msa.records), 3)
            self.assertEqual(msa.records["ABC123"], "ACGTACGT")
            self.assertEqual(msa.records["Simple header"], "ACGTA-GT")
            self.assertEqual(msa.records["XYZ789"], "ACGT--GT")

    def test_from_a2m_different_lengths(self):
        """Test the from_a2m method with sequences of different lengths."""
        a2m_content = ">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA\n>sp|XYZ789|Description2\nACGT--GT\n"
        
        with patch("builtins.open", mock_open(read_data=a2m_content)):
            with self.assertRaises(ValueError):
                MSA.from_a2m("dummy_path.a2m")

    def test_from_a3m(self):
        """Test the from_a3m static method."""
        a3m_content = ">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA-GT\n>sp|XYZ789|Description2\nACGT--GT\n"
        
        with patch("builtins.open", mock_open(read_data=a3m_content)):
            msa = MSA.from_a3m("dummy_path.a3m")
            
            self.assertEqual(len(msa.sequences), 3)
            self.assertEqual(msa.sequences[0], "ACGTACGT")
            self.assertEqual(msa.sequences[1], "ACGTA-GT")
            self.assertEqual(msa.sequences[2], "ACGT--GT")
            
            self.assertEqual(len(msa.records), 3)
            self.assertEqual(msa.records["ABC123"], "ACGTACGT")
            self.assertEqual(msa.records["Simple header"], "ACGTA-GT")
            self.assertEqual(msa.records["XYZ789"], "ACGT--GT")

    def test_from_psi(self):
        """Test the from_psi static method."""
        psi_content = ">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA-GT\n>sp|XYZ789|Description2\nACGT--GT\n"
        
        with patch("builtins.open", mock_open(read_data=psi_content)):
            msa = MSA.from_psi("dummy_path.psi")
            
            self.assertEqual(len(msa.sequences), 3)
            self.assertEqual(msa.sequences[0], "ACGTACGT")
            self.assertEqual(msa.sequences[1], "ACGTA-GT")
            self.assertEqual(msa.sequences[2], "ACGT--GT")
            
            self.assertEqual(len(msa.records), 3)
            self.assertEqual(msa.records["ABC123"], "ACGTACGT")
            self.assertEqual(msa.records["Simple header"], "ACGTA-GT")
            self.assertEqual(msa.records["XYZ789"], "ACGT--GT")

    def test_multiline_sequences(self):
        """Test parsing files with sequences split across multiple lines."""
        multiline_content = ">tr|ABC123|Description1\nACGT\nACGT\n>Simple header\nACGT\nA-GT\n"
        
        with patch("builtins.open", mock_open(read_data=multiline_content)):
            msa = MSA.from_a2m("dummy_path.a2m")
            
            self.assertEqual(len(msa.sequences), 2)
            self.assertEqual(msa.sequences[0], "ACGTACGT")
            self.assertEqual(msa.sequences[1], "ACGTA-GT")
            
            self.assertEqual(len(msa.records), 2)
            self.assertEqual(msa.records["ABC123"], "ACGTACGT")
            self.assertEqual(msa.records["Simple header"], "ACGTA-GT")

    def test_real_file_io(self):
        """Test reading from an actual temporary file."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_file.write(">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA-GT\n")
            temp_path = temp_file.name
        
        try:
            msa = MSA.from_a2m(temp_path)
            
            self.assertEqual(len(msa.sequences), 2)
            self.assertEqual(msa.sequences[0], "ACGTACGT")
            self.assertEqual(msa.sequences[1], "ACGTA-GT")
            
            self.assertEqual(len(msa.records), 2)
            self.assertEqual(msa.records["ABC123"], "ACGTACGT")
            self.assertEqual(msa.records["Simple header"], "ACGTA-GT")
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()