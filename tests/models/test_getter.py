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
    data_dir = DataDir(path=path)
    assert data_dir.dir_type == DirType.LOCAL
    assert isinstance(data_dir.path, Path)
    data_getter = DataGetter(data_dir=data_dir)

    assert isinstance(data_getter, DataGetter)
    assert isinstance(data_getter.data_dir, DataDir)


@pytest.mark.parametrize(
    "path",
    [
        ("tests/test_data/"),
    ],
)
def test_data_getter_from_path(path):
    data_getter = DataGetter.from_path(path)

    assert isinstance(data_getter, DataGetter)
    assert isinstance(data_getter.data_dir, DataDir)
    assert isinstance(data_getter.data_dir.path, Path)
    assert data_getter.data_dir.dir_type == DirType.LOCAL


@pytest.mark.parametrize(
    "path",
    [
        ("tests/invalid_dir/"),
        ("tests/test_data/"),
        (""),
    ],
)
@pytest.mark.xfail(raises=ValueError)
def test_data_getter_get_files_empty(path):
    data_dir = DataDir(path=path)
    data_getter = DataGetter(data_dir=data_dir)
    files = data_getter.data_dir.get_files()
    assert len(files) == 0


@pytest.mark.parametrize(
    "path",
    [
        ("tests/test_data/io/files"),
    ],
)
def test_data_getter_get_files(path):
    data_dir = DataDir(path=path)
    data_getter = DataGetter(data_dir=data_dir)

    files = data_getter.data_dir.get_files()
    assert len(files) > 0

    assert all(isinstance(file, DataFile) for file in files)
    assert all(file.path.is_file() for file in files)

    data = data_getter.get_data()
    assert len(data) == len(files)
