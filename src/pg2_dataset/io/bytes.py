import logging
from pathlib import Path

import dvc.api
from cloudpathlib import CloudPath

logger = logging.getLogger(__name__)

DATASET_REGISTRY = "https://github.com/ProteinGym2/dvc-dataset-registry.git"
DATASET_FOLDER = "dvc_pg2"


def read_bytes(file_path: str | Path) -> bytes:
    try:
        file_path = str(file_path)

        match file_path:
            case _file_path if _file_path.startswith(DATASET_FOLDER):
                with dvc.api.open(file_path, repo=DATASET_REGISTRY, mode="rb") as f:
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


def exists(file_path: str | Path) -> bool:
    try:
        file_path = str(file_path)

        match file_path:
            case _file_path if _file_path.startswith(DATASET_FOLDER):
                return dvc.api.DVCFileSystem(DATASET_REGISTRY).exists(file_path)

            case _file_path if _file_path.startswith("s3://"):
                return CloudPath(file_path).exists()

            case _:
                return Path(file_path).exists()

    except Exception as exc:
        logger.error(exc)
        raise exc
