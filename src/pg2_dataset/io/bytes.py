import logging
from pathlib import Path

import dvc.api
from cloudpathlib import CloudPath

logger = logging.getLogger(__name__)

_DATASET_REGISTRY = "https://github.com/ProteinGym2/dvc-dataset-registry.git"
_DATASET_FOLDER = "dvc_pg2"


def read_bytes(file_path: Path) -> bytes:
    """Read bytes from a file, supporting multiple storage locations.

    This function can read from three different storage backends:
    1. DVC-managed datasets (files starting with _DATASET_FOLDER path)
    2. S3 cloud storage (files with s3:// prefix)
    3. Local filesystem (all other paths)

    Args:
        file_path: Path to the file to read.

    Returns:
        bytes: The complete file content as bytes.
    """

    file_path = str(file_path)

    match file_path:
        case _file_path if _file_path.startswith(_DATASET_FOLDER):
            with dvc.api.open(file_path, repo=_DATASET_REGISTRY, mode="rb") as f:
                return f.read()

        case _file_path if _file_path.startswith("s3://"):
            with CloudPath(file_path).open("rb") as f:
                return f.read()

        case _:
            with open(file_path, "rb") as f:
                return f.read()


def write_bytes(stream, filename):
    with open(filename, "wb") as f:
        f.write(stream)


def exists(file_path: Path) -> bool:
    """Check if a file or directory exists across different storage locations.

    This function can read from three different storage backends:
    1. DVC-managed datasets (files starting with _DATASET_FOLDER path)
    2. S3 cloud storage (files with s3:// prefix)
    3. Local filesystem (all other paths)

    Args:
        file_path: The path to the file or directory to check.

    Returns:
        bool: True if the file or directory exists, False otherwise.
    """

    file_path = str(file_path)

    match file_path:
        case _file_path if _file_path.startswith(_DATASET_FOLDER):
            return dvc.api.DVCFileSystem(_DATASET_REGISTRY).exists(file_path)

        case _file_path if _file_path.startswith("s3://"):
            return CloudPath(file_path).exists()

        case _:
            return Path(file_path).exists()
