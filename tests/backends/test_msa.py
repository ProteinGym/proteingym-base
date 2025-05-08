import os
import tempfile
import pytest
from io import StringIO

from pg2_dataset.primitives.msa import MSA


@pytest.fixture
def msa_data():
    """Fixture providing test data for MSA tests."""
    records = {"seq1": "ACGTACGT", "seq2": "ACGTA-GT", "seq3": "ACGT--GT"}
    return {"records": records}


@pytest.fixture
def msa_instance(msa_data):
    """Fixture providing an MSA instance for tests."""
    return MSA(records=msa_data["records"])


def test_init(msa_instance, msa_data):
    """Test the initialization of the MSA class."""
    assert msa_instance.sequences == list(msa_data["records"].values())
    assert msa_instance.records == msa_data["records"]


def test_get_sequence_by_name_error(msa_instance):
    """Test error handling when a record name is not found."""
    with pytest.raises(KeyError):
        msa_instance.records["nonexistent"]


def test_get_sequence_by_index(msa_instance):
    """Test retrieving a sequence by its index."""
    assert msa_instance.sequences[0] == "ACGTACGT"
    assert msa_instance.sequences[1] == "ACGTA-GT"
    assert msa_instance.sequences[2] == "ACGT--GT"


def test_get_sequence_by_index_error(msa_instance):
    """Test error handling when an index is out of range."""
    with pytest.raises(IndexError):
        msa_instance.sequences[3]
    with pytest.raises(IndexError):
        msa_instance.sequences[4]


def test_extract_record_name():
    """Test the _extract_record_name static method."""
    # Test with tr|NAME|DESCRIPTION format
    assert MSA._extract_record_name(">tr|ABC123|Some description") == "ABC123"

    # Test with sp|NAME|DESCRIPTION format
    assert MSA._extract_record_name(">sp|XYZ789|Another description") == "XYZ789"

    # Test with simple format
    assert MSA._extract_record_name(">Simple header") == "Simple header"

    # Test with other pipe formats
    assert MSA._extract_record_name(">db|ACC|Name") == "ACC"


class MockFile:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return StringIO(self.content)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_from_a2m(monkeypatch):
    """Test the from_a2m static method."""
    a2m_content = ">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA-GT\n>sp|XYZ789|Description2\nACGT--GT\n"

    # Create a mock file object
    mock_file = MockFile(a2m_content)

    # Patch the open function to return our mock file
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: mock_file)

    msa = MSA.from_a2m("dummy_path.a2m")

    assert len(msa.sequences) == 3
    assert msa.sequences[0] == "ACGTACGT"
    assert msa.sequences[1] == "ACGTA-GT"
    assert msa.sequences[2] == "ACGT--GT"

    assert len(msa.records) == 3
    assert msa.records["ABC123"] == "ACGTACGT"
    assert msa.records["Simple header"] == "ACGTA-GT"
    assert msa.records["XYZ789"] == "ACGT--GT"


def test_from_a2m_different_lengths(monkeypatch):
    """Test the from_a2m method with sequences of different lengths."""
    a2m_content = ">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA\n>sp|XYZ789|Description2\nACGT--GT\n"

    # Create a mock file object
    mock_file = MockFile(a2m_content)

    # Patch the open function to return our mock file
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: mock_file)

    with pytest.raises(ValueError):
        MSA.from_a2m("dummy_path.a2m")


def test_from_a3m(monkeypatch):
    """Test the from_a3m static method."""
    a3m_content = ">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA-GT\n>sp|XYZ789|Description2\nACGT--GT\n"

    # Create a mock file object
    mock_file = MockFile(a3m_content)

    # Patch the open function to return our mock file
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: mock_file)

    msa = MSA.from_a3m("dummy_path.a3m")

    assert len(msa.sequences) == 3
    assert msa.sequences[0] == "ACGTACGT"
    assert msa.sequences[1] == "ACGTA-GT"
    assert msa.sequences[2] == "ACGT--GT"

    assert len(msa.records) == 3
    assert msa.records["ABC123"] == "ACGTACGT"
    assert msa.records["Simple header"] == "ACGTA-GT"
    assert msa.records["XYZ789"] == "ACGT--GT"


def test_from_psi(monkeypatch):
    """Test the from_psi static method."""
    psi_content = "tr|ABC123|Description1 ACGTACGT\nSimpleHeader ACGTA-GT\n>sp|XYZ789|Description2 ACGT--GT\n"

    # Create a mock file object
    mock_file = MockFile(psi_content)

    # Patch the open function to return our mock file
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: mock_file)

    msa = MSA.from_psi("dummy_path.psi")

    assert len(msa.sequences) == 3
    assert msa.sequences[0] == "ACGTACGT"
    assert msa.sequences[1] == "ACGTA-GT"
    assert msa.sequences[2] == "ACGT--GT"

    assert len(msa.records) == 3
    assert msa.records["ABC123"] == "ACGTACGT"
    assert msa.records["SimpleHeader"] == "ACGTA-GT"
    assert msa.records["XYZ789"] == "ACGT--GT"


def test_multiline_sequences(monkeypatch):
    """Test parsing files with sequences split across multiple lines."""
    multiline_content = (
        ">tr|ABC123|Description1\nACGT\nACGT\n>Simple header\nACGT\nA-GT\n"
    )

    # Create a mock file object
    mock_file = MockFile(multiline_content)

    # Patch the open function to return our mock file
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: mock_file)

    msa = MSA.from_a2m("dummy_path.a2m")

    assert len(msa.sequences) == 2
    assert msa.sequences[0] == "ACGTACGT"
    assert msa.sequences[1] == "ACGTA-GT"

    assert len(msa.records) == 2
    assert msa.records["ABC123"] == "ACGTACGT"
    assert msa.records["Simple header"] == "ACGTA-GT"


def test_real_file_io():
    """Test reading from an actual temporary file."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        temp_file.write(">tr|ABC123|Description1\nACGTACGT\n>Simple header\nACGTA-GT\n")
        temp_path = temp_file.name

    try:
        msa = MSA.from_a2m(temp_path)

        assert len(msa.sequences) == 2
        assert msa.sequences[0] == "ACGTACGT"
        assert msa.sequences[1] == "ACGTA-GT"

        assert len(msa.records) == 2
        assert msa.records["ABC123"] == "ACGTACGT"
        assert msa.records["Simple header"] == "ACGTA-GT"
    finally:
        os.unlink(temp_path)
