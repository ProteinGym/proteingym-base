import dvc.api
from cloudpathlib import CloudPath
from loguru import logger


def read_bytes(file_path: str) -> bytes:
    try:
        dataset_registry = "https://github.com/ProteinGym2/dvc-dataset-registry"

        match file_path:
            # option 1: dvc file path
            case _file_path if _file_path.startswith(dataset_registry):
                with dvc.api.open(
                    file_path[len(dataset_registry) + 1 :], dataset_registry, mode="rb"
                ) as f:
                    return f.read()

            # option 2: google cloud storage
            case _file_path if _file_path.startswith("gs://"):
                with CloudPath(file_path).open("rb") as f:
                    return f.read()

            # option 3: local file storage
            case _:
                with open(file_path, "rb") as f:
                    return f.read()

    except Exception as exc:
        logger.error(exc)
        raise exc

def write_bytes(stream, filename):
    with open(filename, "wb") as f:
        f.write(stream)
