from pathlib import Path

import pytest

from pg2_dataset.io import DataDir, DataFile
from pg2_dataset.models.constants import DirType
from pg2_dataset.models.getter import DataGetter


@pytest.fixture
def test_data_path():
    return "tests/test_data/"


def test_data_getter_initialization(test_data_path: str):
    data_dir = DataDir(path=test_data_path)
    data_getter = DataGetter(data_dir=data_dir)
    assert data_getter.data_dir.dir_type == DirType.LOCAL
    assert isinstance(data_getter.data_dir.path, Path)
    assert isinstance(data_getter, DataGetter)
    assert isinstance(data_getter.data_dir, DataDir)


def test_data_getter_from_path(test_data_path: str):
    data_getter = DataGetter.from_path(test_data_path)

    assert isinstance(data_getter, DataGetter)
    assert isinstance(data_getter.data_dir, DataDir)
    assert isinstance(data_getter.data_dir.path, Path)
    assert data_getter.data_dir.dir_type == DirType.LOCAL


@pytest.mark.parametrize("invalid_path", ["tests/invalid_dir/", "tests/test_data/", ""])
@pytest.mark.xfail(raises=ValueError)
def test_data_getter_get_files_empty(invalid_path: str):
    data_dir = DataDir(path=invalid_path)
    data_getter = DataGetter(data_dir=data_dir)
    files = data_getter.data_dir.get_files()
    assert len(files) == 0


def test_data_getter_get_files():
    data_dir = DataDir(path="tests/test_data/io/files")
    data_getter = DataGetter(data_dir=data_dir)

    files = data_getter.data_dir.get_files()
    assert len(files) > 0

    assert all(isinstance(file, DataFile) for file in files)
    assert all(file.path.is_file() for file in files)

    data = data_getter.get_data()
    assert len(data) == len(files)
