import logging
from pathlib import Path

import dvc.api
from dvc.exceptions import DVCError
from cloudpathlib import CloudPath
from botocore.exceptions import ClientError, NoCredentialsError
logger = logging.getLogger(__name__)

_DATASET_REGISTRY = "https://github.com/ProteinGym2/dvc-dataset-registry.git"
_DATASET_FOLDER = "dvc_pg2"


def read_bytes(file_path: Path) -> bytes:
    """
    Read bytes from a file, supporting multiple storage backends.
    
    This function can read from three different storage backends:
    1. DVC-managed datasets (files starting with _DATASET_FOLDER path)
    2. S3 cloud storage (files with s3:// prefix)
    3. Local filesystem (all other paths)
    
    Args:
        file_path: Path to the file to read. Can be a local path,
                         S3 URI (s3://bucket/key), or dataset path.
    
    Returns:
        bytes: The complete file content as bytes.
    """

    file_path = str(file_path)

    try:
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

    except Exception as exc:
        logger.error(exc)
        raise exc


def write_bytes(stream, filename):
    with open(filename, "wb") as f:
        f.write(stream)


def exists(file_path: Path) -> bool:
    """
    Check if a file or directory exists across different storage backends.
    
    This function provides a unified interface to check file existence across
    local filesystem, DVC-managed datasets, and S3 cloud storage. It automatically
    determines the appropriate backend based on the file path prefix.
    
    Args:
        file_path: The path to the file or directory to check.
                                Can be a local path, DVC dataset path (starting with
                                DATASET_FOLDER), or S3 URL (starting with "s3://").
    
    Returns:
        bool: True if the file or directory exists, False otherwise.
    """
    
    file_path = str(file_path)

    try:
        match file_path:
            case _file_path if _file_path.startswith(_DATASET_FOLDER):
                return dvc.api.DVCFileSystem(_DATASET_REGISTRY).exists(file_path)

            case _file_path if _file_path.startswith("s3://"):
                return CloudPath(file_path).exists()

            case _:
                return Path(file_path).exists()

    except (DVCError, ClientError, NoCredentialsError) as exc:
        logger.error(f"Service error: {exc}")
        raise exc
    
    except (ConnectionError, OSError, PermissionError, FileNotFoundError) as exc:
        logger.error(f"Network / IO error: {exc}")
        raise exc

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise exc
