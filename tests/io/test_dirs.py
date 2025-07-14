import pytest
from pg2_dataset.io import DataDir, DataFile
from pathlib import Path

@pytest.mark.parametrize(
    "path, dir_type",
    [
        ("tests/test_data/", "local")
    ]
)
def test_data_dir_initialization(path, dir_type):
    data_dir = DataDir(path=path, dir_type=dir_type)
    assert data_dir.path == Path(path)
    assert data_dir.dir_type == dir_type
    assert isinstance(data_dir.files, list)

@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    "path, dir_type",
    [
        ("tests/test_data/non_existent_dir", "local"),
        ("tests/test_data/empty_dir", "local"),
    ]
)
def test_data_dir_bad_path(path, dir_type):
    DataDir(path=path, dir_type=dir_type)


def test_data_dir_get_files(tmp_path):
    # Create a temp dir with files
    (tmp_path / "file1.txt").write_text("Content of file 1")
    (tmp_path / "file2.txt").write_text("Content of file 2")

    data_dir = DataDir(path=tmp_path, dir_type="local")
    files = data_dir.get_files()

    assert len(files) == 2
    assert all(isinstance(file, DataFile) for file in files)
    assert all(file.path.is_file() for file in files)
    assert all(file.file_type == "txt" for file in files)