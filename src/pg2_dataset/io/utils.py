import tomllib
from pathlib import Path
from zipfile import ZipFile


def zip_from_dir(directory, dataset_filename):
    files = Path(directory)
    with ZipFile(Path(dataset_filename), "w") as myzip:
        for f in files.glob("*"):
            myzip.write(f, arcname=f.name)


def export_toml(d, filename):
    with open(filename, "w") as f:
        tomllib.dump(d, f)
