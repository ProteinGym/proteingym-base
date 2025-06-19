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
    try:
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
   
   Raises:
       Exception: Re-raises any exception that occurs during the existence check,
                 after logging the error.
   """

    try:
        file_path = str(file_path)

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
