from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from pg2_dataset.io import DataFile
from pg2_dataset.io.files.sequence import SequenceDataFile
from pg2_dataset.models.constants import SequenceFileType
from pg2_dataset.io import DataFileAdapter
from pathlib import Path
import pytest

TEST_SEQUENCE_FILE = "tests/test_data/io/files/seq.fasta"

@pytest.mark.parametrize(
    "path, file_type",
    [
        ("tests/test_data/io/files/file.txt", "txt"),
        ("tests/test_data/io/files/file.txt", None),

    ]
)
def test_data_file(path, file_type):
    data_file = DataFile(path=path, file_type=file_type)
    assert data_file.path == Path(path)
    assert data_file.file_type != None

@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    "path",
    [("tests/test_data/io/files/non_existent_file.txt"),
     ("tests/test_data/io/files/non_existent_file")
    ]
)
def test_data_file_bad_path(path):
    DataFile(path=path)


@pytest.mark.parametrize(
    "path, file_type",
    [
        (TEST_SEQUENCE_FILE, None),
        (TEST_SEQUENCE_FILE, "fasta"),
    ]
)
def test_sequence_file_adapter(path, file_type):
    adapter = DataFileAdapter.validate_python({"path": path, "file_type": file_type})
    assert isinstance(adapter, SequenceDataFile)
    assert adapter.file_type in [ft.value for ft in SequenceFileType]


@pytest.mark.parametrize(
    "path, file_type",
    [
        (TEST_SEQUENCE_FILE, "fasta"),
    ]
)
def test_sequence_data_file_read(path, file_type):
    seq_file = SequenceDataFile(path=Path(path), file_type=file_type)
    record = seq_file.read()
    assert isinstance(record, SeqRecord)


def test_sequence_data_file_dump(tmp_path):
    seq_file = SequenceDataFile(path=tmp_path / "test_seq.fasta")
    record = SeqRecord(seq=Seq("ATCG"), name="test_seq", description="Test sequence")
    seq_file.dump(record)
    
    assert seq_file.path.exists()
    read_record = seq_file.read()
    assert isinstance(read_record, SeqRecord)
