from pathlib import Path

import pytest

from pg2_dataset.io import DataDir, DataFile
from pg2_dataset.models.getter import DataGetter
from pg2_dataset.models.manifest import Sources


@pytest.mark.parametrize(
    "path, dir_type",
    [
        ("tests/test_data/", "local"),
    ],
)
def test_data_getter_initialization(path, dir_type):
    data_dir = DataDir(path=path, dir_type=dir_type)
    data_getter = DataGetter(data_dirs=[data_dir])

    assert isinstance(data_getter, DataGetter)
    assert len(data_getter.data_dirs) > 0
    assert all(isinstance(dir.path, Path) for dir in data_getter.data_dirs)
    assert data_getter.data_dirs[0].dir_type == dir_type


@pytest.mark.parametrize(
    "path, dir_type",
    [
        ("tests/test_data/", "local"),
    ],
)
def test_data_getter_from_sources(path, dir_type):
    sources = Sources(local=[path])
    data_getter = DataGetter.from_sources(sources)

    assert isinstance(data_getter, DataGetter)
    assert len(data_getter.data_dirs) > 0
    assert data_getter.data_dirs[0].path == Path(path)
    assert data_getter.data_dirs[0].dir_type == dir_type


@pytest.mark.parametrize(
    "path, dir_type",
    [
        ("tests/invalid_dir/", "local"),
        ("tests/test_data/", "asd"),
        ("tests/test_data/", None),
        ("", "local"),
    ],
)
@pytest.mark.xfail(raises=ValueError)
def test_data_getter_get_files_empty(path, dir_type):
    data_dir = DataDir(path=path, dir_type=dir_type)
    data_getter = DataGetter(data_dirs=[data_dir])
    files = data_getter.get_files()
    assert len(files) == 0


@pytest.mark.parametrize(
    "path, dir_type",
    [
        ("tests/test_data/io/files", "local"),
    ],
)
def test_data_getter_get_files(path, dir_type):
    data_dir = DataDir(path=path, dir_type=dir_type)
    data_getter = DataGetter(data_dirs=[data_dir])

    files = data_getter.get_files()
    assert len(files) > 0

    assert all(isinstance(file, DataFile) for file in files)
    assert all(file.path.is_file() for file in files)

    data = data_getter.get_data()
    assert len(data) == len(files)
