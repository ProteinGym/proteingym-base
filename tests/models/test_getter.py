from pathlib import Path

import pytest

from pg2_dataset.io import DataDir, DataFile
from pg2_dataset.models.constants import DirType
from pg2_dataset.models.getter import DataGetter


@pytest.mark.parametrize(
    "path",
    [
        ("tests/test_data/"),
    ],
)
def test_data_getter_initialization(path):
    data_dir = DataDir(path=Path(path))
    assert data_dir.dir_type == DirType.LOCAL
    assert isinstance(data_dir.path, Path)
    data_getter = DataGetter(data_dirs=[data_dir])

    assert isinstance(data_getter, DataGetter)
    assert len(data_getter.data_dirs) > 0


@pytest.mark.parametrize(
    "path",
    [
        (["tests/test_data/"]),
    ],
)
def test_data_getter_from_paths(path):
    data_getter = DataGetter.from_paths(path)

    assert isinstance(data_getter, DataGetter)
    assert len(data_getter.data_dirs) > 0
    for data_dir in data_getter.data_dirs:
        assert isinstance(data_dir, DataDir)
        assert isinstance(data_dir.path, Path)
        assert data_dir.dir_type == DirType.LOCAL


@pytest.mark.parametrize(
    "path",
    [
        ("tests/invalid_dir/"),
        ("tests/test_data/"),
        ("tests/test_data/"),
        (""),
    ],
)
@pytest.mark.xfail(raises=ValueError)
def test_data_getter_get_files_empty(path):
    data_dir = DataDir(path=Path(path))
    data_getter = DataGetter(data_dirs=[data_dir])
    files = data_getter.get_files()
    assert len(files) == 0


@pytest.mark.parametrize(
    "path",
    [
        ("tests/test_data/io/files"),
    ],
)
def test_data_getter_get_files(path):
    data_dir = DataDir(path=Path(path))
    data_getter = DataGetter(data_dirs=[data_dir])

    files = data_getter.get_files()
    assert len(files) > 0

    assert all(isinstance(file, DataFile) for file in files)
    assert all(file.path.is_file() for file in files)

    data = data_getter.get_data()
    assert len(data) == len(files)
