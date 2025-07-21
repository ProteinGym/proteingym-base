import shutil
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List


@contextmanager
def zip_context(zip_path: str | Path, extract_path: str | Path = None) -> Iterator[List[Path]]:
    """Extract the contents of a ZIP within a context manager.
    This will extract the ZIP contents to the current working directory and
    yield the list of extracted files. After the context is exited, it will
    automatically clean up by removing the extracted files and directories.
    Example usage:
        with zip_context("path/to/archive.zip") as files:
            for file in files:
                print(file)
    Args:
        zip_path (str | Path): The path to the ZIP file to extract.
    Yields:
        List[Path]: A list of Paths representing the extracted files.
    Finally:
        Cleans up the extracted files and directories.
    Returns:
        Iterator[List[Path]]: An iterator that yields the list of extracted file paths.
    """
    with zipfile.ZipFile(zip_path, "r") as zipf:
        zip_contents = zipf.namelist()
        zipf.extractall(extract_path)
    try:
        yield [Path(name) for name in zip_contents]
    finally:
        for file_name in zip_contents:
            p = Path(file_name)
            if p.exists():
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)
